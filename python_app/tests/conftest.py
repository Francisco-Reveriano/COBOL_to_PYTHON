"""Shared pytest fixtures.

We use an in-memory SQLite database created from the SQLAlchemy metadata
(rather than running Alembic) so the test suite is fast and PostgreSQL is
not required.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

# Make sure tests never touch a real PostgreSQL by pointing at SQLite *before*
# the application's settings are loaded.
os.environ.setdefault("CBSA_DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import (  # noqa: E402
    get_db,
    get_session_factory,
    reset_engine_for_testing,
)
from app.main import app  # noqa: E402
from app.models import Account, Control, Customer, ProcTran  # noqa: E402,F401


@pytest.fixture(autouse=True)
def _fresh_database() -> Iterator[None]:
    """Reset to a fresh in-memory SQLite database per test."""
    engine = reset_engine_for_testing("sqlite:///:memory:")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def session() -> Iterator[Session]:
    factory = get_session_factory()
    with factory() as s:
        yield s


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    """A FastAPI test client that shares the per-test session."""

    def _override_get_db() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
