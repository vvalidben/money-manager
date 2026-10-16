from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import inspect, select

from money_manager import __version__
from money_manager.core.config import AppConfig
from money_manager.core.errors import DatabaseError
from money_manager.persistence.database import (
    CREATED_AT_KEY,
    CREATED_WITH_VERSION_KEY,
    Database,
)
from money_manager.persistence.models import AppMetadata


@pytest.fixture
def database(app_config: AppConfig) -> Iterator[Database]:
    app_config.data_dir.mkdir(parents=True)
    db = Database(app_config.database_url)
    yield db
    db.dispose()


def test_initialize_creates_database_file(database: Database, app_config: AppConfig) -> None:
    assert not app_config.database_path.exists()

    database.initialize()

    assert app_config.database_path.is_file()
    assert "app_metadata" in inspect(database.engine).get_table_names()


def test_initialize_records_creation_metadata(database: Database) -> None:
    database.initialize()

    with database.session() as session:
        values = {row.key: row.value for row in session.scalars(select(AppMetadata))}

    assert values[CREATED_WITH_VERSION_KEY] == __version__
    assert CREATED_AT_KEY in values


def test_initialize_is_idempotent(database: Database) -> None:
    database.initialize()
    with database.session() as session:
        created_at = session.get(AppMetadata, CREATED_AT_KEY)
        assert created_at is not None
        original = created_at.value

    database.initialize()

    with database.session() as session:
        rows = session.scalars(select(AppMetadata)).all()
        created_at = session.get(AppMetadata, CREATED_AT_KEY)
        assert created_at is not None
        assert created_at.value == original
    assert len(rows) == 2


def test_foreign_keys_are_enforced(database: Database) -> None:
    with database.engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


def test_uses_wal_journal(database: Database) -> None:
    with database.engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"


def test_session_commits_on_success(database: Database) -> None:
    database.initialize()

    with database.session() as session:
        session.add(AppMetadata(key="example", value="1"))

    with database.session() as session:
        assert session.get(AppMetadata, "example") is not None


def test_session_rolls_back_on_error(database: Database) -> None:
    database.initialize()

    with pytest.raises(RuntimeError), database.session() as session:
        session.add(AppMetadata(key="example", value="1"))
        session.flush()
        raise RuntimeError("abort")

    with database.session() as session:
        assert session.get(AppMetadata, "example") is None


def test_outdated_schema_is_detected(database: Database) -> None:
    # A transactions table from an older build, without the allocation_id column.
    with database.engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE transactions (id INTEGER PRIMARY KEY, account_id INTEGER, "
            "category_id INTEGER, type VARCHAR(20), amount_minor INTEGER, currency VARCHAR(3), "
            "occurred_on DATE, description VARCHAR(200), notes TEXT, created_at DATETIME, "
            "updated_at DATETIME)"
        )

    with pytest.raises(DatabaseError, match="cannot be upgraded automatically"):
        database.initialize()


def test_unopenable_database_raises_database_error(tmp_path: Path) -> None:
    # A directory cannot be opened as an SQLite file.
    db = Database(f"sqlite:///{tmp_path.as_posix()}")
    try:
        with pytest.raises(DatabaseError, match="Could not open or create the database"):
            db.initialize()
    finally:
        db.dispose()
