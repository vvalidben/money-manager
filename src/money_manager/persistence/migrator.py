"""Bring any supported database file up to the current schema.

Cases handled by ``migrate``:

* **New (or Sprint 1 metadata-only) database:** tables are created from the
  current models and stamped with the latest revision.
* **Pre-migration database** (Sprints 3–5 created tables without Alembic):
  it must match the baseline revision; it is backed up, stamped ``0001`` and
  upgraded.
* **Managed database behind the latest revision:** backed up, then upgraded.
* **Anything else** (e.g. a Sprint 2 development database) is refused.

Backups use SQLite's online backup API, so they are consistent even in WAL
mode, and are written next to the database as
``<name>.backup-<revision>-<UTC timestamp>.db``.
"""

import logging
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy import Connection, Engine, inspect

from money_manager.core.errors import DatabaseError
from money_manager.core.resources import resource_path
from money_manager.persistence.base import Base

logger = logging.getLogger(__name__)

# Bundled as plain files in a packaged build: Alembic reads the scripts from disk.
MIGRATIONS_DIR = resource_path("persistence", "migrations")
BASELINE_REVISION = "0001"
# Columns only present from the baseline onwards; their absence means an
# older development schema that cannot be upgraded.
_BASELINE_MARKERS = {
    "transactions": {"allocation_id"},
    "allocations": {"normalized_name"},
    "allocation_transfers": {"from_allocation_id", "to_allocation_id"},
}
_FINANCIAL_TABLES = {"accounts", "categories", "transactions"}


def alembic_config(connection: Connection | None = None) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def head_revision() -> str:
    head = ScriptDirectory.from_config(alembic_config()).get_current_head()
    assert head is not None
    return head


def current_revision(engine: Engine) -> str | None:
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def migrate(engine: Engine, database_path: Path | None) -> None:
    """Create, adopt or upgrade the database so it matches the current models."""
    tables = set(inspect(engine).get_table_names())
    head = head_revision()
    backed_up = False

    if "alembic_version" not in tables:
        if not tables & _FINANCIAL_TABLES:
            Base.metadata.create_all(engine)
            _run(engine, lambda config: command.stamp(config, head))
            logger.info("Created a new database at schema revision %s", head)
            return
        _require_baseline(engine, tables)
        backup_database(engine, database_path, "pre-migrations")
        backed_up = True
        _run(engine, lambda config: command.stamp(config, BASELINE_REVISION))
        logger.info("Adopted an existing database at the baseline revision")

    current = current_revision(engine)
    if current == head:
        return
    if current is not None and current not in known_revisions():
        raise DatabaseError(
            "The database was created by a newer version of Money Manager "
            f"(schema {current}). Please update the application."
        )
    if not backed_up:
        backup_database(engine, database_path, current or "none")
    _run(engine, lambda config: command.upgrade(config, "head"))
    logger.info("Upgraded the database schema from %s to %s", current, head)


def known_revisions() -> set[str]:
    script = ScriptDirectory.from_config(alembic_config())
    return {revision.revision for revision in script.walk_revisions()}


def _require_baseline(engine: Engine, tables: set[str]) -> None:
    inspector = inspect(engine)
    for table, columns in _BASELINE_MARKERS.items():
        present = {c["name"] for c in inspector.get_columns(table)} if table in tables else set()
        if not columns <= present:
            raise DatabaseError(
                f"The database at '{engine.url.database}' was created by an early development "
                "version of Money Manager and cannot be upgraded automatically. Rename or "
                "move the file to start with a new database."
            )


def _run(engine: Engine, operation: Callable[[Config], None]) -> None:
    try:
        with engine.begin() as connection:
            operation(alembic_config(connection))
    except CommandError as exc:
        raise DatabaseError(f"The database schema could not be updated: {exc}") from exc


def backup_database(engine: Engine, database_path: Path | None, label: str,
                    moment: datetime | None = None) -> Path | None:
    """Consistent copy next to the database (before a schema change, import or reset).

    The file name carries ``moment`` (default: now) in UTC. In-memory databases are skipped.
    """
    if database_path is None or not database_path.exists():
        return None
    stamp = (moment or datetime.now(UTC)).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = database_path.with_name(f"{database_path.stem}.backup-{label}-{stamp}.db")
    raw = engine.raw_connection()
    destination = sqlite3.connect(target)
    try:
        source = raw.driver_connection
        assert isinstance(source, sqlite3.Connection)
        source.backup(destination)
    finally:
        destination.close()
        raw.close()
    logger.info("Backed up the database to %s (%s)", target, label)
    return target
