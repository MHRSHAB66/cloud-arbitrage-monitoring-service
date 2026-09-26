from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, DateTime, Integer, Index, UniqueConstraint
from db import Base


class PriceSample(Base):
    __tablename__ = "price_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    pair: Mapped[str] = mapped_column(String(32), index=True)
    exchange: Mapped[str] = mapped_column(String(32), index=True)
    price: Mapped[float] = mapped_column(Float)

    __table_args__ = (
        # جلوگیری از رکورد تکراری وقتی نمونه‌برداری سریع است
        UniqueConstraint("ts", "pair", "exchange", name="uq_sample_ts_pair_ex"),
        Index("ix_samples_pair_ts", "pair", "ts"),
    )


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    pair: Mapped[str] = mapped_column(String(32), index=True)
    ex_from: Mapped[str] = mapped_column(String(32))
    ex_to: Mapped[str] = mapped_column(String(32))
    p_from: Mapped[float] = mapped_column(Float)
    p_to: Mapped[float] = mapped_column(Float)
    spread_pct: Mapped[float] = mapped_column(Float, index=True)
    threshold: Mapped[float] = mapped_column(Float)

    __table_args__ = (
        UniqueConstraint("ts", "pair", "ex_from", "ex_to", name="uq_opp_ts_pair_route"),
        Index("ix_opp_pair_ts", "pair", "ts"),
    )
