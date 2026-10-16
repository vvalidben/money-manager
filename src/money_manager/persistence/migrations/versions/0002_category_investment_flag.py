"""Categories: add ``is_investment`` flag (Sprint 6 investment metrics).

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adding a column with a constant default is a plain ALTER TABLE on SQLite,
    # so existing rows (and foreign keys pointing at categories) are untouched.
    op.add_column(
        "categories",
        sa.Column("is_investment", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    with op.batch_alter_table("categories") as batch:
        batch.drop_column("is_investment")
