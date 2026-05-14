"""Unit tests for debit/credit and transfer (ports of DBCRFUN.cbl / XFRFUN.cbl)."""

from __future__ import annotations

import datetime as _dt
import decimal as _d

import pytest

from app.models import ProcTran
from app.models.proctran import (
    PROC_TYPE_CREDIT,
    PROC_TYPE_DEBIT,
    PROC_TYPE_PAYMENT_CREDIT,
    PROC_TYPE_PAYMENT_DEBIT,
    PROC_TYPE_TRANSFER,
)
from app.services import account_service, customer_service, transaction_service
from app.services.errors import (
    AccountTypeRestrictionError,
    InsufficientFundsError,
    InvalidAmountError,
    NotFoundError,
    SameAccountTransferError,
)
from app.services.transaction_service import FACILTYPE_PAYMENT


def _funded_account(session, account_type="CURRENT", initial=_d.Decimal("1000")):
    c = customer_service.create_customer(
        session,
        name="Test",
        address="1 Test St",
        date_of_birth=_dt.date(1990, 1, 1),
        credit_score=700,
    )
    a = account_service.create_account(
        session, customer_number=c.number, account_type=account_type
    )
    # Seed with a teller credit so we don't trip the MORTGAGE/LOAN block.
    if initial != _d.Decimal("0"):
        transaction_service.debit_credit(
            session,
            account_number=a.number,
            amount=initial,
            facility_type=0,  # Teller
        )
    return a


def test_credit_increases_balance(session):
    a = _funded_account(session, initial=_d.Decimal("0"))
    transaction_service.debit_credit(
        session, account_number=a.number, amount=_d.Decimal("250.50")
    )
    refreshed = account_service.get_account(session, a.number)
    assert refreshed.available_balance == _d.Decimal("250.50")
    assert refreshed.actual_balance == _d.Decimal("250.50")


def test_debit_decreases_balance_and_writes_pdr(session):
    a = _funded_account(session)
    result = transaction_service.debit_credit(
        session, account_number=a.number, amount=_d.Decimal("-100")
    )
    refreshed = account_service.get_account(session, a.number)
    assert refreshed.available_balance == _d.Decimal("900")
    assert refreshed.actual_balance == _d.Decimal("900")
    assert result.proctran.type == PROC_TYPE_PAYMENT_DEBIT
    assert result.proctran.amount == _d.Decimal("-100")


def test_teller_debit_writes_deb_proctran(session):
    a = _funded_account(session)
    result = transaction_service.debit_credit(
        session, account_number=a.number, amount=_d.Decimal("-50"), facility_type=0
    )
    assert result.proctran.type == PROC_TYPE_DEBIT


def test_teller_credit_writes_cre_proctran(session):
    a = _funded_account(session, initial=_d.Decimal("0"))
    result = transaction_service.debit_credit(
        session,
        account_number=a.number,
        amount=_d.Decimal("75"),
        facility_type=0,
    )
    assert result.proctran.type == PROC_TYPE_CREDIT


def test_payment_credit_writes_pcr_proctran(session):
    a = _funded_account(session, initial=_d.Decimal("0"))
    result = transaction_service.debit_credit(
        session, account_number=a.number, amount=_d.Decimal("75")
    )
    assert result.proctran.type == PROC_TYPE_PAYMENT_CREDIT


def test_insufficient_funds_rejected(session):
    """DBCRFUN.cbl ~line 344: payment debit below available balance fails."""
    a = _funded_account(session)
    with pytest.raises(InsufficientFundsError) as exc_info:
        transaction_service.debit_credit(
            session,
            account_number=a.number,
            amount=_d.Decimal("-2000"),
            facility_type=FACILTYPE_PAYMENT,
        )
    assert exc_info.value.fail_code == "3"
    # The account balance is unchanged.
    assert account_service.get_account(session, a.number).available_balance == _d.Decimal("1000")


