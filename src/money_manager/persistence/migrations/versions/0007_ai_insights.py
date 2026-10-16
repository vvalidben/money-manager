"""AI insight history (Sprint 12).

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_insights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("is_online", sa.Boolean(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("truncated", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                  nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                  nullable=False),
        sa.CheckConstraint(
            "kind IN ('insights', 'suggestions', 'spending', 'monthly', 'question')",
            name="ck_ai_insights_valid_kind"),
        sa.CheckConstraint("period_start <= period_end", name="ck_ai_insights_period_in_order"),
        sa.PrimaryKeyConstraint("id", name="pk_ai_insights"),
    )
    op.create_index("ix_ai_insights_created_at", "ai_insights", ["created_at"])


def downgrade() -> None:
    op.drop_table("ai_insights")
