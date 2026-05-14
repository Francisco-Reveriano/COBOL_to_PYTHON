"""Transaction service — ports the COBOL transaction programs.

* ``DBCRFUN.cbl`` → :func:`debit_credit`
* ``XFRFUN.cbl``  → :func:`transfer_funds`

Both functions perform their work inside the caller-supplied SQLAlchemy
``Session``; FastAPI commits the transaction at the end of the request.
SQLAlchemy will roll back automatically on any raised exception, so the
COBOL ``EXEC CICS SYNCPOINT ROLLBACK`` is reproduced for free.
"""

from __future__ import annotations

import decimal as _d
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, ProcTran
from app.models.proctran import (
    PROC_TYPE_CREDIT,
    PROC_TYPE_DEBIT,
    PROC_TYPE_PAYMENT_CREDIT,
    PROC_TYPE_PAYMENT_DEBIT,
    PROC_TYPE_TRANSFER,
)
from app.services.common import fmt_account_number, now, sort_code
from app.services.errors import (
    AccountTypeRestrictionError,
    InsufficientFundsError,
    InvalidAmountError,
    NotFoundError,
    SameAccountTransferError,
)

# COBOL ``COMM-FACILTYPE`` value indicating the request came in via the
# Payment interface (vs. the BMS Teller).  Both MORTGAGE/LOAN restrictions
# and the insufficient-funds check are only applied when this value is set
# (see ``DBCRFUN.cbl`` lines 329 and 344).
FACILTYPE_PAYMENT = 496

RESTRICTED_PAYMENT_TYPES = frozenset({"MORTGAGE", "LOAN"})


@dataclass(frozen=True)
class DebitCreditResult:
    account: Account
    proctran: ProcTran


@dataclass(frozen=True)
class TransferResult:
    from_account: Account
    to_account: Account
    from_proctran: ProcTran
    to_proctran: ProcTran


def _lock_account(session: Session, sortcode: str, number: str) -> Account:
    """``SELECT ACCOUNT … FOR UPDATE`` (matches ``DBCRFUN.cbl`` UPDATE flow)."""
    stmt = (
        select(Account)
        .where(Account.sortcode == sortcode, Account.number == number)
        .with_for_update()
    )
    account = session.execute(stmt).scalar_one_or_none()
    if account is None:
        raise NotFoundError(f"Account {number} not found")
    return account


def debit_credit(
    session: Session,
    *,
    account_number: int | str,
    amount: _d.Decimal,
    facility_type: int = FACILTYPE_PAYMENT,
    origin: str = "",
) -> DebitCreditResult:
    """Apply a debit (negative ``amount``) or credit (positive ``amount``).

    Port of ``DBCRFUN.cbl``.

    * Selects the account ``FOR UPDATE`` (locks the row).
    * If ``amount < 0`` (a debit) and ``facility_type == FACILTYPE_PAYMENT``:
        * rejects on MORTGAGE / LOAN accounts (``DBCRFUN.cbl:330``);
        * rejects with :class:`InsufficientFundsError` when ``avail + amount < 0``
          (``DBCRFUN.cbl:344``).
    * For credits with ``facility_type == FACILTYPE_PAYMENT``: also rejects on
      MORTGAGE / LOAN accounts (``DBCRFUN.cbl:367``).
    * Updates both the available and actual balances and writes a single
      ``PROCTRAN`` row whose ``type`` reflects the operation
      (``DEB``/``CRE`` for Teller, ``PDR``/``PCR`` for Payment).
    """
    if amount == 0:
        raise InvalidAmountError("Transaction amount must be non-zero", fail_code="4")

    amount = _d.Decimal(amount)
    sc = sort_code()
    account = _lock_account(session, sc, fmt_account_number(account_number))
    acc_type = account.type.strip().upper()

    if amount < 0:
        if (
            facility_type == FACILTYPE_PAYMENT
            and acc_type in RESTRICTED_PAYMENT_TYPES
        ):
            raise AccountTypeRestrictionError(
                f"Cannot debit a {acc_type} account via the Payment interface"
            )
        if (
            facility_type == FACILTYPE_PAYMENT
            and account.available_balance + amount < 0
        ):
            raise InsufficientFundsError(
                f"Insufficient funds: available={account.available_balance}, "
                f"requested={-amount}"
            )
    else:  # credit
        if (
            facility_type == FACILTYPE_PAYMENT
            and acc_type in RESTRICTED_PAYMENT_TYPES
        ):
            raise AccountTypeRestrictionError(
                f"Cannot credit a {acc_type} account via the Payment interface"
            )

    account.available_balance = account.available_balance + amount
    account.actual_balance = account.actual_balance + amount

    if amount < 0:
        if facility_type == FACILTYPE_PAYMENT:
            type_code = PROC_TYPE_PAYMENT_DEBIT
            desc = (origin or "PAYMENT DEBIT")[:14].ljust(14)
        else:
            type_code = PROC_TYPE_DEBIT
            desc = "COUNTER WTHDRW"
    else:
        if facility_type == FACILTYPE_PAYMENT:
            type_code = PROC_TYPE_PAYMENT_CREDIT
            desc = (origin or "PAYMENT CREDIT")[:14].ljust(14)
        else:
            type_code = PROC_TYPE_CREDIT
            desc = "COUNTER RECVED"

    n = now()
    pt = ProcTran(
        eyecatcher="PRTR",
        sortcode=account.sortcode,
        number=account.number,
        date=n.date(),
        time=n.time().replace(microsecond=0),
        ref="",
        type=type_code,
        description=desc,
        amount=amount,
    )
    session.add(pt)
    session.flush()
    return DebitCreditResult(account=account, proctran=pt)


