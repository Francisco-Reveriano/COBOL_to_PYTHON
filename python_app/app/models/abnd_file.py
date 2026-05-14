"""Abend-audit table — from ``ABNDINFO.cpy`` / ``ABNDPROC.cbl``.

The COBOL ``ABNDPROC`` program writes one row to the centralised
``ABNDFILE`` KSDS dataset whenever an application abend is detected,
so operators can review failures from a single place.  The Python
port mirrors that with a relational ``abnd_file`` table plus a
structured ``app.abend`` log line written from
:func:`app.services.abend_service.record_abend`.

Only the COBOL fields that survive the port to Python are kept;
CICS-specific items (``ABND-UTIME-KEY``/``ABND-TASKNO-KEY``/
``ABND-APPLID``/``ABND-RESPCODE``/``ABND-RESP2CODE``) are dropped
because they have no FastAPI equivalent.  See SDD §7.3 for the
full mapping.
"""

from __future__ import annotations

import datetime as _dt

from sqlalchemy import CHAR, Date, DateTime, Integer, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AbndFile(Base):
    __tablename__ = "abnd_file"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eyecatcher: Mapped[str] = mapped_column(CHAR(4), default="ABND", nullable=False)
    abend_code: Mapped[str] = mapped_column(CHAR(4), nullable=False)
    program: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[_dt.date] = mapped_column(Date, nullable=False)
    time: Mapped[_dt.time] = mapped_column(Time, nullable=False)
    sqlcode: Mapped[int | None] = mapped_column(Integer, nullable=True)
    freeform: Mapped[str] = mapped_column(String(600), nullable=False, default="")
    tran_id: Mapped[str | None] = mapped_column(CHAR(4), nullable=True)
    created_at: Mapped[_dt.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


# Default abend code used by the global FastAPI exception handler when an
# uncaught Python exception bubbles out of a service layer.
ABEND_CODE_PYTHON_EXCEPTION = "PYEX"
