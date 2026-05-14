"""Unit tests for the account service.

Exercises the rules from CREACC.cbl / UPDACC.cbl / DELACC.cbl, including
the 10-account-per-customer cap and the type validation.
"""

from __future__ import annotations

import datetime as _dt
import decimal as _d

import pytest

from app.services import account_service, customer_service
from app.services.errors import (
    InvalidAccountTypeError,
    NotFoundError,
    TooManyAccountsError,
)


def _customer(session):
    return customer_service.create_customer(
        session,
        name="Test",
        address="1 Test St",
        date_of_birth=_dt.date(1990, 1, 1),
        credit_score=700,
    )


def test_create_account_assigns_sequential_numbers(session):
    c = _customer(session)
    a = account_service.create_account(
        session, customer_number=c.number, account_type="CURRENT"
    )
    b = account_service.create_account(
        session, customer_number=c.number, account_type="SAVING"
    )
    assert int(b.number) == int(a.number) + 1
    assert a.customer_number == c.number
    assert a.sortcode == "987654"
    assert a.interest_rate == _d.Decimal("0.00")


def test_create_account_rejects_unknown_type(session):
    c = _customer(session)
    with pytest.raises(InvalidAccountTypeError):
        account_service.create_account(
            session, customer_number=c.number, account_type="WEIRD"
        )


def test_create_account_enforces_10_account_cap(session):
    """CREACC.cbl line ~347: NUMBER-OF-ACCOUNTS > 9 -> fail code '8'."""
    c = _customer(session)
    for _ in range(10):
        account_service.create_account(
            session, customer_number=c.number, account_type="CURRENT"
        )
    with pytest.raises(TooManyAccountsError) as exc_info:
        account_service.create_account(
            session, customer_number=c.number, account_type="CURRENT"
        )
    assert exc_info.value.fail_code == "8"


def test_get_accounts_for_customer_returns_all(session):
    c = _customer(session)
    a1 = account_service.create_account(
        session, customer_number=c.number, account_type="CURRENT"
    )
    a2 = account_service.create_account(
        session, customer_number=c.number, account_type="SAVING"
    )
    rows = account_service.get_accounts_for_customer(session, c.number)
    assert {a.number for a in rows} == {a1.number, a2.number}


def test_update_account_changes_type_rate_and_overdraft(session):
    c = _customer(session)
    a = account_service.create_account(
        session, customer_number=c.number, account_type="CURRENT"
    )
    account_service.update_account(
        session,
        a.number,
        account_type="SAVING",
        interest_rate=_d.Decimal("4.25"),
        overdraft_limit=1000,
    )
    refreshed = account_service.get_account(session, a.number)
    assert refreshed.type.strip() == "SAVING"
    assert refreshed.interest_rate == _d.Decimal("4.25")
    assert refreshed.overdraft_limit == 1000


def test_delete_account_removes_row(session):
    c = _customer(session)
    a = account_service.create_account(
        session, customer_number=c.number, account_type="CURRENT"
    )
    account_service.delete_account(session, a.number)
    with pytest.raises(NotFoundError):
        account_service.get_account(session, a.number)
