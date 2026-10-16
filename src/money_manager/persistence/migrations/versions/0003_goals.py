"""Goals table (Sprint 7).

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("normalized_name", sa.String(60), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("target_minor", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("allocation_id", sa.Integer(), nullable=True),
        sa.Column("manual_current_minor", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                  nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                  nullable=False),
        sa.CheckConstraint("target_minor > 0", name="ck_goals_target_positive"),
        sa.CheckConstraint(
            "(allocation_id IS NULL) <> (manual_current_minor IS NULL)",
            name="ck_goals_one_tracking_mode",
        ),
        sa.CheckConstraint(
            "manual_current_minor IS NULL OR manual_current_minor >= 0",
            name="ck_goals_manual_current_not_negative",
        ),
        sa.ForeignKeyConstraint(["allocation_id"], ["allocations.id"], ondelete="RESTRICT",
                                name="fk_goals_allocation_id_allocations"),
        sa.PrimaryKeyConstraint("id", name="pk_goals"),
        sa.UniqueConstraint("allocation_id", name="uq_goals_allocation_id"),
        sa.UniqueConstraint("normalized_name", name="uq_goals_normalized_name"),
    )


def downgrade() -> None:
    op.drop_table("goals")
