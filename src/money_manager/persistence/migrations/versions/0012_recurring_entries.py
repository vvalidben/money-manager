"""Recurring entries: income or expenses recorded automatically on a schedule.

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recurring_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("frequency", sa.String(16), nullable=False),
        sa.Column("next_date", sa.Date(), nullable=False),
        sa.Column("anchor_day", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                  nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                  nullable=False),
        sa.CheckConstraint("amount_minor > 0", name="ck_recurring_entries_amount_positive"),
        sa.CheckConstraint("type IN ('income', 'expense')", name="ck_recurring_entries_valid_type"),
        sa.CheckConstraint("frequency IN ('weekly', 'monthly', 'quarterly', 'yearly')",
                           name="ck_recurring_entries_valid_frequency"),
        sa.CheckConstraint("anchor_day BETWEEN 1 AND 31",
                           name="ck_recurring_entries_valid_anchor_day"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"],
                                name="fk_recurring_entries_account_id_accounts",
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"],
                                name="fk_recurring_entries_category_id_categories",
                                ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_recurring_entries"),
    )
    op.create_index("ix_recurring_entries_account_id", "recurring_entries", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_recurring_entries_account_id", "recurring_entries")
    op.drop_table("recurring_entries")
