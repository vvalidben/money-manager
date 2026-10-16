"""Subscriptions and their confirmed payments (Sprint 8).

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
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
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("normalized_name", sa.String(60), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("frequency", sa.String(16), nullable=False),
        sa.Column("next_payment_date", sa.Date(), nullable=False),
        sa.Column("anchor_day", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("amount_minor > 0", name="ck_subscriptions_amount_positive"),
        sa.CheckConstraint(
            "frequency IN ('weekly', 'monthly', 'quarterly', 'yearly')",
            name="ck_subscriptions_valid_frequency",
        ),
        sa.CheckConstraint("anchor_day BETWEEN 1 AND 31", name="ck_subscriptions_valid_anchor_day"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL",
                                name="fk_subscriptions_account_id_accounts"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT",
                                name="fk_subscriptions_category_id_categories"),
        sa.PrimaryKeyConstraint("id", name="pk_subscriptions"),
        sa.UniqueConstraint("normalized_name", name="uq_subscriptions_normalized_name"),
    )
    op.create_table(
        "subscription_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("status IN ('paid', 'skipped')",
                           name="ck_subscription_payments_valid_status"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE",
                                name="fk_subscription_payments_subscription_id_subscriptions"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="SET NULL",
                                name="fk_subscription_payments_transaction_id_transactions"),
        sa.PrimaryKeyConstraint("id", name="pk_subscription_payments"),
        sa.UniqueConstraint("subscription_id", "due_date", name="uq_subscription_payments_due"),
    )
    op.create_index("ix_subscription_payments_subscription_id", "subscription_payments",
                    ["subscription_id"])


def downgrade() -> None:
    op.drop_table("subscription_payments")
    op.drop_table("subscriptions")