def test_teller_debit_can_overdraft(session):
    """DBCRFUN.cbl restricts the insufficient-funds check to PAYMENT requests."""
    a = _funded_account(session)
    transaction_service.debit_credit(
        session,
        account_number=a.number,
        amount=_d.Decimal("-5000"),
        facility_type=0,  # Teller
    )
    refreshed = account_service.get_account(session, a.number)
    assert refreshed.available_balance == _d.Decimal("-4000")


@pytest.mark.parametrize("acc_type", ["MORTGAGE", "LOAN"])
def test_payment_against_mortgage_or_loan_rejected(session, acc_type):
    """DBCRFUN.cbl ~line 330 and ~line 367: PAYMENT MORTGAGE/LOAN blocked."""
    a = _funded_account(session, account_type=acc_type, initial=_d.Decimal("0"))
    with pytest.raises(AccountTypeRestrictionError):
        transaction_service.debit_credit(
            session,
            account_number=a.number,
            amount=_d.Decimal("-50"),
            facility_type=FACILTYPE_PAYMENT,
        )
    with pytest.raises(AccountTypeRestrictionError):
        transaction_service.debit_credit(
            session,
            account_number=a.number,
            amount=_d.Decimal("50"),
            facility_type=FACILTYPE_PAYMENT,
        )


def test_zero_amount_rejected(session):
    a = _funded_account(session)
    with pytest.raises(InvalidAmountError):
        transaction_service.debit_credit(
            session, account_number=a.number, amount=_d.Decimal("0")
        )


def test_debit_on_missing_account_raises(session):
    with pytest.raises(NotFoundError):
        transaction_service.debit_credit(
            session, account_number="99999999", amount=_d.Decimal("-10")
        )


# ---- transfer_funds ----------------------------------------------------------


def _two_accounts(session):
    c = customer_service.create_customer(
        session,
        name="Owner",
        address="1 Test St",
        date_of_birth=_dt.date(1990, 1, 1),
        credit_score=700,
    )
    a = account_service.create_account(
        session, customer_number=c.number, account_type="CURRENT"
    )
    b = account_service.create_account(
        session, customer_number=c.number, account_type="SAVING"
    )
    transaction_service.debit_credit(
        session,
        account_number=a.number,
        amount=_d.Decimal("500"),
        facility_type=0,
    )
    return a, b


def test_transfer_moves_funds_and_writes_two_proctrans(session):
    a, b = _two_accounts(session)
    result = transaction_service.transfer_funds(
        session,
        from_account_number=a.number,
        to_account_number=b.number,
        amount=_d.Decimal("200"),
    )
    assert result.from_account.available_balance == _d.Decimal("300")
    assert result.to_account.available_balance == _d.Decimal("200")
    assert result.from_proctran.type == PROC_TYPE_TRANSFER
    assert result.to_proctran.type == PROC_TYPE_TRANSFER
    rows = session.query(ProcTran).filter(ProcTran.type == PROC_TYPE_TRANSFER).all()
    assert len(rows) == 2


def test_transfer_amount_must_be_positive(session):
    """XFRFUN.cbl line ~289: COMM-AMT <= ZERO -> fail code '4'."""
    a, b = _two_accounts(session)
    for bad in (_d.Decimal("0"), _d.Decimal("-1")):
        with pytest.raises(InvalidAmountError) as exc_info:
            transaction_service.transfer_funds(
                session,
                from_account_number=a.number,
                to_account_number=b.number,
                amount=bad,
            )
        assert exc_info.value.fail_code == "4"


def test_transfer_to_same_account_rejected(session):
    """XFRFUN.cbl line ~316: COMM-FACCNO = COMM-TACCNO."""
    a, _b = _two_accounts(session)
    with pytest.raises(SameAccountTransferError):
        transaction_service.transfer_funds(
            session,
            from_account_number=a.number,
            to_account_number=a.number,
            amount=_d.Decimal("10"),
        )


def test_transfer_into_missing_account_raises(session):
    a, _b = _two_accounts(session)
    with pytest.raises(NotFoundError):
        transaction_service.transfer_funds(
            session,
            from_account_number=a.number,
            to_account_number="99999999",
            amount=_d.Decimal("10"),
        )
