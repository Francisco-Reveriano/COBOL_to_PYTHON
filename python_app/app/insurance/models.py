"""SQLAlchemy models for the GenApp insurance domain.

Field shapes are taken from the COBOL copybook ``cics-genapp/base/src/lgpolicy.cpy``
and the DB2 DDL in ``etc/install/base/db2jcl/``.  All four policy sub-types
(Endowment, House, Motor, Commercial) live in separate tables linked to a
common :class:`Policy` header, mirroring the COBOL/DB2 schema 1:1.
"""

from __future__ import annotations

import datetime as _dt

from sqlalchemy import (
    CHAR,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Policy type discriminator codes (CHAR(1) in the COBOL DB2 schema)
POLICY_TYPE_ENDOWMENT = "E"
POLICY_TYPE_HOUSE = "H"
POLICY_TYPE_MOTOR = "M"
POLICY_TYPE_COMMERCIAL = "C"

VALID_POLICY_TYPES: frozenset[str] = frozenset(
    {
        POLICY_TYPE_ENDOWMENT,
        POLICY_TYPE_HOUSE,
        POLICY_TYPE_MOTOR,
        POLICY_TYPE_COMMERCIAL,
    }
)


class InsuranceCustomer(Base):
    """GenApp ``CUSTOMER`` table — ported from ``LGACDB01`` / ``lgpolicy.cpy``.

    Kept entirely separate from CBSA's ``customer`` table (which has different
    fields and a different lifecycle) per SDD §7.2.
    """

    __tablename__ = "insurance_customer"

    customer_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(10), nullable=False)
    last_name: Mapped[str] = mapped_column(String(20), nullable=False)
    date_of_birth: Mapped[_dt.date] = mapped_column(Date, nullable=False)
    house_name: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    house_number: Mapped[str] = mapped_column(String(4), nullable=False, default="")
    postcode: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    phone_mobile: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    phone_home: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    email_address: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    created_at: Mapped[_dt.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    policies: Mapped[list["Policy"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )


class Policy(Base):
    """``POLICY`` header table — common columns across all sub-types.

    The sub-type-specific columns live in :class:`PolicyEndowment`,
    :class:`PolicyHouse`, :class:`PolicyMotor`, :class:`PolicyCommercial`.
    """

    __tablename__ = "insurance_policy"

    policy_number: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    customer_number: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("insurance_customer.customer_number", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_type: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    issue_date: Mapped[_dt.date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[_dt.date] = mapped_column(Date, nullable=False)
    last_changed: Mapped[_dt.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    broker_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    brokers_reference: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    payment: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    customer: Mapped[InsuranceCustomer] = relationship(back_populates="policies")

    endowment: Mapped["PolicyEndowment | None"] = relationship(
        back_populates="policy",
        uselist=False,
        cascade="all, delete-orphan",
    )
    house: Mapped["PolicyHouse | None"] = relationship(
        back_populates="policy",
        uselist=False,
        cascade="all, delete-orphan",
    )
    motor: Mapped["PolicyMotor | None"] = relationship(
        back_populates="policy",
        uselist=False,
        cascade="all, delete-orphan",
    )
    commercial: Mapped["PolicyCommercial | None"] = relationship(
        back_populates="policy",
        uselist=False,
        cascade="all, delete-orphan",
    )
    claims: Mapped[list["Claim"]] = relationship(
        back_populates="policy",
        cascade="all, delete-orphan",
    )


class PolicyEndowment(Base):
    """``ENDOWMENT`` table — for policy_type='E'."""

    __tablename__ = "insurance_policy_endowment"

    policy_number: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("insurance_policy.policy_number", ondelete="CASCADE"),
        primary_key=True,
    )
    with_profits: Mapped[bool] = mapped_column(default=False, nullable=False)
    equities: Mapped[bool] = mapped_column(default=False, nullable=False)
    managed_fund: Mapped[bool] = mapped_column(default=False, nullable=False)
    fund_name: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    term: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sum_assured: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    life_assured: Mapped[str] = mapped_column(String(31), nullable=False, default="")

    policy: Mapped[Policy] = relationship(back_populates="endowment")


class PolicyHouse(Base):
    """``HOUSE`` table — for policy_type='H'."""

    __tablename__ = "insurance_policy_house"

    policy_number: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("insurance_policy.policy_number", ondelete="CASCADE"),
        primary_key=True,
    )
    property_type: Mapped[str] = mapped_column(String(15), nullable=False, default="")
    bedrooms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    house_name: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    house_number: Mapped[str] = mapped_column(String(4), nullable=False, default="")
    postcode: Mapped[str] = mapped_column(String(8), nullable=False, default="")

    policy: Mapped[Policy] = relationship(back_populates="house")


class PolicyMotor(Base):
    """``MOTOR`` table — for policy_type='M'."""

    __tablename__ = "insurance_policy_motor"

    policy_number: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("insurance_policy.policy_number", ondelete="CASCADE"),
        primary_key=True,
    )
    make: Mapped[str] = mapped_column(String(15), nullable=False, default="")
    model: Mapped[str] = mapped_column(String(15), nullable=False, default="")
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reg_number: Mapped[str] = mapped_column(String(7), nullable=False, default="")
    colour: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    cc: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    manufactured: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    premium: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accidents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    policy: Mapped[Policy] = relationship(back_populates="motor")


class PolicyCommercial(Base):
    """``COMMERCIAL`` table — for policy_type='C'."""

    __tablename__ = "insurance_policy_commercial"

    policy_number: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("insurance_policy.policy_number", ondelete="CASCADE"),
        primary_key=True,
    )
    address: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    postcode: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    latitude: Mapped[str] = mapped_column(String(11), nullable=False, default="")
    longitude: Mapped[str] = mapped_column(String(11), nullable=False, default="")
    customer_text: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    prop_type: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    fire_peril: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fire_premium: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    crime_peril: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    crime_premium: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flood_peril: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flood_premium: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weather_peril: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weather_premium: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reject_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    policy: Mapped[Policy] = relationship(back_populates="commercial")


class Claim(Base):
    """``CLAIM`` table — independent of policy type."""

    __tablename__ = "insurance_claim"

    claim_number: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    policy_number: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("insurance_policy.policy_number", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_date: Mapped[_dt.date] = mapped_column(Date, nullable=False)
    paid: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cause: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    observations: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    policy: Mapped[Policy] = relationship(back_populates="claims")
