"""Seed-script integration test."""

from __future__ import annotations

from app.db.seed import SEED_CUSTOMERS, seed_bank_data
from app.models import Account, Customer


def test_seed_is_idempotent(session):
    seed_bank_data(session)
    seed_bank_data(session)
    assert session.query(Customer).count() == len(SEED_CUSTOMERS)
    expected_accounts = sum(len(c["accounts"]) for c in SEED_CUSTOMERS)  # type: ignore[index]
    assert session.query(Account).count() == expected_accounts
