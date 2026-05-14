"""Domain exceptions raised by the service layer.

Each exception carries a short ``fail_code`` that mirrors the
``COMM-FAIL-CODE`` returned by the original COBOL programs, so callers
(and tests) can assert on the exact reason for a failure.
"""

from __future__ import annotations


class CBSAError(Exception):
    """Base class for all CBSA service-layer errors."""

    fail_code: str = "?"

    def __init__(self, message: str, fail_code: str | None = None) -> None:
        super().__init__(message)
        if fail_code is not None:
            self.fail_code = fail_code


class NotFoundError(CBSAError):
    """Record was not found (COBOL ``SQLCODE = +100`` / fail code ``1``)."""

    fail_code = "1"


class IntegrityError(CBSAError):
    """A unique / referential integrity rule was violated."""

    fail_code = "2"


class InsufficientFundsError(CBSAError):
    """Debit would take available balance negative (``DBCRFUN.cbl`` fail ``3``)."""

    fail_code = "3"


class AccountTypeRestrictionError(CBSAError):
    """Operation not allowed for MORTGAGE/LOAN payment (fail code ``4``)."""

    fail_code = "4"


class InvalidAmountError(CBSAError):
    """Transfer amount must be > 0 (``XFRFUN.cbl`` fail code ``4``)."""

    fail_code = "4"


class SameAccountTransferError(CBSAError):
    """Cannot transfer to the same account (``XFRFUN.cbl`` ABCODE 'SAME')."""

    fail_code = "5"


class TooManyAccountsError(CBSAError):
    """Customer already has the maximum of 10 accounts (CREACC fail ``8``)."""

    fail_code = "8"


class InvalidAccountTypeError(CBSAError):
    """Account type is not one of ISA/MORTGAGE/SAVING/CURRENT/LOAN (fail ``A``)."""

    fail_code = "A"


class CreditAgencyTimeoutError(CBSAError):
    """All credit agencies failed to respond within the 3-second window.

    Mirrors ``CRECUST.cbl``'s ``COMM-FAIL-CODE = 'C'`` branch, which is
    taken when the parent's ``EXEC CICS FETCH ANY`` returns NOTFINISHED
    *and* no replies have been retrieved yet.
    """

    fail_code = "T"
