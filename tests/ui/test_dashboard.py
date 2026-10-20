from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

import pytest
from matplotlib.backend_bases import MouseEvent
from matplotlib.dates import date2num
from PySide6.QtWidgets import QApplication, QDialog

from money_manager.core.config import AppConfig
from money_manager.domain.dashboard import BalancePoint, CategorySpending, MonthlyFlow
from money_manager.domain.entities import Account, Category, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.health import HealthLevel
from money_manager.domain.money import Money
from money_manager.services import AppServices
from money_manager.ui.accounts.account_dialog import AccountDialog
from money_manager.ui.charts.money import (
    BalanceHistoryChart,
    CategorySpendingChart,
    IncomeExpenseChart,
    balance_history_table,
    income_expense_table,
)
from money_manager.ui.dashboard.dashboard_page import DashboardPage
from money_manager.ui.dashboard.view_model import build_dashboard_view
from money_manager.ui.formatting import format_compact_amount, format_day_range, format_percent
from money_manager.ui.main_window import MainWindow
from money_manager.ui.pages import DASHBOARD_PAGE_KEY, PAGES, TRANSACTIONS_PAGE_KEY
from tests.services.support import TODAY

SPEC = next(spec for spec in PAGES if spec.key == DASHBOARD_PAGE_KEY)
JUNE_1 = date(2026, 6, 1)


@pytest.fixture
def bank(app_services: AppServices) -> Account:
    return app_services.accounts.create("Bank", opening_balance="29920", opening_date=date(2026, 1, 1))


@pytest.fixture
def categories(app_services: AppServices) -> dict[str, Category]:
    return {
        "salary": app_services.categories.create("Salary", CategoryKind.INCOME),
        "rent": app_services.categories.create("Rent", CategoryKind.EXPENSE),
        "food": app_services.categories.create("Food", CategoryKind.EXPENSE),
    }


@pytest.fixture
def populated(app_services: AppServices, bank: Account, categories: dict[str, Category]) -> None:
    for type_, amount, name, on, description in (
        (TransactionType.INCOME, "12000", "salary", JUNE_1, "June salary"),
        (TransactionType.EXPENSE, "4500", "rent", date(2026, 6, 2), "Rent"),
        (TransactionType.EXPENSE, "2920", "food", date(2026, 6, 10), "Groceries"),
        (TransactionType.EXPENSE, "300", "food", date(2026, 5, 10), "May groceries"),
    ):
        app_services.transactions.create(TransactionDraft(
            bank.id, type_, amount, on, categories[name].id, description=description))
    app_services.allocations.create("Savings", initial_amount="8000")


@pytest.fixture
def page(qapp: QApplication, app_services: AppServices) -> Iterator[DashboardPage]:
    widget = DashboardPage(SPEC, app_services)
    widget.resize(1280, 900)
    widget.show()
    yield widget
    widget.close()
    widget.deleteLater()


class TestFormatting:
    def test_percent(self) -> None:
        assert format_percent(Decimal("0.3817")) == "38.2%"
        assert format_percent(Decimal("0.1"), signed=True) == "+10.0%"
        assert format_percent(Decimal("-0.05"), signed=True) == "−5.0%"
        assert format_percent(Decimal("0"), signed=True) == "0.0%"

    @pytest.mark.parametrize(
        ("value", "text"),
        [("0", "0"), ("950", "950"), ("12000", "12k"), ("1500", "1.5k"),
         ("2500000", "2.5M"), ("-4000", "−4k")],
    )
    def test_compact(self, value: str, text: str) -> None:
        assert format_compact_amount(Decimal(value)) == text

    def test_day_range(self) -> None:
        assert format_day_range(date(2026, 6, 1), date(2026, 6, 15)) == "1–15 Jun"
        assert format_day_range(date(2026, 5, 28), date(2026, 6, 3)) == "28 May – 3 Jun"


