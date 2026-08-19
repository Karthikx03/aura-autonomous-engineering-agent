"""Async SQLAlchemy engine/session plumbing for AURA's memory store.

Keeps a small cache of engines keyed by database URL rather than a single
module-level global so tests can point at an isolated sqlite file without
fighting a cached engine bound to the default ``settings.database_url``.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.memory.models import Base

_engines: dict[str, AsyncEngine] = {}
_sessionmakers: dict[str, async_sessionmaker[AsyncSession]] = {}


def _resolve_url(database_url: str | None) -> str:
    return database_url or get_settings().database_url


def get_engine(database_url: str | None = None) -> AsyncEngine:
    url = _resolve_url(database_url)
    engine = _engines.get(url)
    if engine is None:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        engine = create_async_engine(url, connect_args=connect_args)
        _engines[url] = engine
    return engine


def get_sessionmaker(database_url: str | None = None) -> async_sessionmaker[AsyncSession]:
    url = _resolve_url(database_url)
    factory = _sessionmakers.get(url)
    if factory is None:
        factory = async_sessionmaker(bind=get_engine(url), expire_on_commit=False, class_=AsyncSession)
        _sessionmakers[url] = factory
    return factory


async def init_db(database_url: str | None = None) -> None:
    """Create all tables for the given (or default) database, if missing."""
    engine = get_engine(database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session(database_url: str | None = None) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-``Depends``-friendly async session generator.

    Usage: ``session: AsyncSession = Depends(get_session)``.
    """
    sessionmaker = get_sessionmaker(database_url)
    async with sessionmaker() as session:
        yield session
