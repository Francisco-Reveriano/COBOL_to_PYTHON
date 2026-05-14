"""Transfer REST endpoint (was OTFN / ``XFRFUN.cbl``)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import cbsa_error_to_http
from app.api.schemas import AccountOut, TransferRequest, TransferResult
from app.db.session import get_db
from app.services import transaction_service
from app.services.errors import CBSAError

router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.post("", response_model=TransferResult, status_code=status.HTTP_201_CREATED)
def transfer_endpoint(
    body: TransferRequest, session: Session = Depends(get_db)
) -> TransferResult:
    try:
        result = transaction_service.transfer_funds(
            session,
            from_account_number=body.from_account,
            to_account_number=body.to_account,
            amount=body.amount,
        )
        session.commit()
    except CBSAError as exc:
        session.rollback()
        raise cbsa_error_to_http(exc) from exc
    return TransferResult(
        from_account=AccountOut.model_validate(result.from_account),
        to_account=AccountOut.model_validate(result.to_account),
        from_proctran_id=result.from_proctran.id,
        to_proctran_id=result.to_proctran.id,
    )