class TestViewModel:
    def test_cards(self, app_services: AppServices, populated: None) -> None:
        view = build_dashboard_view(app_services.dashboard.overview())

        assert [s.label for s in view.stats] == [
            "Available balance", "Income this month", "Expenses this month", "Saved this month"
        ]
        assert [s.value for s in view.stats] == [
            "26,200.00 MAD", "+12,000.00 MAD", "−7,420.00 MAD", "+4,580.00 MAD"
        ]
        # 8,000 is in an allocation that backs no goal.
        assert view.stats[0].caption == "34,200.00 MAD total − 8,000.00 MAD set aside"
        assert view.stats[3].caption == "38.2% of income"
        assert view.stats[2].caption == "vs 300.00 MAD in 1–15 May"
        assert view.subtitle == "Jun 2026 · month to date (1–15 Jun)"

    def test_balance_leaves_out_goal_money(self, app_services: AppServices, bank: Account) -> None:
        app_services.goals.create_with_new_allocation("Car", target="200000",
                                                      initial_amount="5000")
        app_services.goals.create_manual("Outside", target="1000", current="400")

        card = build_dashboard_view(app_services.dashboard.overview()).stats[0]

        # Only goal money inside the balance is subtracted; a manual goal's is not in it.
        assert (card.label, card.value) == ("Available balance", "24,920.00 MAD")
        assert card.caption == "29,920.00 MAD total − 5,000.00 MAD in goals"
        assert app_services.balances.total_balance() == Money.of("29920")  # real money unchanged

    def test_balance_with_nothing_set_aside(self, app_services: AppServices, bank: Account) -> None:
        card = build_dashboard_view(app_services.dashboard.overview()).stats[0]

        assert (card.label, card.value, card.tone) == ("Available balance", "29,920.00 MAD", "neutral")
        assert card.caption == "Nothing set aside · as of 15 Jun 2026"

    def test_overspent(self, app_services: AppServices, bank: Account,
                       categories: dict[str, Category]) -> None:
        app_services.transactions.create(TransactionDraft(
            bank.id, TransactionType.EXPENSE, "50", TODAY, categories["food"].id))

        net = build_dashboard_view(app_services.dashboard.overview()).stats[3]

        assert (net.label, net.value, net.tone) == ("Overspent this month", "−50.00 MAD", "outflow")
        assert net.caption == "No income recorded yet this month"

    def test_allocation_rows_and_notes(self, app_services: AppServices, populated: None) -> None:
        view = build_dashboard_view(app_services.dashboard.overview())

        assert [(r.name, r.amount, r.share) for r in view.allocation_rows] == [
            ("Savings", "8,000.00 MAD", "23.4%"),
            ("Available", "26,200.00 MAD", "76.6%"),
        ]
        assert view.allocation_rows[-1].is_available
        assert view.allocation_note is None

    def test_over_allocation_note(self, app_services: AppServices, bank: Account,
                                  categories: dict[str, Category]) -> None:
        app_services.allocations.create("Savings", initial_amount="29920")
        app_services.transactions.create(TransactionDraft(
            bank.id, TransactionType.EXPENSE, "20", TODAY, categories["food"].id))

        view = build_dashboard_view(app_services.dashboard.overview())

        assert view.allocation_note is not None and "Over-allocated by 20.00 MAD" in view.allocation_note
        assert view.allocation_rows[-1].is_negative
        assert view.allocation_rows[-1].bar_fraction == 0

    def test_health_rows(self, app_services: AppServices, populated: None) -> None:
        rows = build_dashboard_view(app_services.dashboard.overview()).health_rows

        assert [(r.label, r.value, r.level) for r in rows] == [
            ("Savings rate", "38.2%", HealthLevel.GOOD),
            ("Spending vs last month", "+2373.3%", HealthLevel.POOR),
            ("Emergency runway", "342.0 months", HealthLevel.GOOD),
            ("Allocated", "23.4%", None),
        ]
        assert rows[0].level_text == "✓ Good"


