"""Account table — from ``ACCDB2.cpy`` / ``ACCOUNT.cpy``."""

from __future__ import annotations

import datetime as _dt
import decimal as _d

from sqlalchemy import CHAR, Date, Integer, Numeric, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Account(Base):
    __tablename__ = "account"
    __table_args__ = (
        PrimaryKeyConstraint("sortcode", "number", name="pk_account"),
    )

    eyecatcher: Mapped[str] = mapped_column(CHAR(4), default="ACCT", nullable=False)
    customer_number: Mapped[str] = mapped_column(CHAR(10), nullable=False, index=True)
    sortcode: Mapped[str] = mapped_column(CHAR(6), nullable=False)
    number: Mapped[str] = mapped_column(CHAR(8), nullable=False)
    type: Mapped[str] = mapped_column(CHAR(8), nullable=False)
    interest_rate: Mapped[_d.Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=_d.Decimal("0.00")
    )
    opened: Mapped[_dt.date] = mapped_column(Date, nullable=False)
    overdraft_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_statement: Mapped[_dt.date] = mapped_column(Date, nullable=False)
    next_statement: Mapped[_dt.date] = mapped_column(Date, nullable=False)
    available_balance: Mapped[_d.Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=_d.Decimal("0.00")
    )
    actual_balance: Mapped[_d.Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=_d.Decimal("0.00")
    )