def transfer_funds(
    session: Session,
    *,
    from_account_number: int | str,
    to_account_number: int | str,
    amount: _d.Decimal,
    facility_type: int = FACILTYPE_PAYMENT,
) -> TransferResult:
    """Transfer ``amount`` from one account to another (port of ``XFRFUN.cbl``).

    Business rules from the COBOL source:

    * Reject if ``amount <= 0`` (``XFRFUN.cbl:289``, fail code ``4``).
    * Reject if the two accounts are identical (``XFRFUN.cbl:316``).
    * Always lock the account with the **lower** numeric key first to
      avoid deadlocks under concurrent transfers (``XFRFUN.cbl:380``).
    * Write **two** ``PROCTRAN`` records (one debit, one credit), each of
      type ``TFR`` with a description identifying the counter-party.
    """
    if amount is None:
        raise InvalidAmountError("Transfer amount is required", fail_code="4")
    amount = _d.Decimal(amount)
    if amount <= 0:
        raise InvalidAmountError(
            "Transfer amount must be greater than zero", fail_code="4"
        )

    sc = sort_code()
    from_num = fmt_account_number(from_account_number)
    to_num = fmt_account_number(to_account_number)
    if from_num == to_num:
        raise SameAccountTransferError(
            "Cannot transfer to the same account"
        )

    if from_num < to_num:
        first_account = _lock_account(session, sc, from_num)
        second_account = _lock_account(session, sc, to_num)
        from_acc, to_acc = first_account, second_account
    else:
        first_account = _lock_account(session, sc, to_num)
        second_account = _lock_account(session, sc, from_num)
        from_acc, to_acc = second_account, first_account

    from_acc.available_balance = from_acc.available_balance - amount
    from_acc.actual_balance = from_acc.actual_balance - amount
    to_acc.available_balance = to_acc.available_balance + amount
    to_acc.actual_balance = to_acc.actual_balance + amount

    n = now()
    today_d = n.date()
    time_d = n.time().replace(microsecond=0)

    from_pt = ProcTran(
        eyecatcher="PRTR",
        sortcode=from_acc.sortcode,
        number=from_acc.number,
        date=today_d,
        time=time_d,
        ref="",
        type=PROC_TYPE_TRANSFER,
        description=(f"TRANSFER TO {to_acc.sortcode}{to_acc.number}")[:40],
        amount=-amount,
    )
    to_pt = ProcTran(
        eyecatcher="PRTR",
        sortcode=to_acc.sortcode,
        number=to_acc.number,
        date=today_d,
        time=time_d,
        ref="",
        type=PROC_TYPE_TRANSFER,
        description=(f"TRANSFER FR {from_acc.sortcode}{from_acc.number}")[:40],
        amount=amount,
    )
    session.add_all([from_pt, to_pt])
    session.flush()

    # Quiet unused-variable lint (facility_type currently doesn't affect transfers).
    _ = facility_type
    return TransferResult(
        from_account=from_acc,
        to_account=to_acc,
        from_proctran=from_pt,
        to_proctran=to_pt,
    )
