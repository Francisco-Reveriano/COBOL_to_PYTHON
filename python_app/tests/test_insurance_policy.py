"""Unit tests for the GenApp insurance policy service."""

from __future__ import annotations

import datetime as _dt

import pytest
from sqlalchemy.orm import Session

from app.insurance import services
from app.insurance.models import InsuranceCustomer, Policy
from app.insurance.schemas import (
    CommercialDetails,
    EndowmentDetails,
    HouseDetails,
    MotorDetails,
)
from app.services.errors import IntegrityError, NotFoundError


def _make_customer(session: Session) -> InsuranceCustomer:
    return services.add_customer(
        session,
        first_name="Alice",
        last_name="Wong",
        date_of_birth=_dt.date(1985, 3, 12),
    )


def _make_endowment(session: Session, customer_number: int) -> Policy:
    return services.add_policy(
        session,
        customer_number=customer_number,
        issue_date=_dt.date(2024, 1, 1),
        expiry_date=_dt.date(2049, 1, 1),
        broker_id=42,
        brokers_reference="ENDOW-001",
        payment=350,
        details=EndowmentDetails(
            with_profits=True,
            equities=False,
            managed_fund=True,
            fund_name="GROWTH",
            term=25,
            sum_assured=150_000,
            life_assured="Alice Wong",
        ),
    )


def test_add_endowment_policy_creates_header_and_sub_row(session: Session) -> None:
    cust = _make_customer(session)
    policy = _make_endowment(session, cust.customer_number)

    assert policy.policy_number >= 1
    assert policy.policy_type == "E"
    assert policy.endowment is not None
    assert policy.endowment.fund_name == "GROWTH"
    assert policy.endowment.sum_assured == 150_000


def test_add_house_policy(session: Session) -> None:
    cust = _make_customer(session)
    p = services.add_policy(
        session,
        customer_number=cust.customer_number,
        issue_date=_dt.date(2024, 6, 1),
        expiry_date=_dt.date(2025, 6, 1),
        details=HouseDetails(
            property_type="Detached",
            bedrooms=4,
            value=450_000,
            house_name="Maple",
            house_number="12",
            postcode="SO21 2JN",
        ),
    )
    assert p.house is not None
    assert p.house.value == 450_000


