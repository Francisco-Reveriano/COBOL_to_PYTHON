"""Initial CBSA schema.

Creates the tables migrated from the COBOL copybooks:

* ``customer`` — from ``CUSTOMER.cpy`` (was VSAM)
* ``account``  — from ``ACCDB2.cpy`` / ``ACCOUNT.cpy``
* ``control``  — from ``CONTDB2.cpy`` / ``CONTROLI.cpy``
* ``proctran`` — from ``PROCDB2.cpy`` / ``PROCTRAN.cpy``

Revision ID: 0001
Revises:
Create Date: 2026-05-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "customer",
        sa.Column("eyecatcher", sa.CHAR(4), nullable=False, server_default="CUST"),
        sa.Column("sortcode", sa.CHAR(6), nullable=False),
        sa.Column("number", sa.CHAR(10), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("address", sa.String(160), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("credit_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cs_review_date", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("sortcode", "number", name="pk_customer"),
    )

    op.create_table(
        "account",
        sa.Column("eyecatcher", sa.CHAR(4), nullable=False, server_default="ACCT"),
        sa.Column("customer_number", sa.CHAR(10), nullable=False, index=True),
        sa.Column("sortcode", sa.CHAR(6), nullable=False),
        sa.Column("number", sa.CHAR(8), nullable=False),
        sa.Column("type", sa.CHAR(8), nullable=False),
        sa.Column("interest_rate", sa.Numeric(4, 2), nullable=False, server_default="0"),
        sa.Column("opened", sa.Date(), nullable=False),
        sa.Column("overdraft_limit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_statement", sa.Date(), nullable=False),
        sa.Column("next_statement", sa.Date(), nullable=False),
        sa.Column(
            "available_balance", sa.Numeric(12, 2), nullable=False, server_default="0"
        ),
        sa.Column(
            "actual_balance", sa.Numeric(12, 2), nullable=False, server_default="0"
        ),
        sa.PrimaryKeyConstraint("sortcode", "number", name="pk_account"),
    )

    op.create_table(
        "control",
        sa.Column("name", sa.CHAR(32), primary_key=True),
        sa.Column("value_num", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("value_str", sa.CHAR(40), nullable=False, server_default=""),
    )

    op.create_table(
        "proctran",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("eyecatcher", sa.CHAR(4), nullable=False, server_default="PRTR"),
        sa.Column("sortcode", sa.CHAR(6), nullable=False, index=True),
        sa.Column("number", sa.CHAR(8), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("time", sa.Time(), nullable=False),
        sa.Column("ref", sa.CHAR(12), nullable=False, server_default=""),
        sa.Column("type", sa.CHAR(3), nullable=False),
        sa.Column("description", sa.String(40), nullable=False, server_default=""),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("proctran")
    op.drop_table("control")
    op.drop_table("account")
    op.drop_table("customer")
