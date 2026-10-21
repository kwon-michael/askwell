"""Moderation status on questions and answers

Existing rows are backfilled as 'published' so nothing disappears from the site.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("questions", "answers"):
        op.add_column(
            table,
            sa.Column("status", sa.String(16), nullable=False, server_default="published"),
        )


def downgrade() -> None:
    for table in ("questions", "answers"):
        op.drop_column(table, "status")
