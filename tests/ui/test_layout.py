"""Every page fits the smallest supported window without being clipped sideways."""

from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from PySide6.QtWidgets import QApplication, QScrollArea

from money_manager.core.config import AppConfig
from money_manager.domain.entities import TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.services import AppServices
from money_manager.ui.main_window import MINIMUM_WINDOW_SIZE, MainWindow
from money_manager.ui.pages import PAGES
from tests.services.support import fixed_today
from tests.ui.support import wait_until


@pytest.fixture
def populated(app_services: AppServices) -> AppServices:
    s = app_services
    bank = s.accounts.create("Everyday bank account", opening_balance="25000",
                             opening_date=date(2026, 1, 1))
    salary = s.categories.create("Salary", CategoryKind.INCOME)
    food = s.categories.create("Groceries and household", CategoryKind.EXPENSE)
    for back in range(0, 120, 3):
        s.transactions.create(TransactionDraft(bank.id, TransactionType.EXPENSE, "123456.78",
                                               fixed_today() - timedelta(days=back), food.id,
                                               description="A fairly long description text"))
    s.transactions.create(TransactionDraft(bank.id, TransactionType.INCOME, "9999999.99",
                                           fixed_today(), salary.id))
    s.goals.create_manual("Emergency fund for the family", target="999999.99", current="12345")
    s.subscriptions.create("Streaming service premium", amount="149.99", frequency="monthly",
                           next_payment_date=fixed_today() + timedelta(days=2),
                           category_id=food.id, account_id=bank.id)
    etf = s.investments.create("World equity index fund", "etf")
    s.investments.add_contribution(etf.investment.id, "5000", fixed_today() - timedelta(days=9))
    s.investments.set_value(etf.investment.id, "5400", fixed_today())
    return s


@pytest.fixture
def window(qapp: QApplication, app_config: AppConfig,
           populated: AppServices) -> Iterator[MainWindow]:
    main = MainWindow(app_config, populated)
    main.resize(MINIMUM_WINDOW_SIZE)
    main.show()
    yield main
    main.close()
    main.deleteLater()


@pytest.mark.parametrize("key", [spec.key for spec in PAGES])
def test_page_fits_the_minimum_window(window: MainWindow, key: str) -> None:
    window.show_page(key)
    page = window.current_page
    wait_until(lambda: not getattr(page, "loading", False))
    for _ in range(3):
        QApplication.processEvents()
    assert page.width() <= window.width()
    for area in page.findChildren(QScrollArea):
        if area.isVisible() and area.widget() is not None:
            assert area.widget().width() <= area.viewport().width() + 1, (
                f"{key}: content {area.widget().width()} px wider than "
                f"{area.viewport().width()} px")


def test_every_rail_button_fits_the_smallest_window(window: MainWindow) -> None:
    rail = window.sidebar
    QApplication.processEvents()
    bottoms = [rail.button(spec.key).geometry().bottom() for spec in PAGES]
    status_top = rail._status_label.parentWidget().height()  # the rail itself
    assert max(bottoms) < status_top - 24, "the last page button would overlap the footer"
