"""Unit tests for the GenApp insurance customer service."""

from __future__ import annotations

import datetime as _dt

import pytest
from sqlalchemy.orm import Session

from app.insurance import services
from app.insurance.models import InsuranceCustomer
from app.services.errors import NotFoundError


def _make(session: Session, **overrides: object) -> InsuranceCustomer:
    base: dict[str, object] = {
        "first_name": "Alice",
        "last_name": "Wong",
        "date_of_birth": _dt.date(1985, 3, 12),
        "house_name": "Maple",
        "house_number": "12",
        "postcode": "SO21 2JN",
        "phone_mobile": "+44 7700 900001",
        "phone_home": "+44 1962 000001",
        "email_address": "alice@example.com",
    }
    base.update(overrides)
    return services.add_customer(session, **base)  # type: ignore[arg-type]


def test_add_customer_allocates_sequential_numbers(session: Session) -> None:
    c1 = _make(session)
    c2 = _make(session, first_name="Bob", last_name="Singh")
    c3 = _make(session, first_name="Carol", last_name="Patel")

    assert (c1.customer_number, c2.customer_number, c3.customer_number) == (1, 2, 3)


def test_inquire_customer_returns_row(session: Session) -> None:
    c = _make(session)
    found = services.inquire_customer(session, c.customer_number)
    assert found.customer_number == c.customer_number
    assert found.first_name == "Alice"


def test_inquire_missing_customer_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        services.inquire_customer(session, 9999)


def test_update_customer_changes_only_supplied_fields(session: Session) -> None:
    c = _make(session)
    updated = services.update_customer(
        session,
        c.customer_number,
        phone_mobile="+44 7700 999999",
        email_address="alice@new.example.com",
    )
    assert updated.phone_mobile == "+44 7700 999999"
    assert updated.email_address == "alice@new.example.com"
    # untouched
    assert updated.first_name == "Alice"
    assert updated.house_name == "Maple"


def test_update_missing_customer_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        services.update_customer(session, 9999, first_name="Nobody")


def test_stats_track_customer_operations(session: Session) -> None:
    c = _make(session)
    services.inquire_customer(session, c.customer_number)
    services.update_customer(session, c.customer_number, first_name="Alicia")

    stats = services.get_stats(session)
    assert stats.add_customer == 1
    assert stats.inquire_customer == 1
    assert stats.update_customer == 1


def test_setup_counters_is_idempotent(session: Session) -> None:
    services.setup_counters(session)
    services.setup_counters(session)
    # Sanity: no exceptions, and counters all start at zero.
    stats = services.get_stats(session)
    assert all(getattr(stats, k) == 0 for k in stats.model_fields)
