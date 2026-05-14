"""Seed initial GenApp insurance data — port of ``LGSETUP.cbl``.

Idempotent: re-running the script does nothing if the insurance customer
counter has already advanced past zero.

Usage::

    python -m app.db.seed_insurance
"""

from __future__ import annotations

import datetime as _dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.insurance import services as insurance_services
from app.insurance.models import (
    InsuranceCustomer,
    Policy,
)
from app.insurance.schemas import (
    CommercialDetails,
    EndowmentDetails,
    HouseDetails,
    MotorDetails,
)

SEED_CUSTOMERS: list[dict[str, object]] = [
    {
        "first_name": "Alice",
        "last_name": "Wong",
        "date_of_birth": _dt.date(1985, 3, 12),
        "house_name": "Maple",
        "house_number": "12",
        "postcode": "SO21 2JN",
        "phone_mobile": "+44 7700 900001",
        "phone_home": "+44 1962 000001",
        "email_address": "alice.wong@example.com",
        "policies": [
            (
                EndowmentDetails(
                    with_profits=True,
                    equities=False,
                    managed_fund=True,
                    fund_name="GROWTH",
                    term=25,
                    sum_assured=150_000,
                    life_assured="Alice Wong",
                ),
                _dt.date(2024, 1, 15),
                _dt.date(2049, 1, 15),
                42,
                "ENDOW-001",
                350,
            ),
            (
                HouseDetails(
                    property_type="Detached",
                    bedrooms=4,
                    value=450_000,
                    house_name="Maple",
                    house_number="12",
                    postcode="SO21 2JN",
                ),
                _dt.date(2024, 6, 1),
                _dt.date(2025, 6, 1),
                42,
                "HOUSE-001",
                450,
            ),
        ],
    },
    {
        "first_name": "Bob",
        "last_name": "Singh",
        "date_of_birth": _dt.date(1978, 11, 4),
        "house_name": "Birch",
        "house_number": "3",
        "postcode": "MK3 6EB",
        "phone_mobile": "+44 7700 900002",
        "phone_home": "+44 1908 000002",
        "email_address": "bob.singh@example.com",
        "policies": [
            (
                MotorDetails(
                    make="Toyota",
                    model="Corolla",
                    value=18_500,
                    reg_number="AB12CDE",
                    colour="SILVER",
                    cc=1798,
                    manufactured="2022-04",
                    premium=620,
                    accidents=0,
                ),
                _dt.date(2024, 3, 10),
                _dt.date(2025, 3, 10),
                42,
                "MOTOR-001",
                620,
            ),
        ],
    },
    {
        "first_name": "Carol",
        "last_name": "Patel",
        "date_of_birth": _dt.date(1990, 7, 22),
        "house_name": "",
        "house_number": "",
        "postcode": "EC2A 4NE",
        "phone_mobile": "+44 7700 900003",
        "phone_home": "",
        "email_address": "carol.patel@example.com",
        "policies": [
            (
                CommercialDetails(
                    address="100 Bishopsgate, London",
                    postcode="EC2A 4NE",
                    latitude="51.5170",
                    longitude="-0.0810",
                    customer_text="Patel Catering Ltd",
                    prop_type="Restaurant",
                    fire_peril=80,
                    fire_premium=1200,
                    crime_peril=60,
                    crime_premium=800,
                    flood_peril=20,
                    flood_premium=300,
                    weather_peril=15,
                    weather_premium=200,
                    status=1,
                    reject_reason="",
                ),
                _dt.date(2024, 2, 1),
                _dt.date(2025, 2, 1),
                42,
                "COMM-001",
                2500,
            ),
        ],
    },
]


def seed_insurance_data(session: Session) -> None:
    """Populate the insurance domain with the deterministic fixtures.

    No-op if any insurance customer already exists.
    """
    if (
        session.execute(select(InsuranceCustomer).limit(1)).scalar_one_or_none()
        is not None
    ):
        return

    insurance_services.setup_counters(session)

    for entry in SEED_CUSTOMERS:
        cust = insurance_services.add_customer(
            session,
            first_name=str(entry["first_name"]),
            last_name=str(entry["last_name"]),
            date_of_birth=entry["date_of_birth"],  # type: ignore[arg-type]
            house_name=str(entry["house_name"]),
            house_number=str(entry["house_number"]),
            postcode=str(entry["postcode"]),
            phone_mobile=str(entry["phone_mobile"]),
            phone_home=str(entry["phone_home"]),
            email_address=str(entry["email_address"]),
        )
        for (
            details,
            issue_date,
            expiry_date,
            broker_id,
            brokers_reference,
            payment,
        ) in entry["policies"]:  # type: ignore[union-attr]
            insurance_services.add_policy(
                session,
                customer_number=cust.customer_number,
                issue_date=issue_date,
                expiry_date=expiry_date,
                broker_id=broker_id,
                brokers_reference=brokers_reference,
                payment=payment,
                details=details,
            )
    session.commit()


def main() -> None:
    factory = get_session_factory()
    with factory() as session:
        seed_insurance_data(session)
        customers = session.execute(select(InsuranceCustomer)).scalars().all()
        policies = session.execute(select(Policy)).scalars().all()
        print(
            f"Seeded {len(customers)} insurance customers and "
            f"{len(policies)} policies."
        )


if __name__ == "__main__":
    main()