class TestCharts:
    def test_income_expense_bars_and_table(self, qapp: QApplication) -> None:
        chart = IncomeExpenseChart()
        flows = [MonthlyFlow(date(2026, 5, 1), Money.of("100"), Money.of("40")),
                 MonthlyFlow(date(2026, 6, 1), Money.of("0"), Money.of("5.5"))]

        chart.render(flows)

        assert chart.hover_texts == [
            "May 2026\nIncome: 100.00 MAD", "May 2026\nExpenses: 40.00 MAD",
            "Jun 2026\nIncome: 0.00 MAD", "Jun 2026\nExpenses: 5.50 MAD",
        ]
        headers, rows = income_expense_table(flows)
        assert headers == ["Month", "Income", "Expenses", "Net"]
        assert rows[0] == ["May 2026", "100.00 MAD", "40.00 MAD", "60.00 MAD"]

    def test_empty_messages(self, qapp: QApplication) -> None:
        for chart, data in ((IncomeExpenseChart(), [MonthlyFlow(JUNE_1, Money.zero(), Money.zero())]),
                            (BalanceHistoryChart(), []),
                            (CategorySpendingChart(), [])):
            chart.render(data)  # type: ignore[attr-defined]
            assert chart.hover_texts == []
            assert chart.axes.texts, "an explanatory message is drawn"

    def test_balance_hover_shows_nearest_day(self, qapp: QApplication) -> None:
        chart = BalanceHistoryChart()
        chart.resize(600, 240)
        points = [BalancePoint(date(2026, 6, d), Money.of(str(d * 100))) for d in range(1, 16)]
        chart.render(points)
        chart.draw()

        x, y = chart.axes.transData.transform((date2num(date(2026, 6, 7)) + 0.3, 500))
        event = MouseEvent("motion_notify_event", chart, x, y)

        assert chart.hover_text(event) == "07 Jun 2026\n700.00 MAD"

    def test_balance_table_lists_every_day_for_short_ranges(self) -> None:
        points = [BalancePoint(date(2026, 6, d), Money.of(str(d))) for d in range(1, 4)]

        _headers, rows = balance_history_table(points)

        assert rows == [["01 Jun 2026", "1.00 MAD"], ["02 Jun 2026", "2.00 MAD"],
                        ["03 Jun 2026", "3.00 MAD"]]

    def test_balance_table_lists_month_ends_for_long_ranges(self) -> None:
        start = date(2026, 5, 1)
        points = [BalancePoint(start + timedelta(days=i), Money.of(str(i))) for i in range(40)]

        _headers, rows = balance_history_table(points)

        assert rows == [["31 May 2026", "30.00 MAD"], ["09 Jun 2026", "39.00 MAD"]]

    def test_category_bars(self, qapp: QApplication) -> None:
        chart = CategorySpendingChart()
        chart.render([CategorySpending(1, "Rent", Money.of("4500"), Decimal("0.6064"))])

        assert chart.hover_texts == ["Rent\n4,500.00 MAD · 60.6%"]


