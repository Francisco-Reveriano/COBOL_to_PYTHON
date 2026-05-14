"""Shared helpers used by the service layer.

Mostly small utilities that mirror COBOL idioms (left-padded numeric strings,
``CONTROL`` row naming convention, today's date, etc.).
"""

from __future__ import annotations

import datetime as _dt

from app.core.config import get_settings


def sort_code() -> str:
    """Return the fixed sort code (was ``GETSCODE.cbl`` / ``SORTCODE.cpy``)."""
    return get_settings().sort_code


def fmt_account_number(value: int | str) -> str:
    """COBOL ``ACCOUNT_NUMBER`` is ``CHAR(8)`` — zero-pad to 8 digits."""
    n = int(str(value).strip())
    if n < 0 or n > 99_999_999:
        raise ValueError(f"Account number {value!r} does not fit in CHAR(8)")
    return f"{n:08d}"


def fmt_customer_number(value: int | str) -> str:
    """COBOL ``CUSTOMER_NUMBER`` is ``CHAR(10)`` — zero-pad to 10 digits."""
    n = int(str(value).strip())
    if n < 0 or n > 9_999_999_999:
        raise ValueError(f"Customer number {value!r} does not fit in CHAR(10)")
    return f"{n:010d}"


def control_name_for_customer_count(sortcode: str) -> str:
    return f"{sortcode}-CUSTOMER-COUNT"


def control_name_for_customer_last(sortcode: str) -> str:
    return f"{sortcode}-CUSTOMER-LAST"


def control_name_for_account_count(sortcode: str) -> str:
    return f"{sortcode}-ACCOUNT-COUNT"


def control_name_for_account_last(sortcode: str) -> str:
    return f"{sortcode}-ACCOUNT-LAST"


def today() -> _dt.date:
    return _dt.date.today()


def now() -> _dt.datetime:
    return _dt.datetime.now()
