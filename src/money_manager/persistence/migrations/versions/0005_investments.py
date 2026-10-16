"""Investments, their contributions/withdrawals and valuations (Sprint 9).

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                  nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                  nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "investments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("normalized_name", sa.String(60), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("kind IN ('stock', 'etf', 'crypto', 'gold', 'other')",
                           name="ck_investments_valid_kind"),
        sa.PrimaryKeyConstraint("id", name="pk_investments"),
        sa.UniqueConstraint("normalized_name", name="uq_investments_normalized_name"),
    )
    op.create_table(
        "investment_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("investment_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=True),
        sa.Column("occurred_on", sa.Date(), nullable=True),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(200), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("kind IN ('contribution', 'withdrawal')",
                           name="ck_investment_entries_valid_kind"),
        sa.CheckConstraint(
            "(transaction_id IS NULL AND amount_minor > 0 AND occurred_on IS NOT NULL) OR "
            "(transaction_id IS NOT NULL AND amount_minor IS NULL AND occurred_on IS NULL)",
            name="ck_investment_entries_own_amount_or_transaction",
        ),
        sa.CheckConstraint(
            "transaction_id IS NULL OR kind = 'contribution'",
            name="ck_investment_entries_only_contributions_have_transactions",
        ),
        sa.ForeignKeyConstraint(["investment_id"], ["investments.id"], ondelete="CASCADE",
                                name="fk_investment_entries_investment_id_investments"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE",
                                name="fk_investment_entries_transaction_id_transactions"),
        sa.PrimaryKeyConstraint("id", name="pk_investment_entries"),
        sa.UniqueConstraint("transaction_id", name="uq_investment_entries_transaction_id"),
    )
    op.create_index("ix_investment_entries_investment_id", "investment_entries",
                    ["investment_id"])
    op.create_table(
        "investment_valuations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("investment_id", sa.Integer(), nullable=False),
        sa.Column("valued_on", sa.Date(), nullable=False),
        sa.Column("value_minor", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(200), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("value_minor >= 0", name="ck_investment_valuations_value_not_negative"),
        sa.ForeignKeyConstraint(["investment_id"], ["investments.id"], ondelete="CASCADE",
                                name="fk_investment_valuations_investment_id_investments"),
        sa.PrimaryKeyConstraint("id", name="pk_investment_valuations"),
        sa.UniqueConstraint("investment_id", "valued_on", name="uq_investment_valuations_day"),
    )
    op.create_index("ix_investment_valuations_investment_id", "investment_valuations",
                    ["investment_id"])


def downgrade() -> None:
    op.drop_table("investment_valuations")
    op.drop_table("investment_entries")
    op.drop_table("investments")
