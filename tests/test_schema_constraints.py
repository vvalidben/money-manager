"""The database itself rejects inconsistent financial rows, even without services."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Connection
from sqlalchemy.exc import IntegrityError

from money_manager.core.config import AppConfig
from money_manager.persistence.database import Database


@pytest.fixture
def connection(app_config: AppConfig) -> Iterator[Connection]:
    app_config.data_dir.mkdir(parents=True)
    db = Database(app_config.database_url)
    db.initialize()
    with db.engine.connect() as conn:
        conn.exec_driver_sql(
            "INSERT INTO accounts (id, name, normalized_name, currency, opening_balance_minor, "
            "opening_date) VALUES (1, 'Main', 'main', 'MAD', 0, '2026-01-01')"
        )
        conn.exec_driver_sql(
            "INSERT INTO categories (id, name, normalized_name, kind, is_archived) "
            "VALUES (1, 'Food', 'food', 'expense', 0)"
        )
        conn.commit()
        yield conn
    db.dispose()


def _insert(conn: Connection, *, type_: str = "expense", amount: int = 100,
            category_id: int | None = 1, account_id: int = 1) -> None:
    conn.exec_driver_sql(
        "INSERT INTO transactions (account_id, category_id, type, amount_minor, currency, "
        "occurred_on, description, notes) VALUES (?, ?, ?, ?, 'MAD', '2026-02-01', '', '')",
        (account_id, category_id, type_, amount),
    )


def test_valid_row_is_stored_as_integer(connection: Connection) -> None:
    _insert(connection, amount=1234)

    assert connection.exec_driver_sql("SELECT typeof(amount_minor) FROM transactions").scalar() == (
        "integer"
    )


@pytest.mark.parametrize("amount", [0, -100])
def test_amount_must_be_positive(connection: Connection, amount: int) -> None:
    with pytest.raises(IntegrityError):
        _insert(connection, amount=amount)


def test_type_must_be_known(connection: Connection) -> None:
    with pytest.raises(IntegrityError):
        _insert(connection, type_="transfer")


def test_income_and_expense_need_a_category(connection: Connection) -> None:
    with pytest.raises(IntegrityError):
        _insert(connection, category_id=None)


def test_adjustments_must_not_have_a_category(connection: Connection) -> None:
    with pytest.raises(IntegrityError):
        _insert(connection, type_="adjustment_in", category_id=1)


def test_unknown_account_is_rejected(connection: Connection) -> None:
    with pytest.raises(IntegrityError):
        _insert(connection, account_id=99)


def test_used_category_cannot_be_deleted(connection: Connection) -> None:
    _insert(connection)

    with pytest.raises(IntegrityError):
        connection.exec_driver_sql("DELETE FROM categories WHERE id = 1")


def test_adjustments_cannot_have_an_allocation(connection: Connection) -> None:
    connection.exec_driver_sql(
        "INSERT INTO allocations (id, name, normalized_name, is_archived) "
        "VALUES (1, 'Bills', 'bills', 0)"
    )
    connection.exec_driver_sql(
        "INSERT INTO transactions (account_id, category_id, allocation_id, type, amount_minor, "
        "currency, occurred_on, description, notes) "
        "VALUES (1, 1, 1, 'expense', 100, 'MAD', '2026-02-01', '', '')"
    )  # tagged expense is fine

    with pytest.raises(IntegrityError):
        connection.exec_driver_sql(
            "INSERT INTO transactions (account_id, category_id, allocation_id, type, "
            "amount_minor, currency, occurred_on, description, notes) "
            "VALUES (1, NULL, 1, 'adjustment_out', 100, 'MAD', '2026-02-01', '', '')"
        )


def _insert_transfer(conn: Connection, source: int | None, target: int | None, amount: int) -> None:
    conn.exec_driver_sql(
        "INSERT INTO allocation_transfers (from_allocation_id, to_allocation_id, amount_minor, "
        "occurred_on, note) VALUES (?, ?, ?, '2026-02-01', '')",
        (source, target, amount),
    )


@pytest.mark.parametrize(
    ("source", "target", "amount"),
    [(None, None, 100), (1, 1, 100), (None, 1, 0), (None, 1, -5), (None, 99, 100)],
)
def test_invalid_transfers_rejected(
    connection: Connection, source: int | None, target: int | None, amount: int
) -> None:
    connection.exec_driver_sql(
        "INSERT INTO allocations (id, name, normalized_name, is_archived) "
        "VALUES (1, 'Savings', 'savings', 0)"
    )
    _insert_transfer(connection, None, 1, 100)  # a valid one

    with pytest.raises(IntegrityError):
        _insert_transfer(connection, source, target, amount)


def test_allocation_with_transfers_cannot_be_deleted(connection: Connection) -> None:
    connection.exec_driver_sql(
        "INSERT INTO allocations (id, name, normalized_name, is_archived) "
        "VALUES (1, 'Savings', 'savings', 0)"
    )
    _insert_transfer(connection, None, 1, 100)

    with pytest.raises(IntegrityError):
        connection.exec_driver_sql("DELETE FROM allocations WHERE id = 1")


def test_category_names_unique_per_kind(connection: Connection) -> None:
    with pytest.raises(IntegrityError):
        connection.exec_driver_sql(
            "INSERT INTO categories (name, normalized_name, kind, is_archived) "
            "VALUES ('FOOD', 'food', 'expense', 0)"
        )
