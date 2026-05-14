"""Seed initial CBSA data.

Port of ``BANKDATA.cbl``.  The COBOL program generates synthetic customers
from a list of street / town names; here we ship a small, deterministic
fixture set so tests and demos are reproducible.

Usage::

    python -m app.db.seed

Idempotent: re-running the script does nothing if customers already exist.
"""

from __future__ import annotations

import datetime as _dt
import decimal as _d

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.models import Account, Control, Customer
from app.services.account_service import create_account
from app.services.common import (
    control_name_for_account_count,
    control_name_for_account_last,
    control_name_for_customer_count,
    control_name_for_customer_last,
    sort_code,
)
from app.services.customer_service import create_customer

SEED_CUSTOMERS: list[dict[str, object]] = [
    {
        "name": "Mr John Smith",
        "address": "1 Oak Lane, Hursley, Winchester, SO21 2JN",
        "date_of_birth": _dt.date(1980, 4, 15),
        "credit_score": 750,
        "accounts": [("CURRENT", _d.Decimal("1.50"), 500),
                     ("SAVING", _d.Decimal("3.25"), 0)],
    },
    {
        "name": "Ms Jane Doe",
        "address": "22 Elm Road, Hursley, Winchester, SO21 2JN",
        "date_of_birth": _dt.date(1992, 11, 3),
        "credit_score": 690,
        "accounts": [("CURRENT", _d.Decimal("1.50"), 250),
                     ("ISA", _d.Decimal("4.10"), 0)],
    },
    {
        "name": "Dr Alan Turing",
        "address": "Bletchley Park, Milton Keynes, MK3 6EB",
        "date_of_birth": _dt.date(1985, 6, 23),
        "credit_score": 820,
        "accounts": [("MORTGAGE", _d.Decimal("2.75"), 0)],
    },
    {
        "name": "Ms Grace Hopper",
        "address": "1 Cobol Way, New York, NY 10001",
        "date_of_birth": _dt.date(1986, 12, 9),
        "credit_score": 800,
        "accounts": [("LOAN", _d.Decimal("5.50"), 0),
                     ("CURRENT", _d.Decimal("1.50"), 1000)],
    },
    {
        "name": "Mr Linus Torvalds",
        "address": "12 Kernel Court, Helsinki, FI-00100",
        "date_of_birth": _dt.date(1969, 12, 28),
        "credit_score": 770,
        "accounts": [("CURRENT", _d.Decimal("1.50"), 500),
                     ("SAVING", _d.Decimal("3.00"), 0)],
    },
]


def seed_bank_data(session: Session) -> None:
    """Populate the database with the deterministic CBSA fixtures.

    No-op if any customer already exists.
    """
    if session.execute(select(Customer).limit(1)).scalar_one_or_none() is not None:
        return

    sc = sort_code()
    # Pre-create the CONTROL rows so the very first INSERT does not race
    # with auto-creation in create_customer/create_account.
    for n in (
        control_name_for_customer_count(sc),
        control_name_for_customer_last(sc),
        control_name_for_account_count(sc),
        control_name_for_account_last(sc),
    ):
        if session.get(Control, n) is None:
            session.add(Control(name=n, value_num=0, value_str=""))
    session.flush()

    for entry in SEED_CUSTOMERS:
        cust = create_customer(
            session,
            name=str(entry["name"]),
            address=str(entry["address"]),
            date_of_birth=entry["date_of_birth"],  # type: ignore[arg-type]
            credit_score=int(entry["credit_score"]),  # type: ignore[arg-type]
        )
        for acc_type, interest, overdraft in entry["accounts"]:  # type: ignore[union-attr]
            create_account(
                session,
                customer_number=cust.number,
                account_type=acc_type,
                interest_rate=interest,
                overdraft_limit=overdraft,
            )
    session.commit()


def main() -> None:
    factory = get_session_factory()
    with factory() as session:
        seed_bank_data(session)
        total_customers = session.execute(select(Customer)).scalars().all()
        total_accounts = session.execute(select(Account)).scalars().all()
        print(
            f"Seeded {len(total_customers)} customers and "
            f"{len(total_accounts)} accounts."
        )


if __name__ == "__main__":
    main()
