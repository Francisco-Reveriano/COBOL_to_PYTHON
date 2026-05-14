"""Customer REST endpoints (was OCCS / ODCS / UPDCUST / DELCUS)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import cbsa_error_to_http
from app.api.schemas import (
    AccountOut,
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
)
from app.db.session import get_db
from app.services import account_service, customer_service
from app.services.errors import CBSAError

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer_endpoint(
    body: CustomerCreate, session: Session = Depends(get_db)
) -> CustomerOut:
    try:
        cust = customer_service.create_customer(
            session,
            name=body.name,
            address=body.address,
            date_of_birth=body.date_of_birth,
            credit_score=body.credit_score,
            cs_review_date=body.cs_review_date,
        )
        session.commit()
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return CustomerOut.model_validate(cust)


@router.get("/{number}", response_model=CustomerOut)
def get_customer_endpoint(
    number: str, session: Session = Depends(get_db)
) -> CustomerOut:
    try:
        cust = customer_service.get_customer(session, number)
    except CBSAError as exc:
        raise cbsa_error_to_http(exc) from exc
    return CustomerOut.model_validate(cust)


@router.put("/{number}", response_model=CustomerOut)
def update_customer_endpoint(
    number: str, body: CustomerUpdate, session: Session = Depends(get_db)
) -> CustomerOut:
    try:
        cust = customer_service.update_customer(
            session,
            number,
            name=body.name,
            address=body.address,
            date_of_birth=body.date_of_birth,
            credit_score=body.credit_score,
            cs_review_date=body.cs_review_date,
        )
        session.commit()
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return CustomerOut.model_validate(cust)


@router.delete("/{number}", response_model=CustomerOut)
def delete_customer_endpoint(
    number: str, session: Session = Depends(get_db)
) -> CustomerOut:
    try:
        cust = customer_service.delete_customer(session, number)
        # Snapshot fields before commit since the row will be expired afterwards.
        out = CustomerOut.model_validate(cust)
        session.commit()
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return out


@router.get("/{number}/accounts", response_model=list[AccountOut])
def list_accounts_for_customer(
    number: str, session: Session = Depends(get_db)
) -> list[AccountOut]:
    try:
        accounts = account_service.get_accounts_for_customer(session, number)
    except CBSAError as exc:
        raise cbsa_error_to_http(exc) from exc
    return [AccountOut.model_validate(a) for a in accounts]
