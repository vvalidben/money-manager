"""Monthly budgets per expense category.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "budgets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                  nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                  nullable=False),
        sa.CheckConstraint("amount_minor > 0", name="ck_budgets_amount_positive"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"],
                                name="fk_budgets_category_id_categories", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_budgets"),
        sa.UniqueConstraint("category_id", name="uq_budgets_category_id"),
    )


def downgrade() -> None:
    op.drop_table("budgets")
