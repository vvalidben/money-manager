"""Safety copies: listing them and restoring one."""

from datetime import date
from pathlib import Path

import pytest

from money_manager.core.errors import ValidationError
from money_manager.domain.entities import TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.persistence.database import Database
from money_manager.services import AppServices
from money_manager.services.data_service import RESET_CONFIRMATION, data_tables
from tests.services.support import fixed_today


@pytest.fixture
def filled(app_services: AppServices) -> AppServices:
    bank = app_services.accounts.create("Bank", opening_balance="10210",
                                        opening_date=date(2026, 1, 1))
    food = app_services.categories.create("Food", CategoryKind.EXPENSE)
    app_services.transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "90",
                                                      fixed_today(), food.id, description="Chill"))
    app_services.goals.create_with_new_allocation("tomobil", target="200000",
                                                  initial_amount="5000")
    return app_services


def test_reset_leaves_a_listed_copy(filled: AppServices) -> None:
    assert filled.data.safety_copies() == []
    filled.data.reset(RESET_CONFIRMATION)

    [copy] = filled.data.safety_copies()
    assert copy.reason == "before-reset" and copy.reason_text == "Before a reset"
    assert (copy.accounts, copy.transactions) == (1, 1) and copy.readable
    assert copy.size_bytes > 0


def test_restore_brings_everything_back_and_keeps_a_copy_of_now(
        filled: AppServices, database: Database) -> None:
    filled.data.reset(RESET_CONFIRMATION)
    filled.accounts.create("New start", opening_balance="1000", opening_date=date(2026, 1, 1))
    [before_reset] = filled.data.safety_copies()

    result = filled.data.restore_safety_copy(before_reset.path)

    assert filled.balances.total_balance() == Money.of("10120")
    assert [a.name for a in filled.accounts.list()] == ["Bank"]
    assert [g.goal.name for g in filled.goals.list()] == ["tomobil"]
    assert result.safety_backup is not None and result.safety_backup.is_file()
    reasons = [copy.reason for copy in filled.data.safety_copies()]
    assert "before-restore" in reasons  # "New start" can be restored again
    assert result.consistency is not None and result.consistency.is_consistent
    assert result.summary.count("accounts") == 1


def test_only_listed_copies_can_be_restored(filled: AppServices, tmp_path: Path) -> None:
    stranger = tmp_path / "elsewhere.db"
    stranger.write_bytes(b"")
    with pytest.raises(ValidationError, match="safety copies listed"):
        filled.data.restore_safety_copy(stranger)


def test_a_damaged_copy_is_listed_but_refused(filled: AppServices, database: Database) -> None:
    assert database.path is not None
    broken = database.path.with_name(
        f"{database.path.stem}.backup-before-reset-20260101T000000Z.db")
    broken.write_bytes(b"not a database at all")
    [copy] = filled.data.safety_copies()
    assert not copy.readable
    before = filled.balances.total_balance()
    with pytest.raises(ValidationError, match="cannot be"):
        filled.data.restore_safety_copy(copy.path)
    assert filled.balances.total_balance() == before  # nothing changed


def test_the_copy_itself_is_never_changed(filled: AppServices) -> None:
    filled.data.reset(RESET_CONFIRMATION)
    [copy] = filled.data.safety_copies()
    content = copy.path.read_bytes()
    filled.data.restore_safety_copy(copy.path)
    assert copy.path.read_bytes() == content


def test_every_data_table_is_restored(filled: AppServices) -> None:
    with filled.data._database.session() as session:  # type: ignore[attr-defined]
        before = {t.name: session.execute(t.select()).fetchall() for t in data_tables()}
    filled.data.reset(RESET_CONFIRMATION)
    [copy] = filled.data.safety_copies()
    filled.data.restore_safety_copy(copy.path)
    with filled.data._database.session() as session:  # type: ignore[attr-defined]
        after = {t.name: session.execute(t.select()).fetchall() for t in data_tables()}
    assert after == before
