"""FastAPI entrypoint for the CBSA Python port."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import accounts, customers, meta, transfers
from app.db.session import get_session_factory
from app.insurance.router import router as insurance_router
from app.models.abnd_file import ABEND_CODE_PYTHON_EXCEPTION
from app.services.abend_service import record_abend

app = FastAPI(
    title="CBSA Python Port",
    version="0.1.0",
    description=(
        "Python port of the CICS Banking Sample Application (CBSA) and the "
        "GenApp insurance domain.  Business logic was translated from the "
        "COBOL sources in `src/base/cobol_src/` and `cics-genapp/base/src/`; "
        "CICS/DB2/VSAM are replaced with FastAPI, SQLAlchemy, and PostgreSQL."
    ),
)

app.include_router(customers.router)
app.include_router(accounts.router)
app.include_router(transfers.router)
app.include_router(meta.router)
app.include_router(insurance_router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


_abend_logger = logging.getLogger("app.abend")


@app.exception_handler(Exception)
async def _handle_uncaught_exception(request: Request, exc: Exception) -> Response:
    """Global handler: port of ``ABNDPROC.cbl`` for FastAPI.

    HTTP-aware exceptions (``HTTPException``, ``RequestValidationError``)
    are forwarded to FastAPI's default handlers so they return their
    normal 4xx responses unmodified.  Anything else is treated as an
    application abend: we open a fresh DB session (the request-scoped
    one may have been rolled back by the failure), persist one
    ``AbndFile`` row via :func:`app.services.abend_service.record_abend`,
    commit it, and return a 500 with the row's ``ref_id`` so an operator
    can find the audit record.
    """
    if isinstance(exc, StarletteHTTPException):
        return await http_exception_handler(request, exc)
    if isinstance(exc, RequestValidationError):
        return await request_validation_exception_handler(request, exc)

    factory = get_session_factory()
    ref_id: int | None = None
    try:
        with factory() as session:
            try:
                abnd = record_abend(
                    session,
                    abend_code=ABEND_CODE_PYTHON_EXCEPTION,
                    program=request.url.path,
                    freeform=str(exc),
                )
                session.commit()
                ref_id = abnd.id
            except Exception:  # noqa: BLE001 — never let audit failures hide the original
                session.rollback()
                _abend_logger.exception(
                    "failed to persist abnd_file row",
                    extra={
                        "abend_code": ABEND_CODE_PYTHON_EXCEPTION,
                        "program": request.url.path,
                    },
                )
    except Exception:  # noqa: BLE001
        _abend_logger.exception("failed to open abend session")

    _abend_logger.exception(
        "uncaught exception",
        extra={
            "abend_code": ABEND_CODE_PYTHON_EXCEPTION,
            "program": request.url.path,
            "ref_id": ref_id,
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "abend_code": ABEND_CODE_PYTHON_EXCEPTION,
                "ref_id": ref_id,
                "message": "Internal Server Error",
            }
        },
    )
