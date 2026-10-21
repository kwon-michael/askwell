"""Record the LLM classifier's verdict on moderation reviews

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("moderation_reviews", sa.Column("llm_verdict", sa.String(16)))
    op.add_column("moderation_reviews", sa.Column("llm_reason", sa.String(500)))


def downgrade() -> None:
    op.drop_column("moderation_reviews", "llm_reason")
    op.drop_column("moderation_reviews", "llm_verdict")
