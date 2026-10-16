"""Schema migrations: new, pre-migration (Sprints 3–5) and managed databases."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from money_manager.core.errors import DatabaseError
from money_manager.persistence.base import Base
from money_manager.persistence.database import Database
from money_manager.persistence.migrator import (
    BASELINE_REVISION,
    alembic_config,
    current_revision,
    head_revision,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "money_manager.db"


@pytest.fixture
def database(db_path: Path) -> Iterator[Database]:
    db = Database(f"sqlite:///{db_path.as_posix()}")
    yield db
    db.dispose()


def _backups(db_path: Path) -> list[Path]:
    return sorted(db_path.parent.glob(f"{db_path.stem}.backup-*.db"))


def _upgrade_to(db_path: Path, revision: str) -> None:
    """Build a database by running the migration scripts themselves."""
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        with engine.begin() as connection:
            command.upgrade(alembic_config(connection), revision)
    finally:
        engine.dispose()


def _make_pre_migration_database(db_path: Path) -> None:
    """The exact schema Sprints 3–5 created, without Alembic's version table, plus data."""
    _upgrade_to(db_path, BASELINE_REVISION)
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE alembic_version")
        conn.execute(
            "INSERT INTO accounts (name, normalized_name, currency, opening_balance_minor, "
            "opening_date) VALUES ('Bank', 'bank', 'MAD', 1234567, '2026-01-01')"
        )
        conn.execute(
            "INSERT INTO categories (name, normalized_name, kind, is_archived) "
            "VALUES ('Food', 'food', 'expense', 0)"
        )
        conn.execute(
            "INSERT INTO transactions (account_id, category_id, type, amount_minor, currency, "
            "occurred_on, description, notes) VALUES (1, 1, 'expense', 30050, 'MAD', "
            "'2026-02-01', 'Groceries', '')"
        )
    conn.close()


def test_new_database_is_created_at_latest_revision(database: Database, db_path: Path) -> None:
    database.initialize()

    assert current_revision(database.engine) == head_revision()
    assert _backups(db_path) == []


def test_migration_scripts_produce_exactly_the_model_schema(db_path: Path) -> None:
    _upgrade_to(db_path, "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        with engine.connect() as connection:
            differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    finally:
        engine.dispose()

    assert differences == []


def test_pre_migration_database_is_backed_up_and_upgraded(
    database: Database, db_path: Path
) -> None:
    _make_pre_migration_database(db_path)

    database.initialize()

    assert current_revision(database.engine) == head_revision()
    columns = {c["name"] for c in inspect(database.engine).get_columns("categories")}
    assert "is_investment" in columns
    with database.engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT amount_minor, description FROM transactions").one() == (
            30050, "Groceries"
        )
        assert conn.exec_driver_sql("SELECT is_investment FROM categories").scalar() == 0
    [backup] = _backups(db_path)
    with sqlite3.connect(backup) as copy:
        assert copy.execute("SELECT opening_balance_minor FROM accounts").fetchone() == (1234567,)
    copy.close()


def test_managed_database_behind_head_is_upgraded(database: Database, db_path: Path) -> None:
    _upgrade_to(db_path, BASELINE_REVISION)

    database.initialize()

    assert current_revision(database.engine) == head_revision()
    assert len(_backups(db_path)) == 1


def test_up_to_date_database_is_left_alone(database: Database, db_path: Path) -> None:
    database.initialize()
    database.initialize()

    assert _backups(db_path) == []


def test_sprint_1_metadata_only_database_becomes_a_new_database(
    database: Database, db_path: Path
) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE app_metadata (key VARCHAR(64) PRIMARY KEY, value VARCHAR(255))")
    conn.close()

    database.initialize()

    assert current_revision(database.engine) == head_revision()
    assert "transactions" in inspect(database.engine).get_table_names()


def test_database_from_a_newer_version_is_refused(database: Database, db_path: Path) -> None:
    database.initialize()
    with database.engine.begin() as conn:
        conn.exec_driver_sql("UPDATE alembic_version SET version_num = '9999'")

    with pytest.raises(DatabaseError, match="newer version"):
        database.initialize()


def test_downgrade_of_latest_revision_works(db_path: Path) -> None:
    _upgrade_to(db_path, "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        with engine.begin() as connection:
            command.downgrade(alembic_config(connection), BASELINE_REVISION)
        columns = {c["name"] for c in inspect(engine).get_columns("categories")}
    finally:
        engine.dispose()

    assert "is_investment" not in columns
