"""Abend-recording service — Python port of ``ABNDPROC.cbl``.

The COBOL ``ABNDPROC`` program writes one row to the ``ABNDFILE``
KSDS dataset for every detected application abend (FR-07).  In the
FastAPI port the row goes to the ``abnd_file`` relational table via
:class:`app.models.abnd_file.AbndFile`, and a single structured log
event is emitted on the ``app.abend`` logger so the same record is
visible to log-aggregation tooling.

A short-window idempotency guard collapses identical bursts of the
same abend (same ``abend_code``/``program``/``freeform`` within one
second) into a single row, to avoid the runaway-amplification
problem you can get when an exception is wrapped and re-raised by
multiple layers of middleware.

``structlog`` will replace stdlib ``logging`` in a Phase 3 PR — for
now we use ``logging.getLogger("app.abend").error(...)`` with the
record fields passed via the ``extra=`` keyword.
"""

from __future__ import annotations

import datetime as _dt
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AbndFile
from app.models.abnd_file import ABEND_CODE_PYTHON_EXCEPTION

logger = logging.getLogger("app.abend")

# Window for the idempotency guard.  Two identical abends arriving within
# this window count as the same event.
IDEMPOTENCY_WINDOW = _dt.timedelta(seconds=1)

# Maximum length of the COBOL ``ABND-FREEFORM`` field (PIC X(600)).
FREEFORM_MAX_LEN = 600


__all__ = [
    "ABEND_CODE_PYTHON_EXCEPTION",
    "FREEFORM_MAX_LEN",
    "IDEMPOTENCY_WINDOW",
    "logger",
    "record_abend",
]


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[:limit]


def record_abend(
    session: Session,
    *,
    abend_code: str,
    program: str,
    freeform: str,
    sqlcode: int | None = None,
    tran_id: str | None = None,
) -> AbndFile:
    """Persist one ``AbndFile`` row and emit a structured log event.

    Mirrors ``ABNDPROC.cbl``: in COBOL the program writes one TS-queue
    entry plus one ``ABNDFILE`` record; here we emit one ``app.abend``
    log line plus one ``abnd_file`` row.

    A duplicate row written within :data:`IDEMPOTENCY_WINDOW` is
    suppressed and the previously-stored ``AbndFile`` is returned
    unchanged.
    """
    abend_code = abend_code[:4]
    program = _truncate(program, 20)
    freeform = _truncate(freeform, FREEFORM_MAX_LEN)
    tran_id_value: str | None = tran_id[:4] if tran_id is not None else None

    cutoff = _dt.datetime.now() - IDEMPOTENCY_WINDOW
    existing = session.execute(
        select(AbndFile)
        .where(
            AbndFile.abend_code == abend_code,
            AbndFile.program == program,
            AbndFile.freeform == freeform,
            AbndFile.created_at >= cutoff,
        )
        .order_by(AbndFile.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if existing is not None:
        logger.error(
            "abend (duplicate suppressed)",
            extra={
                "abend_code": abend_code,
                "program": program,
                "sqlcode": sqlcode,
                "tran_id": tran_id_value,
                "ref_id": existing.id,
                "duplicate": True,
            },
        )
        return existing

    n = _dt.datetime.now()
    abnd = AbndFile(
        eyecatcher="ABND",
        abend_code=abend_code,
        program=program,
        date=n.date(),
        time=n.time().replace(microsecond=0),
        sqlcode=sqlcode,
        freeform=freeform,
        tran_id=tran_id_value,
    )
    session.add(abnd)
    session.flush()

    logger.error(
        "abend",
        extra={
            "abend_code": abend_code,
            "program": program,
            "sqlcode": sqlcode,
            "tran_id": tran_id_value,
            "ref_id": abnd.id,
            "freeform": freeform,
        },
    )
    return abnd
