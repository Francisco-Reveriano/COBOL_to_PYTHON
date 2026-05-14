"""GenApp insurance schema.

Adds the tables for the GenApp insurance domain, ported from
``cics-genapp/base/src/lgpolicy.cpy``:

* ``insurance_customer``               — from ``DB2-CUSTOMER``
* ``insurance_policy``                 — from ``DB2-POLICY``
* ``insurance_policy_endowment``       — from ``DB2-ENDOWMENT``
* ``insurance_policy_house``           — from ``DB2-HOUSE``
* ``insurance_policy_motor``           — from ``DB2-MOTOR``
* ``insurance_policy_commercial``      — from ``DB2-COMMERCIAL``
* ``insurance_claim``                  — from ``DB2-CLAIM``

Revision ID: 0002_insurance_schema
Revises: 0001
Create Date: 2026-05-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0002_insurance_schema"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "insurance_customer",
        sa.Column("customer_number", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(10), nullable=False),
        sa.Column("last_name", sa.String(20), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("house_name", sa.String(20), nullable=False, server_default=""),
        sa.Column("house_number", sa.String(4), nullable=False, server_default=""),
        sa.Column("postcode", sa.String(8), nullable=False, server_default=""),
        sa.Column("phone_mobile", sa.String(20), nullable=False, server_default=""),
        sa.Column("phone_home", sa.String(20), nullable=False, server_default=""),
        sa.Column("email_address", sa.String(100), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.PrimaryKeyConstraint("customer_number", name="pk_insurance_customer"),
    )

    op.create_table(
        "insurance_policy",
        sa.Column(
            "policy_number",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("customer_number", sa.Integer(), nullable=False, index=True),
        sa.Column("policy_type", sa.CHAR(1), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column(
            "last_changed",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column("broker_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "brokers_reference", sa.String(10), nullable=False, server_default=""
        ),
        sa.Column("payment", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["customer_number"],
            ["insurance_customer.customer_number"],
            name="fk_policy_customer",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "insurance_policy_endowment",
        sa.Column("policy_number", sa.Integer(), nullable=False),
        sa.Column(
            "with_profits", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("equities", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "managed_fund", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("fund_name", sa.String(10), nullable=False, server_default=""),
        sa.Column("term", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sum_assured", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("life_assured", sa.String(31), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("policy_number", name="pk_endowment"),
        sa.ForeignKeyConstraint(
            ["policy_number"],
            ["insurance_policy.policy_number"],
            name="fk_endowment_policy",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "insurance_policy_house",
        sa.Column("policy_number", sa.Integer(), nullable=False),
        sa.Column("property_type", sa.String(15), nullable=False, server_default=""),
        sa.Column("bedrooms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("house_name", sa.String(20), nullable=False, server_default=""),
        sa.Column("house_number", sa.String(4), nullable=False, server_default=""),
        sa.Column("postcode", sa.String(8), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("policy_number", name="pk_house"),
        sa.ForeignKeyConstraint(
            ["policy_number"],
            ["insurance_policy.policy_number"],
            name="fk_house_policy",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "insurance_policy_motor",
        sa.Column("policy_number", sa.Integer(), nullable=False),
        sa.Column("make", sa.String(15), nullable=False, server_default=""),
        sa.Column("model", sa.String(15), nullable=False, server_default=""),
        sa.Column("value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reg_number", sa.String(7), nullable=False, server_default=""),
        sa.Column("colour", sa.String(8), nullable=False, server_default=""),
        sa.Column("cc", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manufactured", sa.String(10), nullable=False, server_default=""),
        sa.Column("premium", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accidents", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("policy_number", name="pk_motor"),
        sa.ForeignKeyConstraint(
            ["policy_number"],
            ["insurance_policy.policy_number"],
            name="fk_motor_policy",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "insurance_policy_commercial",
        sa.Column("policy_number", sa.Integer(), nullable=False),
        sa.Column("address", sa.String(255), nullable=False, server_default=""),
        sa.Column("postcode", sa.String(8), nullable=False, server_default=""),
        sa.Column("latitude", sa.String(11), nullable=False, server_default=""),
        sa.Column("longitude", sa.String(11), nullable=False, server_default=""),
        sa.Column("customer_text", sa.String(255), nullable=False, server_default=""),
        sa.Column("prop_type", sa.String(255), nullable=False, server_default=""),
        sa.Column("fire_peril", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fire_premium", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("crime_peril", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("crime_premium", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("flood_peril", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("flood_premium", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weather_peril", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "weather_premium", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("status", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reject_reason", sa.String(255), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("policy_number", name="pk_commercial"),
        sa.ForeignKeyConstraint(
            ["policy_number"],
            ["insurance_policy.policy_number"],
            name="fk_commercial_policy",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "insurance_claim",
        sa.Column(
            "claim_number",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("policy_number", sa.Integer(), nullable=False, index=True),
        sa.Column("claim_date", sa.Date(), nullable=False),
        sa.Column("paid", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cause", sa.String(255), nullable=False, server_default=""),
        sa.Column("observations", sa.String(255), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(
            ["policy_number"],
            ["insurance_policy.policy_number"],
            name="fk_claim_policy",
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("insurance_claim")
    op.drop_table("insurance_policy_commercial")
    op.drop_table("insurance_policy_motor")
    op.drop_table("insurance_policy_house")
    op.drop_table("insurance_policy_endowment")
    op.drop_table("insurance_policy")
    op.drop_table("insurance_customer")
