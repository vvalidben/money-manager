"""Transfers between the user's own accounts.

A transfer is two balance adjustments (out of one account, into the other);
this table ties them together and keeps either side from being deleted alone.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_transfers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("out_transaction_id", sa.Integer(), nullable=False),
        sa.Column("in_transaction_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                  nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                  nullable=False),
        sa.CheckConstraint("out_transaction_id <> in_transaction_id",
                           name="ck_account_transfers_distinct_sides"),
        sa.ForeignKeyConstraint(["out_transaction_id"], ["transactions.id"],
                                name="fk_account_transfers_out_transaction_id_transactions",
                                ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["in_transaction_id"], ["transactions.id"],
                                name="fk_account_transfers_in_transaction_id_transactions",
                                ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_account_transfers"),
        sa.UniqueConstraint("out_transaction_id", name="uq_account_transfers_out_transaction_id"),
        sa.UniqueConstraint("in_transaction_id", name="uq_account_transfers_in_transaction_id"),
    )


def downgrade() -> None:
    op.drop_table("account_transfers")
