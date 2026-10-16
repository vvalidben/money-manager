"""Alembic environment: runs on a connection handed over by the migrator."""

from alembic import context

from money_manager.persistence.base import Base
from money_manager.persistence import models  # noqa: F401  (registers every table)

config = context.config
connection = config.attributes.get("connection")
if connection is None:
    raise RuntimeError("Migrations must be run through money_manager.persistence.migrator.")

context.configure(
    connection=connection,
    target_metadata=Base.metadata,
    render_as_batch=True,  # SQLite needs table rebuilds for most ALTERs
)
with context.begin_transaction():
    context.run_migrations()
