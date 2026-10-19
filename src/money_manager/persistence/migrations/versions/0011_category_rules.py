"""Category rules: keywords that put matching descriptions in a category.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "category_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("keyword", sa.String(60), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                  nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"),
                  nullable=False),
        sa.CheckConstraint("kind IN ('income', 'expense')", name="ck_category_rules_valid_kind"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"],
                                name="fk_category_rules_category_id_categories",
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_category_rules"),
        sa.UniqueConstraint("keyword", "kind", name="uq_category_rules_keyword"),
    )
    op.create_index("ix_category_rules_category_id", "category_rules", ["category_id"])


def downgrade() -> None:
    op.drop_index("ix_category_rules_category_id", "category_rules")
    op.drop_table("category_rules")
