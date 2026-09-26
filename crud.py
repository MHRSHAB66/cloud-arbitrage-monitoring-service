# crud.py
from __future__ import annotations
from datetime import datetime, timezone
from typing import Iterable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models import PriceSample, Opportunity

# ذخیره نمونه قیمت (Upsert روی Postgres؛ روی SQLite dedup دستی)
async def save_price(pair: str, exchange: str, price: float, ts: datetime | None = None, db: AsyncSession | None = None):
    """
    ذخیره یا آپدیت آخرین قیمت خوانده‌شده.
    اگر db None باشد، فرض می‌کنیم در سطح بالاتر سشن تزریق شده؛
    ولی بهترین حالت: این تابع را با db صدا بزنید.
    """
    if ts is None:
        ts = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC for SQLAlchemy DateTime

    row = {"ts": ts, "pair": pair, "exchange": exchange, "price": float(price)}

    if db.bind and db.bind.dialect.name == "postgresql":
        stmt = (
            pg_insert(PriceSample)
            .values(row)
            .on_conflict_do_update(
                constraint="uq_sample_ts_pair_ex",
                set_={"price": pg_insert.excluded.price},
            )
        )
        await db.execute(stmt)
    else:
        # SQLite fallback (no ON CONFLICT target name)
        exists_q = select(PriceSample).where(
            (PriceSample.ts == row["ts"]) &
            (PriceSample.pair == row["pair"]) &
            (PriceSample.exchange == row["exchange"])
        )
        if (await db.execute(exists_q)).scalar_one_or_none() is None:
            db.add(PriceSample(**row))
        else:
            # ساده: اگر وجود داشت، آپدیتش کنیم
            ps = (await db.execute(exists_q)).scalar_one()
            ps.price = row["price"]

    await db.commit()


async def save_opportunity(
    pair: str,
    ex_from: str,
    ex_to: str,
    p_from: float,
    p_to: float,
    spread_pct: float,
    threshold: float,
    ts: datetime | None = None,
    db: AsyncSession | None = None,
) -> None:
    if ts is None:
        ts = datetime.now(timezone.utc).replace(tzinfo=None)

    opp = {
        "ts": ts,
        "pair": pair,
        "ex_from": ex_from,
        "ex_to": ex_to,
        "p_from": float(p_from),
        "p_to": float(p_to),
        "spread_pct": float(spread_pct),
        "threshold": float(threshold),
    }

    if db.bind and db.bind.dialect.name == "postgresql":
        stmt = (
            pg_insert(Opportunity)
            .values(opp)
            .on_conflict_do_nothing(constraint="uq_opp_ts_pair_route")
        )
        await db.execute(stmt)
    else:
        exists_q = select(Opportunity).where(
            (Opportunity.ts == opp["ts"]) &
            (Opportunity.pair == opp["pair"]) &
            (Opportunity.ex_from == opp["ex_from"]) &
            (Opportunity.ex_to == opp["ex_to"])
        )
        if (await db.execute(exists_q)).scalar_one_or_none() is None:
            db.add(Opportunity(**opp))

    await db.commit()


async def recent_prices(db: AsyncSession, pair: str, limit: int = 100) -> Sequence[PriceSample]:
    q = (
        select(PriceSample)
        .where(PriceSample.pair == pair)
        .order_by(PriceSample.ts.desc())
        .limit(limit)
    )
    return (await db.execute(q)).scalars().all()
