"""
Async SQLAlchemy engine + session factory.

Windows compatibility
---------------------
On Python 3.12+ Windows, asyncpg works correctly with the default
ProactorEventLoop that Python uses automatically -- no manual policy
manipulation needed or wanted (set_event_loop_policy is deprecated in
3.12 and removed in 3.16).

The only requirement is that the engine and session factory are created
LAZILY -- i.e. only after uvicorn's event loop is already running, not
at module import time. This is why _engine and _session_maker start as
None and are initialised on the first real request.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# ── Lazy singletons ───────────────────────────────────────────────────────────
# Both are None at import time. Initialised on first request.
# This means importing this module is always instant and never touches
# the network, DNS, or event loop.

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def _get_session_maker() -> async_sessionmaker[AsyncSession]:
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_maker


def get_engine_or_none() -> AsyncEngine | None:
    """Return the engine if initialised, None otherwise.
    Used by main.py lifespan to safely dispose on shutdown."""
    return _engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a scoped async DB session per request."""
    async with _get_session_maker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()