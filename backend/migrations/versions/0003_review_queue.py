"""Moderator flag on users and the moderation review queue

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "moderation_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), unique=True),
        sa.Column("answer_id", sa.Integer(), sa.ForeignKey("answers.id"), unique=True),
        sa.Column("reason", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "(question_id IS NULL) <> (answer_id IS NULL)", name="ck_review_one_target"
        ),
    )
    op.create_index("ix_moderation_reviews_created_at", "moderation_reviews", ["created_at"])


def downgrade() -> None:
    op.drop_table("moderation_reviews")
    op.drop_column("users", "is_admin")