def test_add_motor_policy(session: Session) -> None:
    cust = _make_customer(session)
    p = services.add_policy(
        session,
        customer_number=cust.customer_number,
        issue_date=_dt.date(2024, 3, 10),
        expiry_date=_dt.date(2025, 3, 10),
        details=MotorDetails(
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
    )
    assert p.motor is not None
    assert p.motor.make == "Toyota"


def test_add_commercial_policy(session: Session) -> None:
    cust = _make_customer(session)
    p = services.add_policy(
        session,
        customer_number=cust.customer_number,
        issue_date=_dt.date(2024, 2, 1),
        expiry_date=_dt.date(2025, 2, 1),
        details=CommercialDetails(
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
    )
    assert p.commercial is not None
    assert p.commercial.fire_premium == 1200


def test_add_policy_for_unknown_customer_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        services.add_policy(
            session,
            customer_number=99_999,
            issue_date=_dt.date(2024, 1, 1),
            expiry_date=_dt.date(2025, 1, 1),
            details=HouseDetails(),
        )


def test_inquire_policy_returns_loaded_row(session: Session) -> None:
    cust = _make_customer(session)
    p = _make_endowment(session, cust.customer_number)
    found = services.inquire_policy(session, p.policy_number)
    assert found.policy_number == p.policy_number
    assert found.policy_type == "E"


def test_inquire_missing_policy_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        services.inquire_policy(session, 9999)


def test_list_policies_for_customer(session: Session) -> None:
    cust = _make_customer(session)
    p1 = _make_endowment(session, cust.customer_number)
    p2 = services.add_policy(
        session,
        customer_number=cust.customer_number,
        issue_date=_dt.date(2024, 6, 1),
        expiry_date=_dt.date(2025, 6, 1),
        details=HouseDetails(property_type="Flat", bedrooms=2, value=180_000),
    )
    listed = services.list_policies_for_customer(session, cust.customer_number)
    assert [p.policy_number for p in listed] == [p1.policy_number, p2.policy_number]


def test_list_policies_unknown_customer_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        services.list_policies_for_customer(session, 9999)


def test_update_policy_header_only(session: Session) -> None:
    cust = _make_customer(session)
    p = _make_endowment(session, cust.customer_number)
    updated = services.update_policy(
        session,
        p.policy_number,
        payment=999,
        brokers_reference="ENDOW-XYZ",
    )
    assert updated.payment == 999
    assert updated.brokers_reference == "ENDOW-XYZ"


def test_update_policy_details_in_place(session: Session) -> None:
    cust = _make_customer(session)
    p = _make_endowment(session, cust.customer_number)
    new_details = EndowmentDetails(
        with_profits=False,
        equities=True,
        managed_fund=False,
        fund_name="EQUITY",
        term=30,
        sum_assured=200_000,
        life_assured="Alice W Wong",
    )
    updated = services.update_policy(session, p.policy_number, details=new_details)
    assert updated.endowment is not None
    assert updated.endowment.fund_name == "EQUITY"
    assert updated.endowment.sum_assured == 200_000


def test_update_policy_cross_type_rejected(session: Session) -> None:
    cust = _make_customer(session)
    p = _make_endowment(session, cust.customer_number)
    with pytest.raises(IntegrityError):
        services.update_policy(
            session,
            p.policy_number,
            details=HouseDetails(property_type="Detached", bedrooms=3, value=100_000),
        )


def test_update_missing_policy_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        services.update_policy(session, 9999, payment=1)


def test_delete_policy_cascades(session: Session) -> None:
    cust = _make_customer(session)
    p = _make_endowment(session, cust.customer_number)
    services.add_claim(
        session,
        policy_number=p.policy_number,
        claim_date=_dt.date(2024, 12, 1),
        value=5_000,
        paid=4_500,
        cause="Storm damage",
        observations="Quick settle",
    )

    services.delete_policy(session, p.policy_number)

    with pytest.raises(NotFoundError):
        services.inquire_policy(session, p.policy_number)
    # Claim should also be gone via FK cascade
    with pytest.raises(NotFoundError):
        services.list_claims_for_policy(session, p.policy_number)


def test_delete_missing_policy_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        services.delete_policy(session, 9999)


def test_add_claim_and_list(session: Session) -> None:
    cust = _make_customer(session)
    p = _make_endowment(session, cust.customer_number)
    services.add_claim(
        session,
        policy_number=p.policy_number,
        claim_date=_dt.date(2024, 7, 4),
        value=2_500,
        paid=2_000,
        cause="Burglary",
        observations="Awaiting police report",
    )
    claims = services.list_claims_for_policy(session, p.policy_number)
    assert len(claims) == 1
    assert claims[0].cause == "Burglary"


def test_add_claim_unknown_policy_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        services.add_claim(
            session,
            policy_number=9999,
            claim_date=_dt.date(2024, 7, 4),
            value=100,
        )


def test_increment_stat_rejects_unknown_key(session: Session) -> None:
    with pytest.raises(ValueError):
        services.increment_stat(session, "bogus")


def test_list_claims_unknown_policy_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        services.list_claims_for_policy(session, 9999)


def test_update_endowment_to_house_then_back(session: Session) -> None:
    """Field-level updates on each sub-type — exercises _update_sub_type branches."""
    cust = _make_customer(session)

    # House sub-type updated
    house = services.add_policy(
        session,
        customer_number=cust.customer_number,
        issue_date=_dt.date(2024, 6, 1),
        expiry_date=_dt.date(2025, 6, 1),
        details=HouseDetails(property_type="Flat", bedrooms=2, value=180_000),
    )
    services.update_policy(
        session,
        house.policy_number,
        details=HouseDetails(
            property_type="Detached",
            bedrooms=5,
            value=600_000,
            house_name="Oak",
            house_number="9",
            postcode="SO21 2JN",
        ),
    )
    assert house.house is not None
    assert house.house.bedrooms == 5

    # Motor sub-type updated
    motor = services.add_policy(
        session,
        customer_number=cust.customer_number,
        issue_date=_dt.date(2024, 3, 10),
        expiry_date=_dt.date(2025, 3, 10),
        details=MotorDetails(make="Toyota", model="Yaris", value=12_000),
    )
    services.update_policy(
        session,
        motor.policy_number,
        details=MotorDetails(
            make="Honda",
            model="Civic",
            value=15_000,
            reg_number="ZZ99ZZZ",
            colour="BLACK",
            cc=1500,
            manufactured="2023-01",
            premium=700,
            accidents=1,
        ),
    )
    assert motor.motor is not None
    assert motor.motor.make == "Honda"

    # Commercial sub-type updated
    commercial = services.add_policy(
        session,
        customer_number=cust.customer_number,
        issue_date=_dt.date(2024, 2, 1),
        expiry_date=_dt.date(2025, 2, 1),
        details=CommercialDetails(address="old", customer_text="Old Co"),
    )
    services.update_policy(
        session,
        commercial.policy_number,
        details=CommercialDetails(
            address="new",
            postcode="AB1 2CD",
            customer_text="New Co",
            prop_type="Office",
            fire_peril=10,
            fire_premium=100,
            crime_peril=5,
            crime_premium=50,
            flood_peril=2,
            flood_premium=20,
            weather_peril=1,
            weather_premium=10,
            status=2,
            reject_reason="",
        ),
    )
    assert commercial.commercial is not None
    assert commercial.commercial.address == "new"


def test_stats_track_policy_operations(session: Session) -> None:
    cust = _make_customer(session)
    p = _make_endowment(session, cust.customer_number)
    services.inquire_policy(session, p.policy_number)
    services.update_policy(session, p.policy_number, payment=500)
    services.add_claim(
        session,
        policy_number=p.policy_number,
        claim_date=_dt.date(2024, 7, 4),
        value=100,
    )
    services.delete_policy(session, p.policy_number)

    stats = services.get_stats(session)
    assert stats.add_policy == 1
    assert stats.inquire_policy == 1
    assert stats.update_policy == 1
    assert stats.delete_policy == 1
    assert stats.add_claim == 1
