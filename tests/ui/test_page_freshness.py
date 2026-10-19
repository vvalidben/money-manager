"""Pages skip recalculating when nothing changed, and refresh when data does."""

from collections.abc import Iterator
from datetime import date

import pytest
from PySide6.QtWidgets import QApplication
from sqlalchemy import event

from money_manager.core.config import AppConfig
from money_manager.domain.entities import TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.persistence.database import Database
from money_manager.services import AppServices
from money_manager.ui.main_window import MainWindow
from money_manager.ui.pages import PAGES
from tests.services.support import fixed_today
from tests.ui.support import wait_until


@pytest.fixture
def window(qapp: QApplication, app_config: AppConfig,
           app_services: AppServices) -> Iterator[MainWindow]:
    main = MainWindow(app_config, app_services)
    main.show()
    yield main
    main.close()
    main.deleteLater()


def count_queries(database: Database, action) -> int:  # noqa: ANN001
    statements: list[str] = []
    listener = lambda *args: statements.append(args[2])  # noqa: E731
    event.listen(database.engine, "before_cursor_execute", listener)
    try:
        action()
    finally:
        event.remove(database.engine, "before_cursor_execute", listener)
    return len(statements)


def test_database_revision_counts_committed_writes(database: Database,
                                                   app_services: AppServices) -> None:
    start = database.revision
    app_services.accounts.list()
    assert database.revision == start  # reads do not count
    app_services.accounts.create("Bank", opening_balance="1", opening_date=date(2026, 1, 1))
    assert database.revision == start + 1
    with pytest.raises(Exception):
        app_services.accounts.create("Bank", opening_balance="1", opening_date=date(2026, 1, 1))
    assert database.revision == start + 1  # a rejected write changes nothing


@pytest.mark.parametrize("key", [spec.key for spec in PAGES
                                 if spec.key != "settings"])
def test_revisiting_an_unchanged_page_runs_no_queries(window: MainWindow, database: Database,
                                                      key: str) -> None:
    window.show_page(key)
    wait_until(lambda: not getattr(window.current_page, "loading", False))
    window.show_page("settings")
    assert count_queries(database, lambda: window.show_page(key)) <= 2  # AI status only


def test_changed_data_is_shown_on_the_next_visit(window: MainWindow,
                                                 app_services: AppServices) -> None:
    bank = app_services.accounts.create("Bank", opening_balance="100",
                                        opening_date=date(2026, 1, 1))
    window.show_page("dashboard")
    window.show_page("settings")
    salary = app_services.categories.create("Salary", CategoryKind.INCOME)
    app_services.transactions.create(TransactionDraft(bank.id, TransactionType.INCOME, "900",
                                                      fixed_today(), salary.id))
    window.show_page("dashboard")
    values = " ".join(card.value for card in window.current_page.stat_cards)  # type: ignore[attr-defined]
    assert "1,000.00" in values
