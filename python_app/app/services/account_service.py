"""Account service — ports the COBOL ACCOUNT programs.

* ``CREACC.cbl``  → :func:`create_account` (CONTROL row lock + 10-account cap)
* ``INQACC.cbl``  → :func:`get_account`
* ``INQACCCU.cbl``→ :func:`get_accounts_for_customer`
* ``UPDACC.cbl``  → :func:`update_account`
* ``DELACC.cbl``  → :func:`delete_account`
"""

from __future__ import annotations

import datetime as _dt
import decimal as _d
from collections.abc import Sequence

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Account, Control, ProcTran
from app.models.proctran import (
    PROC_TYPE_BRANCH_CREATE_ACCOUNT,
    PROC_TYPE_BRANCH_DELETE_ACCOUNT,
)
from app.services.common import (
    control_name_for_account_count,
    control_name_for_account_last,
    fmt_account_number,
    now,
    sort_code,
    today,
)
from app.services.customer_service import get_customer
from app.services.errors import (
    InvalidAccountTypeError,
    NotFoundError,
    TooManyAccountsError,
)

VALID_ACCOUNT_TYPES = frozenset(
    {"ISA", "MORTGAGE", "SAVING", "CURRENT", "LOAN"}
)
MAX_ACCOUNTS_PER_CUSTOMER = 10


def _validate_account_type(account_type: str) -> str:
    """Replicates ``CREACC.cbl`` ``ACCOUNT-TYPE-CHECK`` (line 1209)."""
    t = (account_type or "").strip().upper()
    if t not in VALID_ACCOUNT_TYPES:
        raise InvalidAccountTypeError(
            f"Account type {account_type!r} is not one of {sorted(VALID_ACCOUNT_TYPES)}"
        )
    return t


def _ensure_control(session: Session, name: str) -> Control:
    stmt = select(Control).where(Control.name == name).with_for_update()
    row = session.execute(stmt).scalar_one_or_none()
    if row is None:
        row = Control(name=name, value_num=0, value_str="")
        session.add(row)
        session.flush()
    return row


def create_account(
    session: Session,
    *,
    customer_number: int | str,
    account_type: str,
    interest_rate: _d.Decimal = _d.Decimal("0.00"),
    overdraft_limit: int = 0,
    opened: _dt.date | None = None,
) -> Account:
    """Create a new account for a customer (port of ``CREACC.cbl``).

    1. Validate the customer exists (LINK to ``INQCUST``).
    2. Reject if the customer already has 10 accounts.
    3. Validate the account type.
    4. ``SELECT … FOR UPDATE`` on the ``CONTROL`` row holding ``ACCOUNT-LAST``
       (replaces CICS Named Counter ENQ / DEQ).
    5. Increment the counter, insert the ``ACCOUNT`` row, and write the
       ``OCA`` PROCTRAN.
    """
    cust = get_customer(session, customer_number)

    existing = (
        session.execute(
            select(func.count(Account.number)).where(
                Account.customer_number == cust.number
            )
        ).scalar_one()
    )
    if existing >= MAX_ACCOUNTS_PER_CUSTOMER:
        raise TooManyAccountsError(
            f"Customer {cust.number} already has {existing} accounts (max "
            f"{MAX_ACCOUNTS_PER_CUSTOMER})"
        )

    acc_type = _validate_account_type(account_type)
    sc = sort_code()
    opened = opened or today()
    last_stmt = opened
    next_stmt = opened + relativedelta(months=1)

    count = _ensure_control(session, control_name_for_account_count(sc))
    last = _ensure_control(session, control_name_for_account_last(sc))
    new_number = last.value_num + 1
    last.value_num = new_number
    count.value_num = count.value_num + 1

    account = Account(
        eyecatcher="ACCT",
        customer_number=cust.number,
        sortcode=sc,
        number=fmt_account_number(new_number),
        type=acc_type,
        interest_rate=interest_rate,
        opened=opened,
        overdraft_limit=overdraft_limit,
        last_statement=last_stmt,
        next_statement=next_stmt,
        available_balance=_d.Decimal("0.00"),
        actual_balance=_d.Decimal("0.00"),
    )
    session.add(account)
    session.flush()

    n = now()
    session.add(
        ProcTran(
            eyecatcher="PRTR",
            sortcode=account.sortcode,
            number=account.number,
            date=n.date(),
            time=n.time().replace(microsecond=0),
            ref="",
            type=PROC_TYPE_BRANCH_CREATE_ACCOUNT,
            description=(
                f"{cust.number}{acc_type:<8}"
                f"{last_stmt.strftime('%d%m%Y')}{next_stmt.strftime('%d%m%Y')}"
            )[:40],
            amount=_d.Decimal("0.00"),
        )
    )
    session.flush()
    return account


def get_account(session: Session, number: int | str) -> Account:
    """Read a single account (port of ``INQACC.cbl``)."""
    sc = sort_code()
    stmt = select(Account).where(
        Account.sortcode == sc, Account.number == fmt_account_number(number)
    )
    row = session.execute(stmt).scalar_one_or_none()
    if row is None:
        raise NotFoundError(f"Account {number} not found")
    return row


def get_accounts_for_customer(
    session: Session, customer_number: int | str
) -> Sequence[Account]:
    """Read all accounts for a customer (port of ``INQACCCU.cbl``).

    Raises :class:`NotFoundError` if the customer does not exist (this
    mirrors how ``INQACCCU`` is normally called after ``INQCUST``).
    """
    cust = get_customer(session, customer_number)
    stmt = (
        select(Account)
        .where(Account.customer_number == cust.number)
        .order_by(Account.number)
    )
    return session.execute(stmt).scalars().all()


def update_account(
    session: Session,
    number: int | str,
    *,
    account_type: str | None = None,
    interest_rate: _d.Decimal | None = None,
    overdraft_limit: int | None = None,
    last_statement: _dt.date | None = None,
    next_statement: _dt.date | None = None,
) -> Account:
    """Update an account (port of ``UPDACC.cbl``).

    ``UPDACC.cbl`` updates ``ACCOUNT_TYPE``, ``ACCOUNT_INTEREST_RATE`` and
    ``ACCOUNT_OVERDRAFT_LIMIT``.  We additionally accept the two statement
    dates so the same call can drive the statement-date update used by
    other COBOL programs.
    """
    account = get_account(session, number)
    if account_type is not None:
        account.type = _validate_account_type(account_type)
    if interest_rate is not None:
        account.interest_rate = interest_rate
    if overdraft_limit is not None:
        account.overdraft_limit = overdraft_limit
    if last_statement is not None:
        account.last_statement = last_statement
    if next_statement is not None:
        account.next_statement = next_statement
    session.flush()
    return account


def delete_account(session: Session, number: int | str) -> Account:
    """Delete an account and write the ``ODA`` PROCTRAN (port of ``DELACC.cbl``)."""
    account = get_account(session, number)

    n = now()
    session.add(
        ProcTran(
            eyecatcher="PRTR",
            sortcode=account.sortcode,
            number=account.number,
            date=n.date(),
            time=n.time().replace(microsecond=0),
            ref="",
            type=PROC_TYPE_BRANCH_DELETE_ACCOUNT,
            description=(
                f"{account.customer_number}{account.type:<8}DELETE"
            )[:40],
            amount=account.actual_balance,
        )
    )
    session.delete(account)

    sc = sort_code()
    count = _ensure_control(session, control_name_for_account_count(sc))
    if count.value_num > 0:
        count.value_num -= 1
    session.flush()
    return account


__all__ = [
    "create_account",
    "delete_account",
    "get_account",
    "get_accounts_for_customer",
    "update_account",
]
