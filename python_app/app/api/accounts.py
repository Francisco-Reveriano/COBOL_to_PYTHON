"""Account and transaction REST endpoints (was OCAC / ODAC / OUAC / OCRA)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import cbsa_error_to_http
from app.api.schemas import (
    AccountCreate,
    AccountOut,
    AccountUpdate,
    TransactionRequest,
    TransactionResult,
)
from app.db.session import get_db
from app.services import account_service, transaction_service
from app.services.errors import CBSAError

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account_endpoint(
    body: AccountCreate, session: Session = Depends(get_db)
) -> AccountOut:
    try:
        acc = account_service.create_account(
            session,
            customer_number=body.customer_number,
            account_type=body.type,
            interest_rate=body.interest_rate,
            overdraft_limit=body.overdraft_limit,
            opened=body.opened,
        )
        session.commit()
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return AccountOut.model_validate(acc)


@router.get("/{number}", response_model=AccountOut)
def get_account_endpoint(
    number: str, session: Session = Depends(get_db)
) -> AccountOut:
    try:
        acc = account_service.get_account(session, number)
    except CBSAError as exc:
        raise cbsa_error_to_http(exc) from exc
    return AccountOut.model_validate(acc)


@router.put("/{number}", response_model=AccountOut)
def update_account_endpoint(
    number: str, body: AccountUpdate, session: Session = Depends(get_db)
) -> AccountOut:
    try:
        acc = account_service.update_account(
            session,
            number,
            account_type=body.type,
            interest_rate=body.interest_rate,
            overdraft_limit=body.overdraft_limit,
            last_statement=body.last_statement,
            next_statement=body.next_statement,
        )
        session.commit()
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return AccountOut.model_validate(acc)


@router.delete("/{number}", response_model=AccountOut)
def delete_account_endpoint(
    number: str, session: Session = Depends(get_db)
) -> AccountOut:
    try:
        acc = account_service.delete_account(session, number)
        out = AccountOut.model_validate(acc)
        session.commit()
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return out


@router.post(
    "/{number}/transactions",
    response_model=TransactionResult,
    status_code=status.HTTP_201_CREATED,
)
def debit_credit_endpoint(
    number: str,
    body: TransactionRequest,
    session: Session = Depends(get_db),
) -> TransactionResult:
    try:
        result = transaction_service.debit_credit(
            session,
            account_number=number,
            amount=body.amount,
            facility_type=body.facility_type,
            origin=body.origin,
        )
        session.commit()
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return TransactionResult(
        account=AccountOut.model_validate(result.account),
        proctran_id=result.proctran.id,
        proctran_type=result.proctran.type,
        new_available_balance=result.account.available_balance,
        new_actual_balance=result.account.actual_balance,
    )