class TestPage:
    def test_empty_state_without_accounts(self, page: DashboardPage) -> None:
        page.on_shown()

        assert not page.empty_state.isHidden()
        assert page.flows_card.isHidden() and page.stats_row.isHidden()

    def test_create_account_from_empty_state(
        self, page: DashboardPage, app_services: AppServices, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        page.on_shown()

        def submit(dialog: AccountDialog) -> int:
            dialog.name_edit.setText("Wallet")
            dialog.balance_edit.setText("500")
            return QDialog.DialogCode.Accepted if dialog.submit() else QDialog.DialogCode.Rejected

        monkeypatch.setattr(AccountDialog, "exec", submit)
        page.empty_state.action_button.click()

        assert page.empty_state.isHidden()
        assert page.stat_cards[0].value == "500.00 MAD"

    def test_populated(self, page: DashboardPage, populated: None) -> None:
        page.on_shown()

        assert [card.value for card in page.stat_cards] == [
            "26,200.00 MAD", "+12,000.00 MAD", "−7,420.00 MAD", "+4,580.00 MAD"
        ]
        assert page.header.subtitle_label.text() == "Jun 2026 · month to date (1–15 Jun)"
        assert [r.name for r in page.allocation_card.rows] == ["Savings", "Available"]
        assert page.recent_card.model.rowCount() == 4
        assert page.recent_card.model.row_at(0).description == "Groceries"
        assert len(page.flows_card.chart.hover_texts) == 12  # 6 months × 2 series
        assert len(page.spending_card.chart.hover_texts) == 2
        assert [r.label for r in page.health_card.rows][0] == "Savings rate"

    def test_net_worth_by_month(self, page: DashboardPage, app_services: AppServices,
                                populated: None) -> None:
        etf = app_services.investments.create("ETF", "etf")
        app_services.investments.set_value(etf.investment.id, "5000", date(2026, 5, 20))
        page.refresh()

        assert [p.month.month for p in page.net_worth] == [1, 2, 3, 4, 5, 6]
        chart = page.net_worth_card.chart
        chart.draw()
        x, y = chart.axes.transData.transform((4.2, 30000))
        assert chart.hover_text(MouseEvent("motion_notify_event", chart, x, y)) == (
            "May 2026 · 31 May 2026\nNet worth: 34,620.00 MAD\n"
            "Balance: 29,620.00 MAD\nInvestments: 5,000.00 MAD")
        page.net_worth_card.toggle_button.click()
        table = page.net_worth_card.table
        assert [table.item(5, c).text() for c in range(5)] == [
            "Jun 2026", "34,200.00 MAD", "5,000.00 MAD", "0.00 MAD", "39,200.00 MAD"]

    def test_table_toggle(self, page: DashboardPage, populated: None) -> None:
        page.on_shown()

        page.spending_card.toggle_button.click()

        assert page.spending_card.stack.currentWidget() is page.spending_card.table
        assert page.spending_card.table.item(0, 0).text() == "Rent"
        assert page.spending_card.toggle_button.text() == "Chart"

    def test_refresh_reflects_new_transactions(
        self, page: DashboardPage, app_services: AppServices, populated: None, bank: Account,
        categories: dict[str, Category],
    ) -> None:
        page.on_shown()
        app_services.transactions.create(TransactionDraft(
            bank.id, TransactionType.EXPENSE, "200", TODAY, categories["food"].id))

        page.on_shown()

        assert page.stat_cards[0].value == "26,000.00 MAD"  # 8,000 set aside
        assert page.stat_cards[2].value == "−7,620.00 MAD"

    def test_view_all_navigates(self, page: DashboardPage, populated: None) -> None:
        requested: list[str] = []
        page.navigate_requested.connect(requested.append)
        page.on_shown()

        page.recent_card.view_all_button.click()

        assert requested == [TRANSACTIONS_PAGE_KEY]


def test_main_window_opens_on_dashboard_and_view_all_switches_page(
    qapp: QApplication, app_config: AppConfig, app_services: AppServices, populated: None
) -> None:
    window = MainWindow(app_config, app_services)
    window.show()
    try:
        dashboard = window.page(DASHBOARD_PAGE_KEY)
        assert isinstance(dashboard, DashboardPage)
        assert dashboard.overview is not None  # loaded because it is the start page

        dashboard.navigate_requested.emit(TRANSACTIONS_PAGE_KEY)

        assert window.current_page.spec.key == TRANSACTIONS_PAGE_KEY
        assert window.sidebar.current_key() == TRANSACTIONS_PAGE_KEY
    finally:
        window.close()
        window.deleteLater()


def test_forecast_card(page: DashboardPage, app_services: AppServices, populated: None) -> None:
    rent = app_services.categories.create("Car", CategoryKind.EXPENSE)
    bank = app_services.accounts.list()[0]
    app_services.recurring.create("Car loan", type="expense", amount="40000",
                                  account_id=bank.id, category_id=rent.id,
                                  frequency="monthly", first_date=date(2026, 7, 5))
    page.refresh()
    assert page.forecast is not None
    assert "Money gets tight around 05 Jul 2026" in page.forecast_note.text()
    assert page.forecast_note.property("tone") == "warning"
    page.forecast_card.toggle_button.click()
    table = page.forecast_card.table
    assert [table.item(0, c).text() for c in range(3)] == ["05 Jul 2026", "Car loan",
                                                           "−40,000.00 MAD"]
