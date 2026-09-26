# db.py
from __future__ import annotations

import os
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncAttrs,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text


# --------- 1) ENV & flags ---------
def _as_bool(value: Optional[str], default: bool = False) -> bool:
    """
    Parse a string env var into bool. Accepts: "1"/"0", "true"/"false", "yes"/"no".
    """
    if value is None:
        return default
    v = value.strip().lower()
    return v in ("1", "true", "yes", "on")


DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
DB_ECHO = _as_bool(os.getenv("DB_ECHO"), False)

if not DATABASE_URL:
    # Fail fast: we *must* have a URL (e.g., postgresql+asyncpg://user:pass@host:5432/dbname)
    raise RuntimeError("DATABASE_URL is not set")

# Soft validation:
if not DATABASE_URL.startswith(("postgresql+asyncpg://", "sqlite+aiosqlite:///")):
    # We allow SQLite for dev, but recommend asyncpg in prod.
    # No hard failure, just a heads-up in logs.
    print(
        f"[db] Warning: Unexpected driver in DATABASE_URL: {DATABASE_URL.split('://',1)[0]} "
        f"(recommended: postgresql+asyncpg)"
    )


# --------- 2) SQLAlchemy base ---------
class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for all ORM models.
    - AsyncAttrs allows 'await obj.refresh()' etc. in async contexts.
    - DeclarativeBase is SQLAlchemy 2.0 style.
    """
    pass


# --------- 3) Engine & Session factory ---------
# Tuned for asyncpg; these connect_args are harmless for SQLite (ignored).
CONNECT_ARGS = {
    "server_settings": {
        "application_name": "arbitrage-service",
        # Set a sane statement timeout at the server level (milliseconds) for protection.
        # You can change or remove this if you want longer queries.
        "statement_timeout": "5000",
    }
}

# Pool settings: queue pool is supported for asyncpg.
# For SQLite+aiosqlite, pool params are mostly ignored but do not break.
engine = create_async_engine(
    DATABASE_URL,
    echo=DB_ECHO,              # Log SQL if DB_ECHO=true
    pool_pre_ping=True,        # Validate connections before using them (drops stale ones)
    pool_recycle=1800,         # Recycle connections every 30 minutes
    pool_size=5,               # Reasonable default for this app
    max_overflow=10,           # Allow short bursts
    connect_args=CONNECT_ARGS if DATABASE_URL.startswith("postgresql+asyncpg://") else {},
)

# Session factory: expire_on_commit=False to keep objects usable after commit
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# --------- 4) Public helpers ---------
async def init_db(create_all: bool = True) -> None:
    """
    Initialize database:
    - Create tables (optional, default True)
    - Do a quick connectivity check
    """
    # Lazy import to avoid circular import at module load time.
    try:
        from models import PriceSample, Opportunity  # noqa: F401  (used by metadata)
    except Exception as e:
        # We don't fail hard here; allow running healthcheck first if needed.
        print(f"[db] models import warning: {e}")

    if create_all:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Lightweight health check
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def db_healthcheck() -> bool:
    """
    Return True if a trivial SELECT works, else False.
    Useful for /healthz endpoint or startup probe.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"[db] healthcheck failed: {e}")
        return False


async def get_session() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency-style session provider:
    Usage:
        @router.get("/items")
        async def handler(db: AsyncSession = Depends(get_session)):
            ...
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            # Any explicit cleanup can go here; context manager handles close.
            ...


__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "init_db",
    "db_healthcheck",
    "get_session",
]
