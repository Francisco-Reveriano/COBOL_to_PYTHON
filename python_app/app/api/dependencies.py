"""FastAPI dependencies and exception translation.

Service-layer errors raise :class:`app.services.errors.CBSAError`; here we
turn those into the HTTP responses described in the README.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from app.services.errors import (
    AccountTypeRestrictionError,
    CBSAError,
    InsufficientFundsError,
    IntegrityError,
    InvalidAccountTypeError,
    InvalidAmountError,
    NotFoundError,
    SameAccountTransferError,
    TooManyAccountsError,
)

_STATUS_BY_ERROR: dict[type[CBSAError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    IntegrityError: status.HTTP_409_CONFLICT,
    InsufficientFundsError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    AccountTypeRestrictionError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    InvalidAmountError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    SameAccountTransferError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    TooManyAccountsError: status.HTTP_409_CONFLICT,
    InvalidAccountTypeError: status.HTTP_422_UNPROCESSABLE_ENTITY,
}


def cbsa_error_to_http(exc: CBSAError) -> HTTPException:
    """Translate a CBSA service error into a FastAPI ``HTTPException``."""
    http_status = _STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return HTTPException(
        status_code=http_status,
        detail={"message": str(exc), "fail_code": exc.fail_code},
    )
