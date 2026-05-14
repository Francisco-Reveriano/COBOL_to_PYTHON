"""Tests for the GenApp insurance seed script."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.seed_insurance import seed_insurance_data
from app.insurance.models import InsuranceCustomer, Policy


def test_seed_creates_customers_and_policies(session: Session) -> None:
    seed_insurance_data(session)
    customers = session.execute(select(InsuranceCustomer)).scalars().all()
    policies = session.execute(select(Policy)).scalars().all()
    assert len(customers) == 3
    # 2 policies for Alice, 1 for Bob, 1 for Carol
    assert len(policies) == 4
    types = sorted(p.policy_type for p in policies)
    assert types == ["C", "E", "H", "M"]


def test_seed_is_idempotent(session: Session) -> None:
    seed_insurance_data(session)
    customers_first = session.execute(select(InsuranceCustomer)).scalars().all()
    seed_insurance_data(session)
    customers_second = session.execute(select(InsuranceCustomer)).scalars().all()
    assert len(customers_first) == len(customers_second)
