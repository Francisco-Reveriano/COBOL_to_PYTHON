"""Pydantic schemas — the REST contract.

These replace the COBOL COMMAREA layouts from the ``.cpy`` files (e.g.
``CRECUST.cpy``, ``CREACC.cpy``, ``PAYDBCR.cpy``, ``XFRFUN.cpy``).
"""

from __future__ import annotations

import datetime as _dt
import decimal as _d

from pydantic import BaseModel, ConfigDict, Field


class CustomerBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    name: str = Field(..., max_length=60)
    address: str = Field(..., max_length=160)
    date_of_birth: _dt.date


class CustomerCreate(CustomerBase):
    credit_score: int | None = Field(None, ge=0, le=999)
    cs_review_date: _dt.date | None = None


class CustomerUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(None, max_length=60)
    address: str | None = Field(None, max_length=160)
    date_of_birth: _dt.date | None = None
    credit_score: int | None = Field(None, ge=0, le=999)
    cs_review_date: _dt.date | None = None


class CustomerOut(CustomerBase):
    eyecatcher: str
    sortcode: str
    number: str
    credit_score: int
    cs_review_date: _dt.date


class AccountBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    type: str = Field(..., max_length=8)
    interest_rate: _d.Decimal = Field(_d.Decimal("0.00"), max_digits=4, decimal_places=2)
    overdraft_limit: int = 0


class AccountCreate(AccountBase):
    customer_number: str = Field(..., min_length=1, max_length=10)
    opened: _dt.date | None = None


class AccountUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    type: str | None = Field(None, max_length=8)
    interest_rate: _d.Decimal | None = Field(
        None, max_digits=4, decimal_places=2
    )
    overdraft_limit: int | None = None
    last_statement: _dt.date | None = None
    next_statement: _dt.date | None = None


class AccountOut(AccountBase):
    eyecatcher: str
    customer_number: str
    sortcode: str
    number: str
    opened: _dt.date
    last_statement: _dt.date
    next_statement: _dt.date
    available_balance: _d.Decimal
    actual_balance: _d.Decimal


class TransactionRequest(BaseModel):
    """Request body for ``POST /accounts/{number}/transactions`` (was OCRA)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    amount: _d.Decimal = Field(
        ..., description="Positive for credit, negative for debit."
    )
    facility_type: int = Field(
        496,
        description=(
            "COBOL COMM-FACILTYPE.  Use 496 for a PAYMENT (the default — "
            "MORTGAGE/LOAN block and insufficient-funds check apply); use "
            "any other value to model a BMS Teller transaction."
        ),
    )
    origin: str = Field("", max_length=40)


class TransferRequest(BaseModel):
    """Request body for ``POST /transfers`` (was OTFN)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    from_account: str = Field(..., max_length=8)
    to_account: str = Field(..., max_length=8)
    amount: _d.Decimal = Field(..., gt=0)


class TransactionResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account: AccountOut
    proctran_id: int
    proctran_type: str
    new_available_balance: _d.Decimal
    new_actual_balance: _d.Decimal


class TransferResult(BaseModel):
    from_account: AccountOut
    to_account: AccountOut
    from_proctran_id: int
    to_proctran_id: int


class ProcTranOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    eyecatcher: str
    sortcode: str
    number: str
    date: _dt.date
    time: _dt.time
    ref: str
    type: str
    description: str
    amount: _d.Decimal


class SortCodeOut(BaseModel):
    sort_code: str


class CompanyOut(BaseModel):
    company_name: str
