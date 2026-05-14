"""Pydantic schemas for the GenApp insurance REST contract.

Replaces the COBOL COMMAREA layouts in ``cics-genapp/base/src/lgcmarea.cpy``
and the per-sub-type structures in ``cics-genapp/base/src/lgpolicy.cpy``.

The four policy sub-types are modelled as a Pydantic discriminated union on
``policy_type`` — callers send one ``details`` object whose shape is fixed by
the discriminator value, rather than 4-way conditional branches.
"""

from __future__ import annotations

import datetime as _dt
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from app.insurance.models import (
    POLICY_TYPE_COMMERCIAL,
    POLICY_TYPE_ENDOWMENT,
    POLICY_TYPE_HOUSE,
    POLICY_TYPE_MOTOR,
)

# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------


class InsuranceCustomerBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    first_name: str = Field(..., max_length=10)
    last_name: str = Field(..., max_length=20)
    date_of_birth: _dt.date
    house_name: str = Field("", max_length=20)
    house_number: str = Field("", max_length=4)
    postcode: str = Field("", max_length=8)
    phone_mobile: str = Field("", max_length=20)
    phone_home: str = Field("", max_length=20)
    email_address: str = Field("", max_length=100)


class InsuranceCustomerCreate(InsuranceCustomerBase):
    pass


class InsuranceCustomerUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    first_name: str | None = Field(None, max_length=10)
    last_name: str | None = Field(None, max_length=20)
    date_of_birth: _dt.date | None = None
    house_name: str | None = Field(None, max_length=20)
    house_number: str | None = Field(None, max_length=4)
    postcode: str | None = Field(None, max_length=8)
    phone_mobile: str | None = Field(None, max_length=20)
    phone_home: str | None = Field(None, max_length=20)
    email_address: str | None = Field(None, max_length=100)


class InsuranceCustomerOut(InsuranceCustomerBase):
    customer_number: int


# ---------------------------------------------------------------------------
# Policy details — discriminated union per ``policy_type``
# ---------------------------------------------------------------------------


class EndowmentDetails(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    policy_type: Literal["E"] = POLICY_TYPE_ENDOWMENT
    with_profits: bool = False
    equities: bool = False
    managed_fund: bool = False
    fund_name: str = Field("", max_length=10)
    term: int = Field(0, ge=0)
    sum_assured: int = Field(0, ge=0)
    life_assured: str = Field("", max_length=31)


class HouseDetails(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    policy_type: Literal["H"] = POLICY_TYPE_HOUSE
    property_type: str = Field("", max_length=15)
    bedrooms: int = Field(0, ge=0)
    value: int = Field(0, ge=0)
    house_name: str = Field("", max_length=20)
    house_number: str = Field("", max_length=4)
    postcode: str = Field("", max_length=8)


class MotorDetails(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    policy_type: Literal["M"] = POLICY_TYPE_MOTOR
    make: str = Field("", max_length=15)
    model: str = Field("", max_length=15)
    value: int = Field(0, ge=0)
    reg_number: str = Field("", max_length=7)
    colour: str = Field("", max_length=8)
    cc: int = Field(0, ge=0)
    manufactured: str = Field("", max_length=10)
    premium: int = Field(0, ge=0)
    accidents: int = Field(0, ge=0)


class CommercialDetails(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    policy_type: Literal["C"] = POLICY_TYPE_COMMERCIAL
    address: str = Field("", max_length=255)
    postcode: str = Field("", max_length=8)
    latitude: str = Field("", max_length=11)
    longitude: str = Field("", max_length=11)
    customer_text: str = Field("", max_length=255)
    prop_type: str = Field("", max_length=255)
    fire_peril: int = 0
    fire_premium: int = 0
    crime_peril: int = 0
    crime_premium: int = 0
    flood_peril: int = 0
    flood_premium: int = 0
    weather_peril: int = 0
    weather_premium: int = 0
    status: int = 0
    reject_reason: str = Field("", max_length=255)


PolicyDetails = Annotated[
    Union[EndowmentDetails, HouseDetails, MotorDetails, CommercialDetails],
    Field(discriminator="policy_type"),
]


# ---------------------------------------------------------------------------
# Policy header / aggregate
# ---------------------------------------------------------------------------


class PolicyBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    customer_number: int = Field(..., ge=1)
    issue_date: _dt.date
    expiry_date: _dt.date
    broker_id: int = Field(0, ge=0)
    brokers_reference: str = Field("", max_length=10)
    payment: int = Field(0, ge=0)


class PolicyCreate(PolicyBase):
    details: PolicyDetails


class PolicyUpdate(BaseModel):
    """Partial update of the POLICY header.  Sub-type details are updated
    via :class:`PolicyDetailsUpdate` against the matching nested endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True)

    issue_date: _dt.date | None = None
    expiry_date: _dt.date | None = None
    broker_id: int | None = Field(None, ge=0)
    brokers_reference: str | None = Field(None, max_length=10)
    payment: int | None = Field(None, ge=0)
    details: PolicyDetails | None = None


class PolicyOut(PolicyBase):
    policy_number: int
    policy_type: str
    last_changed: _dt.datetime
    details: PolicyDetails


# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------


class ClaimBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    claim_date: _dt.date
    paid: int = Field(0, ge=0)
    value: int = Field(0, ge=0)
    cause: str = Field("", max_length=255)
    observations: str = Field("", max_length=255)


class ClaimCreate(ClaimBase):
    policy_number: int = Field(..., ge=1)


class ClaimOut(ClaimBase):
    claim_number: int
    policy_number: int


# ---------------------------------------------------------------------------
# Stats — ``LGASTAT1`` port
# ---------------------------------------------------------------------------


class StatsOut(BaseModel):
    add_customer: int = 0
    inquire_customer: int = 0
    update_customer: int = 0
    add_policy: int = 0
    inquire_policy: int = 0
    update_policy: int = 0
    delete_policy: int = 0
    add_claim: int = 0
