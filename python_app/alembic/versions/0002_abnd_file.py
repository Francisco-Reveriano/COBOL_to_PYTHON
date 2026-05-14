"""Add the ``abnd_file`` audit table (FR-07 / ABNDPROC port).

The COBOL ``ABNDPROC`` (see ``src/base/cobol_src/ABNDPROC.cbl``) writes one
row per application abend to the ``ABNDFILE`` KSDS dataset using the layout
in ``ABNDINFO.cpy``.  This migration creates the relational equivalent so
the FastAPI global exception handler can persist one row per uncaught
service exception (SDD §7.3).

Revision ID: 0002_abnd_file
Revises: 0001
Create Date: 2026-05-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0002_abnd_file"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "abnd_file",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("eyecatcher", sa.CHAR(4), nullable=False, server_default="ABND"),
        sa.Column("abend_code", sa.CHAR(4), nullable=False),
        sa.Column("program", sa.String(20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("time", sa.Time(), nullable=False),
        sa.Column("sqlcode", sa.Integer(), nullable=True),
        sa.Column("freeform", sa.String(600), nullable=False, server_default=""),
        sa.Column("tran_id", sa.CHAR(4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_abnd_file_created_at", "abnd_file", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_abnd_file_created_at", table_name="abnd_file")
    op.drop_table("abnd_file")
