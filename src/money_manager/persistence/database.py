"""SQLite engine, session management and schema initialisation."""

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from money_manager import __version__
from money_manager.core.errors import DatabaseError
from money_manager.persistence.base import Base
from money_manager.persistence.migrator import backup_database, migrate
from money_manager.persistence.models import AppMetadata

logger = logging.getLogger(__name__)

CREATED_AT_KEY = "created_at"
CREATED_WITH_VERSION_KEY = "created_with_version"


def _configure_sqlite_connection(dbapi_connection: Any, _connection_record: Any) -> None:
    """Apply per-connection SQLite settings.

    SQLite does not enforce foreign keys unless asked to on every connection.
    WAL journaling keeps the file consistent if the app is killed mid-write.
    """
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA busy_timeout = 5000")
    finally:
        cursor.close()


_WRITE_PREFIXES = ("INSERT", "UPDATE", "DELETE", "REPLACE")


class Database:
    """Owns the SQLAlchemy engine and hands out transactional sessions.

    ``revision`` increases with every committed write, so the UI can skip
    recalculating a page when nothing has changed since it was last shown.
    """

    def __init__(self, url: str) -> None:
        self._engine = create_engine(url)
        self._revision = 0
        event.listen(self._engine, "connect", _configure_sqlite_connection)
        event.listen(self._engine, "before_cursor_execute", self._note_write)
        event.listen(self._engine, "commit", self._note_commit)
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    @property
    def revision(self) -> int:
        return self._revision

    @staticmethod
    def _note_write(connection: Any, _cursor: Any, statement: str, *_args: Any) -> None:
        if statement.lstrip()[:7].upper().startswith(_WRITE_PREFIXES):
            connection.info["money_manager_wrote"] = True

    def _note_commit(self, connection: Any) -> None:
        if connection.info.pop("money_manager_wrote", False):
            self._revision += 1

    @property
    def engine(self) -> Engine:
        return self._engine

    @property
    def path(self) -> Path | None:
        """The database file, or None for an in-memory database."""
        name = self._engine.url.database
        return Path(name) if name and name != ":memory:" else None

    def initialize(self) -> None:
        """Create or migrate the database to the current schema. Idempotent.

        Existing databases are backed up before any schema change (see
        ``persistence.migrator``). Raises ``DatabaseError`` if the file cannot
        be opened or its schema cannot be upgraded.
        """
        try:
            migrate(self._engine, self.path)
            self._verify_schema()
            with self.session() as session:
                if session.get(AppMetadata, CREATED_AT_KEY) is None:
                    session.add_all(
                        [
                            AppMetadata(key=CREATED_AT_KEY, value=datetime.now(UTC).isoformat()),
                            AppMetadata(key=CREATED_WITH_VERSION_KEY, value=__version__),
                        ]
                    )
                    logger.info("Created a new database")
        except SQLAlchemyError as exc:
            raise DatabaseError(
                f"Could not open or create the database at '{self._engine.url.database}'."
            ) from exc
        logger.info("Database ready at %s", self._engine.url.database)

    def _verify_schema(self) -> None:
        """Final guard: every column the models need must exist after migrating."""
        inspector = inspect(self._engine)
        for table in Base.metadata.sorted_tables:
            existing = {column["name"] for column in inspector.get_columns(table.name)}
            missing = sorted(column.name for column in table.columns if column.name not in existing)
            if missing:
                logger.error("Table %s is missing columns %s", table.name, missing)
                raise DatabaseError(
                    f"The database at '{self._engine.url.database}' was created by an older "
                    "development version of Money Manager and cannot be upgraded "
                    "automatically. Rename or move the file to start with a new database."
                )

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Unit of work: commits on success, rolls back on any exception.

        Low-level SQLAlchemy failures are re-raised as ``DatabaseError``.
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            logger.error("Database operation failed", exc_info=True)
            raise DatabaseError("A database operation failed; no changes were saved.") from exc
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()

    def backup(self, label: str, moment: datetime | None = None) -> Path | None:
        """Write a consistent copy of the database next to it; None for in-memory."""
        try:
            return backup_database(self._engine, self.path, label, moment)
        except (OSError, sqlite3.Error) as exc:
            raise DatabaseError(f"Could not write a backup of the database: {exc}") from exc

    def dispose(self) -> None:
        """Close all pooled connections (call on shutdown).

        ``PRAGMA optimize`` first lets SQLite refresh the statistics its query
        planner uses, as SQLite recommends before closing a connection.
        """
        try:
            with self._engine.connect() as connection:
                connection.exec_driver_sql("PRAGMA optimize")
        except SQLAlchemyError:
            logger.debug("PRAGMA optimize was skipped", exc_info=True)
        self._engine.dispose()
