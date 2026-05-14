"""Tests for FR-07 / ``ABNDPROC.cbl`` port.

Covers:
* ``record_abend`` writes one ``AbndFile`` row with the expected fields.
* Idempotency: two identical calls within the 1-second window only
  produce a single row.
* FastAPI global exception handler: an unhandled exception in a route
  results in a 500 with an ``abend_code`` and integer ``ref_id``, and
  exactly one matching ``AbndFile`` row is persisted.
"""

from __future__ import annotations

import datetime as _dt

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import get_session_factory
from app.main import _handle_uncaught_exception, app
from app.models import AbndFile
from app.services.abend_service import (
    ABEND_CODE_PYTHON_EXCEPTION,
    FREEFORM_MAX_LEN,
    record_abend,
)


def test_record_abend_writes_row(session):
    abnd = record_abend(
        session,
        abend_code="ABCD",
        program="/some/path",
        freeform="boom went the dynamite",
        sqlcode=-803,
        tran_id="ZX01",
    )
    session.commit()

    assert abnd.id is not None
    fetched = session.execute(select(AbndFile)).scalars().all()
    assert len(fetched) == 1
    row = fetched[0]
    assert row.eyecatcher == "ABND"
    assert row.abend_code == "ABCD"
    assert row.program == "/some/path"
    assert row.freeform == "boom went the dynamite"
    assert row.sqlcode == -803
    assert row.tran_id == "ZX01"
    assert isinstance(row.date, _dt.date)
    assert isinstance(row.time, _dt.time)
    assert isinstance(row.created_at, _dt.datetime)


def test_record_abend_truncates_long_freeform(session):
    long_text = "x" * (FREEFORM_MAX_LEN + 250)
    abnd = record_abend(session, abend_code="LONG", program="/p", freeform=long_text)
    session.commit()

    assert len(abnd.freeform) == FREEFORM_MAX_LEN


def test_record_abend_truncates_long_program(session):
    program = "/" + ("a" * 50)
    abnd = record_abend(session, abend_code="LONG", program=program, freeform="nope")
    session.commit()

    assert len(abnd.program) == 20


def test_record_abend_is_idempotent_within_window(session):
    first = record_abend(session, abend_code="DUPE", program="/p", freeform="same")
    session.commit()
    second = record_abend(session, abend_code="DUPE", program="/p", freeform="same")
    session.commit()

    assert first.id == second.id
    rows = session.execute(select(AbndFile)).scalars().all()
    assert len(rows) == 1


def test_record_abend_distinct_codes_produce_distinct_rows(session):
    record_abend(session, abend_code="AA01", program="/p", freeform="m")
    record_abend(session, abend_code="AA02", program="/p", freeform="m")
    session.commit()
    rows = session.execute(select(AbndFile)).scalars().all()
    assert len(rows) == 2


def test_global_exception_handler_persists_row_and_returns_500(session):
    """Register a temporary route that raises, hit it, verify the response."""
    # The handler opens a fresh session via ``get_session_factory()`` rather
    # than re-using the request session, so we use a raw TestClient (no
    # dependency overrides) and assert against the same in-memory engine
    # that the conftest fixture set up.

    @app.get("/__test_abend__")
    def _boom() -> None:
        raise RuntimeError("kaboom in test route")

    try:
        with TestClient(app, raise_server_exceptions=False) as raw_client:
            resp = raw_client.get("/__test_abend__")
        assert resp.status_code == 500
        body = resp.json()
        assert body["detail"]["abend_code"] == ABEND_CODE_PYTHON_EXCEPTION
        assert isinstance(body["detail"]["ref_id"], int)
        assert body["detail"]["message"] == "Internal Server Error"

        # Use a fresh session because the row was written via a different
        # session by the handler.
        factory = get_session_factory()
        with factory() as s:
            rows = (
                s.execute(
                    select(AbndFile).where(
                        AbndFile.abend_code == ABEND_CODE_PYTHON_EXCEPTION,
                        AbndFile.program == "/__test_abend__",
                    )
                )
                .scalars()
                .all()
            )
        assert len(rows) == 1
        assert "kaboom in test route" in rows[0].freeform
        assert rows[0].id == body["detail"]["ref_id"]
    finally:
        _remove_route(app, "/__test_abend__")


def test_http_exceptions_pass_through_unmodified(client):
    """``HTTPException`` 4xx responses must not be replaced by the handler."""
    # /customers/<unknown> returns 404 via a proper HTTPException.
    resp = client.get("/customers/9999999999")
    assert resp.status_code == 404
    # Default HTTPException body shape is {"detail": "..."}; the abend
    # handler would have replaced this with a 500 body if it caught it.
    assert "abend_code" not in resp.text


def _remove_route(application: FastAPI, path: str) -> None:
    application.router.routes = [
        r for r in application.router.routes if getattr(r, "path", None) != path
    ]


@pytest.mark.asyncio
async def test_handler_is_async_callable():
    # Smoke-test that the handler exists and is async — guards against
    # accidental signature changes.
    import inspect

    assert inspect.iscoroutinefunction(_handle_uncaught_exception)
