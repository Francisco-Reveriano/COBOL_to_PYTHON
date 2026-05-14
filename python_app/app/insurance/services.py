"""Service layer for the GenApp insurance domain — SDD §7.2.

This module ports the business logic from ``cics-genapp/base/src/`` while
re-using the existing :class:`app.models.Control` table for named-counter
allocation (so we get the same ``SELECT … FOR UPDATE`` semantics that the
CBSA banking services already rely on).
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.insurance.models import (
    POLICY_TYPE_COMMERCIAL,
    POLICY_TYPE_ENDOWMENT,
    POLICY_TYPE_HOUSE,
    POLICY_TYPE_MOTOR,
    VALID_POLICY_TYPES,
    Claim,
    InsuranceCustomer,
    Policy,
    PolicyCommercial,
    PolicyEndowment,
    PolicyHouse,
    PolicyMotor,
)
from app.insurance.schemas import (
    CommercialDetails,
    EndowmentDetails,
    HouseDetails,
    MotorDetails,
    StatsOut,
)
from app.models import Control
from app.services.errors import IntegrityError, NotFoundError

# ---------------------------------------------------------------------------
# Counter helpers (CICS NCS → CONTROL row + SELECT … FOR UPDATE)
# ---------------------------------------------------------------------------

INSURANCE_CUSTOMER_LAST = "INS-CUSTOMER-LAST"
INSURANCE_CUSTOMER_COUNT = "INS-CUSTOMER-COUNT"

# LGASTAT1 stat counters.  Names are short tokens that match the COBOL
# program suffixes (ACUS = add-customer, ICUS = inquire-customer, etc.).
_STAT_NAMES: dict[str, str] = {
    "add_customer": "INS-STAT-ACUS",
    "inquire_customer": "INS-STAT-ICUS",
    "update_customer": "INS-STAT-UCUS",
    "add_policy": "INS-STAT-APOL",
    "inquire_policy": "INS-STAT-IPOL",
    "update_policy": "INS-STAT-UPOL",
    "delete_policy": "INS-STAT-DPOL",
    "add_claim": "INS-STAT-ACLM",
}


def _ensure_control(session: Session, name: str) -> Control:
    """Get-or-create a ``CONTROL`` row under a row-level lock."""
    stmt = select(Control).where(Control.name == name).with_for_update()
    row = session.execute(stmt).scalar_one_or_none()
    if row is None:
        row = Control(name=name, value_num=0, value_str="")
        session.add(row)
        session.flush()
    return row


def increment_stat(session: Session, stat_key: str) -> int:
    """Bump a LGASTAT1 counter — returns the new value."""
    if stat_key not in _STAT_NAMES:
        raise ValueError(f"Unknown stat key: {stat_key!r}")
    row = _ensure_control(session, _STAT_NAMES[stat_key])
    row.value_num += 1
    session.flush()
    return row.value_num


def get_stats(session: Session) -> StatsOut:
    """Return every LGASTAT1 counter in one object."""
    values: dict[str, int] = {}
    for stat_key, ctrl_name in _STAT_NAMES.items():
        row = session.get(Control, ctrl_name)
        values[stat_key] = row.value_num if row is not None else 0
    return StatsOut(**values)


def setup_counters(session: Session) -> None:
    """Port of ``LGSETUP.cbl`` — pre-create every counter at zero.

    Idempotent: existing counters are left untouched.
    """
    for name in (INSURANCE_CUSTOMER_LAST, INSURANCE_CUSTOMER_COUNT, *_STAT_NAMES.values()):
        if session.get(Control, name) is None:
            session.add(Control(name=name, value_num=0, value_str=""))
    session.flush()


# ---------------------------------------------------------------------------
# Customer service (LGACUS01 / LGICUS01 / LGUCUS01)
# ---------------------------------------------------------------------------


def add_customer(
    session: Session,
    *,
    first_name: str,
    last_name: str,
    date_of_birth: _dt.date,
    house_name: str = "",
    house_number: str = "",
    postcode: str = "",
    phone_mobile: str = "",
    phone_home: str = "",
    email_address: str = "",
) -> InsuranceCustomer:
    """Port of ``LGACUS01`` → ``LGACDB01`` / ``LGACVS01``.

    Allocates the next customer number under a CONTROL-row lock (replaces
    the CICS ``GET COUNTER`` on ``GENACUSTNUM``).
    """
    count = _ensure_control(session, INSURANCE_CUSTOMER_COUNT)
    last = _ensure_control(session, INSURANCE_CUSTOMER_LAST)

    new_number = last.value_num + 1
    last.value_num = new_number
    count.value_num = count.value_num + 1

    customer = InsuranceCustomer(
        customer_number=new_number,
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth,
        house_name=house_name,
        house_number=house_number,
        postcode=postcode,
        phone_mobile=phone_mobile,
        phone_home=phone_home,
        email_address=email_address,
    )
    session.add(customer)
    session.flush()

    increment_stat(session, "add_customer")
    return customer


def inquire_customer(session: Session, customer_number: int) -> InsuranceCustomer:
    """Port of ``LGICUS01`` → ``LGICDB01`` / ``LGICVS01``."""
    row = session.get(InsuranceCustomer, customer_number)
    if row is None:
        raise NotFoundError(f"Insurance customer {customer_number} not found")
    increment_stat(session, "inquire_customer")
    return row


def update_customer(
    session: Session,
    customer_number: int,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    date_of_birth: _dt.date | None = None,
    house_name: str | None = None,
    house_number: str | None = None,
    postcode: str | None = None,
    phone_mobile: str | None = None,
    phone_home: str | None = None,
    email_address: str | None = None,
) -> InsuranceCustomer:
    """Port of ``LGUCUS01`` → ``LGUCDB01`` / ``LGUCVS01``.

    Field-level UPDATE: unset fields are left alone — mirrors the COBOL
    behaviour of moving only spaces-replaced fields into the row.
    """
    row = session.get(InsuranceCustomer, customer_number)
    if row is None:
        raise NotFoundError(f"Insurance customer {customer_number} not found")
    if first_name is not None:
        row.first_name = first_name
    if last_name is not None:
        row.last_name = last_name
    if date_of_birth is not None:
        row.date_of_birth = date_of_birth
    if house_name is not None:
        row.house_name = house_name
    if house_number is not None:
        row.house_number = house_number
    if postcode is not None:
        row.postcode = postcode
    if phone_mobile is not None:
        row.phone_mobile = phone_mobile
    if phone_home is not None:
        row.phone_home = phone_home
    if email_address is not None:
        row.email_address = email_address
    session.flush()

    increment_stat(session, "update_customer")
    return row


# ---------------------------------------------------------------------------
# Policy service (LGAPOL01 / LGIPOL01 / LGUPOL01 / LGDPOL01)
# ---------------------------------------------------------------------------


def _attach_sub_type(
    session: Session,
    policy: Policy,
    details: EndowmentDetails | HouseDetails | MotorDetails | CommercialDetails,
) -> None:
    """Insert the sub-type-specific row for ``policy`` from ``details``."""
    if details.policy_type == POLICY_TYPE_ENDOWMENT:
        assert isinstance(details, EndowmentDetails)  # narrowing for mypy
        session.add(
            PolicyEndowment(
                policy_number=policy.policy_number,
                with_profits=details.with_profits,
                equities=details.equities,
                managed_fund=details.managed_fund,
                fund_name=details.fund_name,
                term=details.term,
                sum_assured=details.sum_assured,
                life_assured=details.life_assured,
            )
        )
    elif details.policy_type == POLICY_TYPE_HOUSE:
        assert isinstance(details, HouseDetails)
        session.add(
            PolicyHouse(
                policy_number=policy.policy_number,
                property_type=details.property_type,
                bedrooms=details.bedrooms,
                value=details.value,
                house_name=details.house_name,
                house_number=details.house_number,
                postcode=details.postcode,
            )
        )
    elif details.policy_type == POLICY_TYPE_MOTOR:
        assert isinstance(details, MotorDetails)
        session.add(
            PolicyMotor(
                policy_number=policy.policy_number,
                make=details.make,
                model=details.model,
                value=details.value,
                reg_number=details.reg_number,
                colour=details.colour,
                cc=details.cc,
                manufactured=details.manufactured,
                premium=details.premium,
                accidents=details.accidents,
            )
        )
    elif details.policy_type == POLICY_TYPE_COMMERCIAL:
        assert isinstance(details, CommercialDetails)
        session.add(
            PolicyCommercial(
                policy_number=policy.policy_number,
                address=details.address,
                postcode=details.postcode,
                latitude=details.latitude,
                longitude=details.longitude,
                customer_text=details.customer_text,
                prop_type=details.prop_type,
                fire_peril=details.fire_peril,
                fire_premium=details.fire_premium,
                crime_peril=details.crime_peril,
                crime_premium=details.crime_premium,
                flood_peril=details.flood_peril,
                flood_premium=details.flood_premium,
                weather_peril=details.weather_peril,
                weather_premium=details.weather_premium,
                status=details.status,
                reject_reason=details.reject_reason,
            )
        )
    else:  # pragma: no cover — guarded by VALID_POLICY_TYPES check
        raise ValueError(f"Unknown policy_type {details.policy_type!r}")
    session.flush()


def _hydrate_details(
    policy: Policy,
) -> EndowmentDetails | HouseDetails | MotorDetails | CommercialDetails:
    """Return the typed sub-type detail object for an already-loaded policy."""
    if policy.policy_type == POLICY_TYPE_ENDOWMENT:
        if policy.endowment is None:
            raise IntegrityError(
                f"Policy {policy.policy_number} marked Endowment but has no row"
            )
        return EndowmentDetails.model_validate(policy.endowment)
    if policy.policy_type == POLICY_TYPE_HOUSE:
        if policy.house is None:
            raise IntegrityError(
                f"Policy {policy.policy_number} marked House but has no row"
            )
        return HouseDetails.model_validate(policy.house)
    if policy.policy_type == POLICY_TYPE_MOTOR:
        if policy.motor is None:
            raise IntegrityError(
                f"Policy {policy.policy_number} marked Motor but has no row"
            )
        return MotorDetails.model_validate(policy.motor)
    if policy.policy_type == POLICY_TYPE_COMMERCIAL:
        if policy.commercial is None:
            raise IntegrityError(
                f"Policy {policy.policy_number} marked Commercial but has no row"
            )
        return CommercialDetails.model_validate(policy.commercial)
    raise IntegrityError(f"Unknown policy_type {policy.policy_type!r}")


def add_policy(
    session: Session,
    *,
    customer_number: int,
    issue_date: _dt.date,
    expiry_date: _dt.date,
    details: EndowmentDetails | HouseDetails | MotorDetails | CommercialDetails,
    broker_id: int = 0,
    brokers_reference: str = "",
    payment: int = 0,
) -> Policy:
    """Port of ``LGAPOL01`` → ``LGAPDB01`` / ``LGAPVS01``.

    The COBOL program inserts the POLICY header row (with DB2 IDENTITY
    auto-allocating POLICYNUMBER) then conditionally inserts the sub-type
    row.  We do the same: header → flush → :func:`_attach_sub_type`.
    """
    if details.policy_type not in VALID_POLICY_TYPES:
        raise IntegrityError(f"Invalid policy_type {details.policy_type!r}")
    if session.get(InsuranceCustomer, customer_number) is None:
        # COBOL: LGAPDB01 returns SQLCODE -530 (FK) when this happens.
        raise NotFoundError(f"Insurance customer {customer_number} not found")

    policy = Policy(
        customer_number=customer_number,
        policy_type=details.policy_type,
        issue_date=issue_date,
        expiry_date=expiry_date,
        broker_id=broker_id,
        brokers_reference=brokers_reference,
        payment=payment,
    )
    session.add(policy)
    session.flush()  # so policy.policy_number is populated

    _attach_sub_type(session, policy, details)

    increment_stat(session, "add_policy")
    return policy


def inquire_policy(session: Session, policy_number: int) -> Policy:
    """Port of ``LGIPOL01`` → ``LGIPDB01`` / ``LGIPVS01``."""
    row = session.get(Policy, policy_number)
    if row is None:
        raise NotFoundError(f"Policy {policy_number} not found")
    increment_stat(session, "inquire_policy")
    return row


def list_policies_for_customer(
    session: Session, customer_number: int
) -> list[Policy]:
    """List every policy for a customer (no direct COBOL equivalent — was a
    BMS scroll list)."""
    if session.get(InsuranceCustomer, customer_number) is None:
        raise NotFoundError(f"Insurance customer {customer_number} not found")
    stmt = (
        select(Policy)
        .where(Policy.customer_number == customer_number)
        .order_by(Policy.policy_number)
    )
    return list(session.execute(stmt).scalars())


def update_policy(
    session: Session,
    policy_number: int,
    *,
    issue_date: _dt.date | None = None,
    expiry_date: _dt.date | None = None,
    broker_id: int | None = None,
    brokers_reference: str | None = None,
    payment: int | None = None,
    details: EndowmentDetails | HouseDetails | MotorDetails | CommercialDetails | None = None,
) -> Policy:
    """Port of ``LGUPOL01`` → ``LGUPDB01`` / ``LGUPVS01``.

    Header-level fields are field-updated (only supplied ones changed).
    ``details`` (if supplied) MUST match the existing ``policy_type`` —
    the COBOL program rejects cross-type updates with return code '98'.
    """
    policy = session.get(Policy, policy_number)
    if policy is None:
        raise NotFoundError(f"Policy {policy_number} not found")

    if issue_date is not None:
        policy.issue_date = issue_date
    if expiry_date is not None:
        policy.expiry_date = expiry_date
    if broker_id is not None:
        policy.broker_id = broker_id
    if brokers_reference is not None:
        policy.brokers_reference = brokers_reference
    if payment is not None:
        policy.payment = payment

    if details is not None:
        if details.policy_type != policy.policy_type:
            raise IntegrityError(
                f"Cannot change policy_type from {policy.policy_type!r} "
                f"to {details.policy_type!r}"
            )
        _update_sub_type(session, policy, details)

    policy.last_changed = _dt.datetime.now()
    session.flush()

    increment_stat(session, "update_policy")
    return policy


def _update_sub_type(
    session: Session,
    policy: Policy,
    details: EndowmentDetails | HouseDetails | MotorDetails | CommercialDetails,
) -> None:
    """In-place field update of the sub-type row matching ``policy``."""
    if details.policy_type == POLICY_TYPE_ENDOWMENT:
        assert isinstance(details, EndowmentDetails) and policy.endowment is not None
        e = policy.endowment
        e.with_profits = details.with_profits
        e.equities = details.equities
        e.managed_fund = details.managed_fund
        e.fund_name = details.fund_name
        e.term = details.term
        e.sum_assured = details.sum_assured
        e.life_assured = details.life_assured
    elif details.policy_type == POLICY_TYPE_HOUSE:
        assert isinstance(details, HouseDetails) and policy.house is not None
        h = policy.house
        h.property_type = details.property_type
        h.bedrooms = details.bedrooms
        h.value = details.value
        h.house_name = details.house_name
        h.house_number = details.house_number
        h.postcode = details.postcode
    elif details.policy_type == POLICY_TYPE_MOTOR:
        assert isinstance(details, MotorDetails) and policy.motor is not None
        m = policy.motor
        m.make = details.make
        m.model = details.model
        m.value = details.value
        m.reg_number = details.reg_number
        m.colour = details.colour
        m.cc = details.cc
        m.manufactured = details.manufactured
        m.premium = details.premium
        m.accidents = details.accidents
    elif details.policy_type == POLICY_TYPE_COMMERCIAL:
        assert isinstance(details, CommercialDetails) and policy.commercial is not None
        c = policy.commercial
        c.address = details.address
        c.postcode = details.postcode
        c.latitude = details.latitude
        c.longitude = details.longitude
        c.customer_text = details.customer_text
        c.prop_type = details.prop_type
        c.fire_peril = details.fire_peril
        c.fire_premium = details.fire_premium
        c.crime_peril = details.crime_peril
        c.crime_premium = details.crime_premium
        c.flood_peril = details.flood_peril
        c.flood_premium = details.flood_premium
        c.weather_peril = details.weather_peril
        c.weather_premium = details.weather_premium
        c.status = details.status
        c.reject_reason = details.reject_reason
    session.flush()


def delete_policy(session: Session, policy_number: int) -> Policy:
    """Port of ``LGDPOL01`` → ``LGDPDB01`` / ``LGDPVS01``.

    Cascade-deletes the sub-type row and any claims (ORM ``cascade="all,
    delete-orphan"`` configured on the relationships).  Returns the loaded
    Policy *before* deletion so callers can snapshot it for the response.
    """
    policy = session.get(Policy, policy_number)
    if policy is None:
        raise NotFoundError(f"Policy {policy_number} not found")
    session.delete(policy)
    session.flush()

    increment_stat(session, "delete_policy")
    return policy


# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------


def add_claim(
    session: Session,
    *,
    policy_number: int,
    claim_date: _dt.date,
    paid: int = 0,
    value: int = 0,
    cause: str = "",
    observations: str = "",
) -> Claim:
    """Insert a CLAIM row against an existing policy."""
    if session.get(Policy, policy_number) is None:
        raise NotFoundError(f"Policy {policy_number} not found")
    claim = Claim(
        policy_number=policy_number,
        claim_date=claim_date,
        paid=paid,
        value=value,
        cause=cause,
        observations=observations,
    )
    session.add(claim)
    session.flush()

    increment_stat(session, "add_claim")
    return claim


def list_claims_for_policy(session: Session, policy_number: int) -> list[Claim]:
    if session.get(Policy, policy_number) is None:
        raise NotFoundError(f"Policy {policy_number} not found")
    stmt = (
        select(Claim)
        .where(Claim.policy_number == policy_number)
        .order_by(Claim.claim_number)
    )
    return list(session.execute(stmt).scalars())


# ---------------------------------------------------------------------------
# Serialisation helpers — used by the router
# ---------------------------------------------------------------------------


def policy_to_dict(policy: Policy) -> dict[str, Any]:
    """Flatten a Policy + its sub-type row into a dict that PolicyOut accepts."""
    return {
        "policy_number": policy.policy_number,
        "customer_number": policy.customer_number,
        "policy_type": policy.policy_type,
        "issue_date": policy.issue_date,
        "expiry_date": policy.expiry_date,
        "last_changed": policy.last_changed,
        "broker_id": policy.broker_id,
        "brokers_reference": policy.brokers_reference,
        "payment": policy.payment,
        "details": _hydrate_details(policy),
    }
