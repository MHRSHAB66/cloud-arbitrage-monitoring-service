# app.py — multi-pair worker + metrics + db save + notify (CLEAN)
import asyncio
from datetime import datetime, timezone
from typing import Tuple

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from settings import (
    PAIRS, THRESHOLD_PCT, POLL_SEC,
    ENABLE_WORKER,
)
from exchanges import wallex_last, nobitex_last, ExchangeError
from notifier import notify
from db import init_db, get_session
from metric import spread_latest, arbitrage_found_total, price_last
from crud import save_price, save_opportunity  # << فایل باید به‌نام crud.py باشد

app = FastAPI(title="Cloud HW1 - Arbitrage (multi-pair)")

# ---------- helpers ----------
def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _best_route(pair: str, wpx: float, npx: float) -> Tuple[str, str, float, float, float]:
    """
    Return: (ex_from, ex_to, p_from, p_to, spread_pct)
    Buy lower; sell higher. spread% = (sell - buy)/buy * 100
    """
    if wpx <= npx:
        ex_from, ex_to = "wallex", "nobitex"
        p_from, p_to = wpx, npx
    else:
        ex_from, ex_to = "nobitex", "wallex"
        p_from, p_to = npx, wpx
    spread_pct = (p_to - p_from) / p_from * 100.0 if p_from > 0 else 0.0
    return ex_from, ex_to, p_from, p_to, spread_pct

# ---------- single-tick for one pair ----------
async def _tick_pair(pair: str):
    """
    Fetch prices for one pair, update metrics, store DB, send notify if threshold met.
    """
    try:
        # concurrent fetch from both exchanges
        w_task = asyncio.create_task(wallex_last(pair))
        n_task = asyncio.create_task(nobitex_last(pair))
        wpx, npx = await asyncio.gather(w_task, n_task)
    except Exception:
        # api_requests_total & latency handled inside exchanges.py already
        return

    # update latest prices in metrics
    price_last.labels("wallex", pair).set(wpx)
    price_last.labels("nobitex", pair).set(npx)

    ex_from, ex_to, p_from, p_to, spread_pct = _best_route(pair, wpx, npx)
    spread_latest.labels(pair).set(spread_pct)

    now = _utcnow_naive()
    # single DB session for both inserts
    async for db in get_session():
        await save_price(pair, "wallex", wpx, ts=now, db=db)
        await save_price(pair, "nobitex", npx, ts=now, db=db)

        if spread_pct >= THRESHOLD_PCT:
            arbitrage_found_total.labels(pair).inc()
            await save_opportunity(
                pair=pair,
                ex_from=ex_from, ex_to=ex_to,
                p_from=p_from, p_to=p_to,
                spread_pct=spread_pct, threshold=THRESHOLD_PCT,
                ts=now, db=db,
            )
            # notify (best-effort)
            html = (
                f"<b>Arbitrage detected</b>\n"
                f"Pair: <code>{pair}</code>\n"
                f"Buy @ <b>{ex_from}</b>: <code>{p_from}</code>\n"
                f"Sell @ <b>{ex_to}</b>: <code>{p_to}</code>\n"
                f"Spread: <b>{spread_pct:.3f}%</b> (threshold {THRESHOLD_PCT}%)\n"
                f"Time: {now.isoformat()}Z"
            )
            try:
                await notify(html)
            except Exception:
                pass

# ---------- background worker ----------
async def _worker():
    """
    Round-robin all pairs, fetch concurrently per tick.
    """
    await init_db(create_all=True)
    while True:
        try:
            await asyncio.gather(*[_tick_pair(p) for p in PAIRS])
        except Exception:
            # do not crash worker loop
            pass
        await asyncio.sleep(POLL_SEC)

# ---------- startup ----------
@app.on_event("startup")
async def _startup():
    if ENABLE_WORKER:
        asyncio.create_task(_worker())

# ---------- endpoints ----------
@app.get("/healthz")
async def healthz():
    return {"ok": True, "pairs": PAIRS, "threshold_pct": THRESHOLD_PCT, "poll_sec": POLL_SEC}

@app.get("/config")
def config():
    return {"PAIRS": PAIRS, "THRESHOLD_PCT": THRESHOLD_PCT, "POLL_SEC": POLL_SEC}

@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
