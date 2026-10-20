"""Click every visible, enabled button on every page (empty and with data).

Modal dialogs are cancelled automatically. Exceptions raised inside Qt slots
are only printed by Qt, so they are captured through ``sys.excepthook``:
any exception there fails the test.
"""

import sys
from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QHeaderView,
    QInputDialog,
    QPushButton,
)
from shiboken6 import isValid

from money_manager.ai.settings import AIMode, AISettings
from money_manager.core.config import AppConfig
from money_manager.domain.entities import TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.main_window import MainWindow
from money_manager.ui.pages import PAGES
from tests.ai.support import ScriptedProvider
from tests.services.support import fixed_today
from tests.ui.support import wait_until


@pytest.fixture
def slot_errors(monkeypatch: pytest.MonkeyPatch) -> list[BaseException]:
    errors: list[BaseException] = []
    monkeypatch.setattr(sys, "excepthook", lambda kind, value, tb: errors.append(value))
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *args, **kw: ("", False)))
    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(lambda *args, **kw: ("", False)))
    for name in ("show_error", "show_warning", "show_info"):
        monkeypatch.setattr(dialogs, name, lambda *args: None)
    monkeypatch.setattr(dialogs, "ask_save_path", lambda *args: None)
    monkeypatch.setattr(dialogs, "ask_open_path", lambda *args: None)
    monkeypatch.setattr(dialogs, "confirm_destructive", lambda *args: False)
    monkeypatch.setattr(dialogs, "choose", lambda *args: None)
    return errors


def populate(s: AppServices) -> None:
    today = fixed_today()
    bank = s.accounts.create("Bank", opening_balance="5000", opening_date=date(2026, 1, 1))
    salary = s.categories.create("Salary", CategoryKind.INCOME)
    food = s.categories.create("Food", CategoryKind.EXPENSE)
    stocks = s.categories.create("Stocks", CategoryKind.EXPENSE)
    s.categories.set_investment(stocks.id, True)
    pot = s.allocations.create("Holiday", initial_amount="500")
    for month in range(1, 7):
        s.transactions.create(TransactionDraft(bank.id, TransactionType.INCOME, "9000",
                                               date(2026, month, 1), salary.id, "Pay"))
        s.transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "120",
                                               date(2026, month, 3), food.id, "Market",
                                               allocation_id=pot.id if month == 6 else None))
    s.goals.create_with_new_allocation("Car", target="20000", initial_amount="1000",
                                       deadline=today + timedelta(days=300))
    s.goals.create_manual("Gift", target="800", current="100")
    s.subscriptions.create("Netflix", amount="65", frequency="monthly",
                           next_payment_date=today - timedelta(days=1), category_id=food.id,
                           account_id=bank.id)
    fund = s.investments.create("ETF", "etf")
    s.investments.add_contribution(fund.investment.id, "1000", date(2026, 6, 2),
                                   account_id=bank.id, category_id=stocks.id)
    s.investments.set_value(fund.investment.id, "1100", today)
    s.ai.save_settings(AISettings(AIMode.LOCAL, local_model="llama3.2"))


@pytest.fixture
def window(qapp: QApplication, app_config: AppConfig,
           app_services: AppServices) -> Iterator[MainWindow]:
    main = MainWindow(app_config, app_services)
    main.resize(1280, 860)
    main.show()
    yield main
    main.close()
    main.deleteLater()


def select_first_rows(page: object) -> None:
    """Select the first row of every list so row actions are enabled."""
    for view in page.findChildren(QAbstractItemView):  # type: ignore[attr-defined]
        model = view.model()
        if isinstance(view, QHeaderView):  # shares the table's selection
            continue
        if view.isVisible() and model is not None and model.rowCount() > 0:
            view.setCurrentIndex(model.index(0, 0))
            if hasattr(view, "selectRow"):
                view.selectRow(0)


def settle(page: object) -> None:
    wait_until(lambda: not getattr(page, "loading", False) and not getattr(page, "busy", False))


def click_everything(window: MainWindow) -> int:
    clicked = 0
    for spec in PAGES:
        window.show_page(spec.key)
        page = window.current_page
        settle(page)
        buttons = list(page.findChildren(QPushButton))
        for button in buttons:
            if window.current_page is not page:  # a button navigated away: come back
                window.show_page(spec.key)
                settle(page)
            select_first_rows(page)
            if not isValid(button) or not button.isVisible() or not button.isEnabled():
                continue
            button.click()
            clicked += 1
            QApplication.processEvents()
            settle(page)
    return clicked


def test_every_button_on_empty_pages(window: MainWindow,
                                     slot_errors: list[BaseException]) -> None:
    assert click_everything(window) > 20
    assert slot_errors == []


def test_every_button_with_data(window: MainWindow, app_services: AppServices,
                                slot_errors: list[BaseException],
                                monkeypatch: pytest.MonkeyPatch) -> None:
    populate(app_services)
    monkeypatch.setattr(app_services.ai, "provider", lambda settings=None: ScriptedProvider())
    assert click_everything(window) > 60
    # Twice: the first round changed state (payments recorded, answers stored, …).
    click_everything(window)
    assert slot_errors == []


@pytest.mark.parametrize("code", ["fr", "ar"])
def test_every_button_in_another_language(window: MainWindow, app_services: AppServices,
                                          slot_errors: list[BaseException],
                                          monkeypatch: pytest.MonkeyPatch, code: str) -> None:
    """The same in French and Arabic (wrong placeholders would raise here)."""
    from money_manager.core.i18n import set_language

    populate(app_services)
    monkeypatch.setattr(app_services.ai, "provider", lambda settings=None: ScriptedProvider())
    set_language(code)
    try:
        assert click_everything(window) > 60
        click_everything(window)
    finally:
        set_language("en")
    assert slot_errors == []
