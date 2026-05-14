"""Customer table — migrated from VSAM (``CUSTOMER.cpy``)."""

from __future__ import annotations

import datetime as _dt

from sqlalchemy import CHAR, Date, Integer, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Customer(Base):
    __tablename__ = "customer"
    __table_args__ = (PrimaryKeyConstraint("sortcode", "number", name="pk_customer"),)

    eyecatcher: Mapped[str] = mapped_column(CHAR(4), default="CUST", nullable=False)
    sortcode: Mapped[str] = mapped_column(CHAR(6), nullable=False)
    number: Mapped[str] = mapped_column(CHAR(10), nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    address: Mapped[str] = mapped_column(String(160), nullable=False)
    date_of_birth: Mapped[_dt.date] = mapped_column(Date, nullable=False)
    credit_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cs_review_date: Mapped[_dt.date] = mapped_column(Date, nullable=False)
