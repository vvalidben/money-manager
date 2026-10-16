"""Baseline: the schema shipped by Sprints 3–5 (before migrations existed).

Revision ID: 0001
Revises:
Create Date: 2026-09-27

Databases created before Alembic was introduced already have exactly this
schema; the migrator stamps them with this revision instead of running it.
This file is a frozen snapshot: it must never import the current models.
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
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
        "app_metadata",
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("value", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("key", name="pk_app_metadata"),
    )
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("normalized_name", sa.String(60), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("opening_balance_minor", sa.Integer(), nullable=False),
        sa.Column("opening_date", sa.Date(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("length(currency) = 3", name="ck_accounts_currency_code"),
        sa.PrimaryKeyConstraint("id", name="pk_accounts"),
        sa.UniqueConstraint("normalized_name", name="uq_accounts_normalized_name"),
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("normalized_name", sa.String(40), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("kind IN ('income', 'expense')", name="ck_categories_valid_kind"),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
        sa.UniqueConstraint("kind", "normalized_name", name="uq_categories_kind"),
    )
    op.create_table(
        "allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("normalized_name", sa.String(40), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_allocations"),
        sa.UniqueConstraint("normalized_name", name="uq_allocations_normalized_name"),
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("allocation_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("amount_minor > 0", name="ck_transactions_amount_positive"),
        sa.CheckConstraint(
            "type IN ('income', 'expense', 'adjustment_in', 'adjustment_out')",
            name="ck_transactions_valid_type",
        ),
        sa.CheckConstraint(
            "(type IN ('income', 'expense')) = (category_id IS NOT NULL)",
            name="ck_transactions_category_matches_type",
        ),
        sa.CheckConstraint(
            "allocation_id IS NULL OR type IN ('income', 'expense')",
            name="ck_transactions_allocation_only_for_income_expense",
        ),
        sa.CheckConstraint("length(currency) = 3", name="ck_transactions_currency_code"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT",
                                name="fk_transactions_account_id_accounts"),
        sa.ForeignKeyConstraint(["allocation_id"], ["allocations.id"], ondelete="RESTRICT",
                                name="fk_transactions_allocation_id_allocations"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT",
                                name="fk_transactions_category_id_categories"),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
    )
    op.create_index("ix_transactions_account_date", "transactions", ["account_id", "occurred_on"])
    op.create_index("ix_transactions_allocation_id", "transactions", ["allocation_id"])
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])
    op.create_table(
        "allocation_transfers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("from_allocation_id", sa.Integer(), nullable=True),
        sa.Column("to_allocation_id", sa.Integer(), nullable=True),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("note", sa.String(200), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("amount_minor > 0", name="ck_allocation_transfers_amount_positive"),
        sa.CheckConstraint(
            "COALESCE(from_allocation_id, 0) <> COALESCE(to_allocation_id, 0)",
            name="ck_allocation_transfers_distinct_endpoints",
        ),
        sa.ForeignKeyConstraint(["from_allocation_id"], ["allocations.id"], ondelete="RESTRICT",
                                name="fk_allocation_transfers_from_allocation_id_allocations"),
        sa.ForeignKeyConstraint(["to_allocation_id"], ["allocations.id"], ondelete="RESTRICT",
                                name="fk_allocation_transfers_to_allocation_id_allocations"),
        sa.PrimaryKeyConstraint("id", name="pk_allocation_transfers"),
    )
    op.create_index("ix_allocation_transfers_from_allocation_id", "allocation_transfers",
                    ["from_allocation_id"])
    op.create_index("ix_allocation_transfers_to_allocation_id", "allocation_transfers",
                    ["to_allocation_id"])


def downgrade() -> None:
    for table in ("allocation_transfers", "transactions", "allocations", "categories",
                  "accounts", "app_metadata"):
        op.drop_table(table)
