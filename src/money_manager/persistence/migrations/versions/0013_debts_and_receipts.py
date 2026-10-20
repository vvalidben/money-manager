"""Debts and loans, and receipts attached to transactions.

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-20
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
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
        "debts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("amount_minor > 0", name="ck_debts_amount_positive"),
        sa.CheckConstraint("direction IN ('lent', 'borrowed')", name="ck_debts_valid_direction"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"],
                                name="fk_debts_transaction_id_transactions", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_debts"),
    )
    op.create_table(
        "debt_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("debt_id", sa.Integer(), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("note", sa.String(200), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("amount_minor > 0", name="ck_debt_payments_amount_positive"),
        sa.ForeignKeyConstraint(["debt_id"], ["debts.id"],
                                name="fk_debt_payments_debt_id_debts", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"],
                                name="fk_debt_payments_transaction_id_transactions",
                                ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_debt_payments"),
    )
    op.create_index("ix_debt_payments_debt_id", "debt_payments", ["debt_id"])
    op.create_table(
        "receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(200), nullable=False),
        sa.Column("media_type", sa.String(40), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("size > 0", name="ck_receipts_size_positive"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"],
                                name="fk_receipts_transaction_id_transactions",
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_receipts"),
    )
    op.create_index("ix_receipts_transaction_id", "receipts", ["transaction_id"])


def downgrade() -> None:
    op.drop_index("ix_receipts_transaction_id", "receipts")
    op.drop_table("receipts")
    op.drop_index("ix_debt_payments_debt_id", "debt_payments")
    op.drop_table("debt_payments")
    op.drop_table("debts")
