"""Control table — from ``CONTDB2.cpy`` / ``CONTROLI.cpy``.

Replaces the CICS Named Counter Server (NCS) used by the COBOL programs to
allocate the next CUSTOMER / ACCOUNT number.  Atomicity is achieved via a
``SELECT … FOR UPDATE`` on the row (see ``app.services.account_service``).
"""

from __future__ import annotations

from sqlalchemy import CHAR, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Control(Base):
    __tablename__ = "control"

    name: Mapped[str] = mapped_column(CHAR(32), primary_key=True)
    value_num: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    value_str: Mapped[str] = mapped_column(CHAR(40), nullable=False, default="")
