"""Database engine and session management.

The engine URL comes from :class:`app.core.config.Settings.database_url` so it
can be overridden per environment (PostgreSQL in production, SQLite in tests).
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _build_engine(url: str) -> Engine:
    connect_args: dict[str, object] = {}
    kwargs: dict[str, object] = {"future": True}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        # In-memory SQLite is per-connection; pin one connection so the whole
        # app (and the FastAPI TestClient) shares a single database.
        if ":memory:" in url or url.endswith("sqlite://"):
            kwargs["poolclass"] = StaticPool
    return create_engine(url, connect_args=connect_args, **kwargs)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _build_engine(get_settings().database_url)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False, future=True
        )
    return _SessionLocal


def reset_engine_for_testing(url: str) -> Engine:
    """Reset the cached engine/session factory (used by the test suite)."""
    global _engine, _SessionLocal
    _engine = _build_engine(url)
    _SessionLocal = sessionmaker(
        bind=_engine, autoflush=False, expire_on_commit=False, future=True
    )
    return _engine


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a SQLAlchemy session."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
