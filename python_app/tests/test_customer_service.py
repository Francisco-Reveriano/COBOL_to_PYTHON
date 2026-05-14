"""Unit tests for the customer service (ports of CRECUST / INQCUST / UPDCUST / DELCUS)."""

from __future__ import annotations

import datetime as _dt

import pytest

from app.services import account_service, customer_service
from app.services.errors import NotFoundError


def _make_customer(session, **overrides):
    payload = {
        "name": "Test Customer",
        "address": "1 Test St",
        "date_of_birth": _dt.date(1990, 1, 1),
        "credit_score": 700,
    }
    payload.update(overrides)
    return customer_service.create_customer(session, **payload)


def test_create_customer_assigns_sequential_numbers(session):
    a = _make_customer(session, name="A")
    b = _make_customer(session, name="B")
    assert int(b.number) == int(a.number) + 1
    assert a.sortcode == "987654"
    assert a.eyecatcher == "CUST"


def test_get_customer_returns_existing_record(session):
    c = _make_customer(session)
    found = customer_service.get_customer(session, c.number)
    assert found.name == "Test Customer"


def test_get_customer_raises_for_missing_record(session):
    with pytest.raises(NotFoundError):
        customer_service.get_customer(session, 9999999999)


def test_update_customer_only_changes_supplied_fields(session):
    c = _make_customer(session)
    customer_service.update_customer(session, c.number, address="2 New St")
    refreshed = customer_service.get_customer(session, c.number)
    assert refreshed.address == "2 New St"
    assert refreshed.name == "Test Customer"  # unchanged


def test_delete_customer_cascades_accounts(session):
    c = _make_customer(session)
    account_service.create_account(
        session, customer_number=c.number, account_type="CURRENT"
    )
    account_service.create_account(
        session, customer_number=c.number, account_type="SAVING"
    )
    customer_service.delete_customer(session, c.number)
    with pytest.raises(NotFoundError):
        customer_service.get_customer(session, c.number)
    # Cascaded accounts should be gone too.
    from app.models import Account

    remaining = (
        session.query(Account).filter_by(customer_number=c.number).count()
    )
    assert remaining == 0

def test_create_customer_default_cs_review_date_is_today_plus_21_days(session):
    """FR-04: CRECUST stamps CUSTOMER-CS-REVIEW-DATE 21 days in the future."""
    today = _dt.date.today()
    c = customer_service.create_customer(
        session,
        name="Test Review",
        address="1 Test St",
        date_of_birth=_dt.date(1990, 1, 1),
        credit_score=700,  # bypass agency fan-out
    )
    assert c.cs_review_date == today + _dt.timedelta(days=21), (
        f"expected today+21d ({today + _dt.timedelta(days=21)}), got {c.cs_review_date}"
    )


def test_create_customer_explicit_cs_review_date_is_preserved(session):
    """Caller-supplied cs_review_date overrides the +21 default."""
    explicit = _dt.date(2030, 1, 15)
    c = customer_service.create_customer(
        session,
        name="Test Explicit Review",
        address="2 Test St",
        date_of_birth=_dt.date(1990, 1, 1),
        credit_score=700,
        cs_review_date=explicit,
    )
    assert c.cs_review_date == explicit
