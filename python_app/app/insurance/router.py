"""FastAPI router for the GenApp insurance domain.

Mounted at ``/insurance`` by ``app.main`` — matches the SDD §7.2 mapping
and keeps the existing CBSA banking routers (``/customers`` etc.) untouched.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import cbsa_error_to_http
from app.db.session import get_db
from app.insurance import services
from app.insurance.schemas import (
    ClaimCreate,
    ClaimOut,
    InsuranceCustomerCreate,
    InsuranceCustomerOut,
    InsuranceCustomerUpdate,
    PolicyCreate,
    PolicyOut,
    PolicyUpdate,
    StatsOut,
)
from app.services.errors import CBSAError

router = APIRouter(prefix="/insurance", tags=["insurance"])


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------


@router.post(
    "/customers",
    response_model=InsuranceCustomerOut,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    body: InsuranceCustomerCreate, session: Session = Depends(get_db)
) -> InsuranceCustomerOut:
    try:
        cust = services.add_customer(
            session,
            first_name=body.first_name,
            last_name=body.last_name,
            date_of_birth=body.date_of_birth,
            house_name=body.house_name,
            house_number=body.house_number,
            postcode=body.postcode,
            phone_mobile=body.phone_mobile,
            phone_home=body.phone_home,
            email_address=body.email_address,
        )
        session.commit()
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return InsuranceCustomerOut.model_validate(cust)


@router.get("/customers/{customer_number}", response_model=InsuranceCustomerOut)
def get_customer(
    customer_number: int, session: Session = Depends(get_db)
) -> InsuranceCustomerOut:
    try:
        cust = services.inquire_customer(session, customer_number)
        session.commit()  # commit the stat counter bump
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return InsuranceCustomerOut.model_validate(cust)


@router.put("/customers/{customer_number}", response_model=InsuranceCustomerOut)
def update_customer(
    customer_number: int,
    body: InsuranceCustomerUpdate,
    session: Session = Depends(get_db),
) -> InsuranceCustomerOut:
    try:
        cust = services.update_customer(
            session,
            customer_number,
            first_name=body.first_name,
            last_name=body.last_name,
            date_of_birth=body.date_of_birth,
            house_name=body.house_name,
            house_number=body.house_number,
            postcode=body.postcode,
            phone_mobile=body.phone_mobile,
            phone_home=body.phone_home,
            email_address=body.email_address,
        )
        session.commit()
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return InsuranceCustomerOut.model_validate(cust)


@router.get(
    "/customers/{customer_number}/policies", response_model=list[PolicyOut]
)
def list_policies_for_customer(
    customer_number: int, session: Session = Depends(get_db)
) -> list[PolicyOut]:
    try:
        policies = services.list_policies_for_customer(session, customer_number)
    except CBSAError as exc:
        raise cbsa_error_to_http(exc) from exc
    return [PolicyOut.model_validate(services.policy_to_dict(p)) for p in policies]


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


@router.post(
    "/policies",
    response_model=PolicyOut,
    status_code=status.HTTP_201_CREATED,
)
def create_policy(
    body: PolicyCreate, session: Session = Depends(get_db)
) -> PolicyOut:
    try:
        policy = services.add_policy(
            session,
            customer_number=body.customer_number,
            issue_date=body.issue_date,
            expiry_date=body.expiry_date,
            broker_id=body.broker_id,
            brokers_reference=body.brokers_reference,
            payment=body.payment,
            details=body.details,
        )
        out = PolicyOut.model_validate(services.policy_to_dict(policy))
        session.commit()
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return out


@router.get("/policies/{policy_number}", response_model=PolicyOut)
def get_policy(
    policy_number: int, session: Session = Depends(get_db)
) -> PolicyOut:
    try:
        policy = services.inquire_policy(session, policy_number)
        out = PolicyOut.model_validate(services.policy_to_dict(policy))
        session.commit()
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return out


@router.put("/policies/{policy_number}", response_model=PolicyOut)
def update_policy(
    policy_number: int,
    body: PolicyUpdate,
    session: Session = Depends(get_db),
) -> PolicyOut:
    try:
        policy = services.update_policy(
            session,
            policy_number,
            issue_date=body.issue_date,
            expiry_date=body.expiry_date,
            broker_id=body.broker_id,
            brokers_reference=body.brokers_reference,
            payment=body.payment,
            details=body.details,
        )
        out = PolicyOut.model_validate(services.policy_to_dict(policy))
        session.commit()
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return out


@router.delete("/policies/{policy_number}", response_model=PolicyOut)
def delete_policy(
    policy_number: int, session: Session = Depends(get_db)
) -> PolicyOut:
    try:
        policy = services.delete_policy(session, policy_number)
        out = PolicyOut.model_validate(services.policy_to_dict(policy))
        session.commit()
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return out


# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------


@router.post(
    "/claims",
    response_model=ClaimOut,
    status_code=status.HTTP_201_CREATED,
)
def create_claim(
    body: ClaimCreate, session: Session = Depends(get_db)
) -> ClaimOut:
    try:
        claim = services.add_claim(
            session,
            policy_number=body.policy_number,
            claim_date=body.claim_date,
            paid=body.paid,
            value=body.value,
            cause=body.cause,
            observations=body.observations,
        )
        session.commit()
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return ClaimOut.model_validate(claim)


@router.get(
    "/policies/{policy_number}/claims", response_model=list[ClaimOut]
)
def list_claims_for_policy(
    policy_number: int, session: Session = Depends(get_db)
) -> list[ClaimOut]:
    try:
        claims = services.list_claims_for_policy(session, policy_number)
    except CBSAError as exc:
        raise cbsa_error_to_http(exc) from exc
    return [ClaimOut.model_validate(c) for c in claims]


# ---------------------------------------------------------------------------
# Stats — LGASTAT1
# ---------------------------------------------------------------------------


@router.get("/stats", response_model=StatsOut)
def get_stats(session: Session = Depends(get_db)) -> StatsOut:
    return services.get_stats(session)
