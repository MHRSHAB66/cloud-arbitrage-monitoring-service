# exchanges.py — unified with metric.py
import asyncio
from typing import Optional

import httpx
from settings import (
    HTTP_TIMEOUT_SEC, HTTP_RETRIES,
    WALLEX_BASE_URL, NOBITEX_BASE_URL,
    NOBITEX_FALLBACK_ENABLED, NOBITEX_IP,
    WALLEX_KEY, NOBITEX_KEY,
)
# Use shared metrics
from metric import api_latency, api_requests_total, price_last

class ExchangeError(RuntimeError):
    pass

def _split_symbol(unified: str):
    s = unified.lower()
    if s.endswith(("irt", "irr")):
        return s[:-3], "rls"
    return s[:-4], s[-4:]

def _nx_key(unified: str) -> str:
    src, dst = _split_symbol(unified)
    return f"{src}-{dst}"

async def wallex_last(symbol: str, api_key: Optional[str] = None) -> float:
    url = f"{WALLEX_BASE_URL.rstrip('/')}/v1/trades"
    headers = {"x-api-key": api_key or WALLEX_KEY} if (api_key or WALLEX_KEY) else {}
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SEC, follow_redirects=True) as cx:
            r = await cx.get(url, params={"symbol": symbol}, headers=headers)
            r.raise_for_status()
            data = r.json()
        trades = data.get("result", {}).get("latestTrades") if isinstance(data, dict) else None
        if not trades:
            raise ValueError("Wallex: no trades in response")
        last_trade = trades[-1]
        price = float(last_trade["price"])
        # metrics
        api_requests_total.labels("wallex", symbol, "ok").inc()
        api_latency.labels("wallex", symbol).observe(r.elapsed.total_seconds())
        price_last.labels("wallex", symbol).set(price)
        return price
    except Exception as e:
        api_requests_total.labels("wallex", symbol, "error").inc()
        raise ExchangeError(f"Wallex error: {e}")

async def nobitex_last(symbol: str, api_key: Optional[str] = None) -> float:
    src, dst = _split_symbol(symbol)
    key = f"{src}-{dst}"
    base_url = NOBITEX_BASE_URL.rstrip("/")
    url = f"{base_url}/market/stats"
    headers = {"Content-Type": "application/json"}
    if api_key or NOBITEX_KEY:
        headers["Authorization"] = f"Token {api_key or NOBITEX_KEY}"
    payload = {"srcCurrency": src, "dstCurrency": dst}

    # Normal attempts
    for attempt in range(1, HTTP_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SEC, follow_redirects=True) as cx:
                r = await cx.post(url, json=payload, headers=headers)
                r.raise_for_status()
                j = r.json()
            stats = j.get("stats", {})
            if key not in stats:
                raise KeyError(f"Nobitex: key '{key}' not found in stats")
            data = stats[key]
            last = data.get("bestSell") or data.get("bestBuy") or data.get("latest")
            price = float(last)
            api_requests_total.labels("nobitex", symbol, "ok").inc()
            api_latency.labels("nobitex", symbol).observe(r.elapsed.total_seconds())
            price_last.labels("nobitex", symbol).set(price)
            return price
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.NetworkError) as e:
            api_requests_total.labels("nobitex", symbol, "error").inc()
            if attempt < HTTP_RETRIES:
                await asyncio.sleep(1.0)
                continue
            if NOBITEX_FALLBACK_ENABLED:
                break
            raise ExchangeError(f"Nobitex network error after {attempt} attempts: {e}")
        except Exception as e:
            api_requests_total.labels("nobitex", symbol, "error").inc()
            if attempt < HTTP_RETRIES:
                await asyncio.sleep(1.0)
                continue
            raise ExchangeError(f"Nobitex error after {attempt} attempts: {e}")

    # Fallback to IP (TLS verify=False; acceptable for this exercise)
    if not NOBITEX_FALLBACK_ENABLED:
        raise ExchangeError("Nobitex fallback disabled and DNS/Network failed.")

    ip_url = f"https://{NOBITEX_IP}/market/stats"
    fb_headers = {"Host": "api.nobitex.ir", "Content-Type": "application/json"}
    if api_key or NOBITEX_KEY:
        fb_headers["Authorization"] = f"Token {api_key or NOBITEX_KEY}"

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SEC, follow_redirects=True, verify=False) as cx:
            r = await cx.post(ip_url, json=payload, headers=fb_headers)
            r.raise_for_status()
            j = r.json()
        stats = j.get("stats", {})
        if key not in stats:
            raise KeyError(f"Nobitex (fallback): key '{key}' not found in stats")
        data = stats[key]
        last = data.get("bestSell") or data.get("bestBuy") or data.get("latest")
        price = float(last)
        api_requests_total.labels("nobitex", symbol, "ok").inc()
        api_latency.labels("nobitex", symbol).observe(r.elapsed.total_seconds())
        price_last.labels("nobitex", symbol).set(price)
        return price
    except Exception as e:
        api_requests_total.labels("nobitex", symbol, "error").inc()
        raise ExchangeError(f"Nobitex fallback error: {e}")
