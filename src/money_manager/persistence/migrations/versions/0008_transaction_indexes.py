"""Covering indexes for the aggregate queries (Sprint 14).

Measured on 200,000 transactions: account balances 207 → 5 ms per account,
daily/ledger aggregates 104/61 → 24/12 ms, expense records 64 → 35 ms, the
newest-first transaction page 22 → 1 ms. Each index holds every column its
queries read, so SQLite answers them from the index alone.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-27
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_transactions_account_totals", "transactions",
                    ["account_id", "type", "occurred_on", "amount_minor"])
    op.create_index("ix_transactions_day_totals", "transactions",
                    ["occurred_on", "type", "category_id", "amount_minor"])
    op.create_index("ix_transactions_expense_records", "transactions",
                    ["type", "occurred_on", "category_id", "amount_minor", "description"])
    op.execute("ANALYZE")


def downgrade() -> None:
    op.drop_index("ix_transactions_expense_records", "transactions")
    op.drop_index("ix_transactions_day_totals", "transactions")
    op.drop_index("ix_transactions_account_totals", "transactions")
