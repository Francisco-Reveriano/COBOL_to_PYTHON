"""Processed-transaction table — from ``PROCDB2.cpy`` / ``PROCTRAN.cpy``.

The COBOL ``PROC-TRAN-TYPE`` field is a 3-character code (e.g. ``DEB``,
``CRE``, ``TFR``, ``PDR``, ``OCA`` …); we keep it verbatim here.
"""

from __future__ import annotations

import datetime as _dt
import decimal as _d

from sqlalchemy import CHAR, Date, Integer, Numeric, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProcTran(Base):
    __tablename__ = "proctran"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eyecatcher: Mapped[str] = mapped_column(CHAR(4), default="PRTR", nullable=False)
    sortcode: Mapped[str] = mapped_column(CHAR(6), nullable=False, index=True)
    number: Mapped[str] = mapped_column(CHAR(8), nullable=False, index=True)
    date: Mapped[_dt.date] = mapped_column(Date, nullable=False)
    time: Mapped[_dt.time] = mapped_column(Time, nullable=False)
    ref: Mapped[str] = mapped_column(CHAR(12), nullable=False, default="")
    type: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    description: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    amount: Mapped[_d.Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=_d.Decimal("0.00")
    )


# COBOL PROC-TRAN-TYPE values (see PROCTRAN.cpy).
PROC_TYPE_DEBIT = "DEB"
PROC_TYPE_CREDIT = "CRE"
PROC_TYPE_PAYMENT_DEBIT = "PDR"
PROC_TYPE_PAYMENT_CREDIT = "PCR"
PROC_TYPE_TRANSFER = "TFR"
PROC_TYPE_BRANCH_CREATE_CUSTOMER = "OCC"
PROC_TYPE_BRANCH_DELETE_CUSTOMER = "ODC"
PROC_TYPE_BRANCH_CREATE_ACCOUNT = "OCA"
PROC_TYPE_BRANCH_DELETE_ACCOUNT = "ODA"
