from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

import pytest
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from money_manager.domain.analytics import (
    CategoryAmount,
    CategoryChange,
    Granularity,
    SpendingTrend,
    TrendBucket,
    TrendDirection,
)
from money_manager.domain.entities import Account, Category, TransactionDraft
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import Money
from money_manager.domain.periods import DateRange, StatsRange
from money_manager.services import AppServices
from money_manager.ui.charts.analysis import (
    MAX_TREND_TICKS,
    CategoryChangeChart,
    CategoryShareChart,
    SpendingTrendChart,
    category_colours,
    category_change_table,
    change_label,
    fold_categories,
)
from money_manager.ui.charts.base import CATEGORICAL, OTHER_COLOR
from money_manager.ui.components import ResponsiveRow
from money_manager.ui.pages import PAGES, STATISTICS_PAGE_KEY
from money_manager.ui.statistics.investment_dialog import InvestmentCategoriesDialog
from money_manager.ui.statistics.range_bar import DEFAULT_RANGE, RangeBar
from money_manager.ui.statistics.statistics_page import StatisticsPage
from money_manager.ui.statistics.view_model import build_statistics_view
from tests.services.support import TODAY, fixed_today
from tests.ui.support import wait_until

SPEC = next(spec for spec in PAGES if spec.key == STATISTICS_PAGE_KEY)


def m(value: str) -> Money:
    return Money.of(value)


@pytest.fixture
def bank(app_services: AppServices) -> Account:
    return app_services.accounts.create("Bank", opening_balance="10000", opening_date=date(2026, 1, 1))


@pytest.fixture
def cats(app_services: AppServices) -> dict[str, Category]:
    return {
        "salary": app_services.categories.create("Salary", CategoryKind.INCOME),
        "food": app_services.categories.create("Food", CategoryKind.EXPENSE),
        "stocks": app_services.categories.create("Stocks", CategoryKind.EXPENSE),
    }


@pytest.fixture
def populated(app_services: AppServices, bank: Account, cats: dict[str, Category]) -> None:
    def add(type_: TransactionType, amount: str, name: str, on: date, text: str = "") -> None:
        app_services.transactions.create(
            TransactionDraft(bank.id, type_, amount, on, cats[name].id, description=text))

    add(TransactionType.INCOME, "10000", "salary", date(2026, 6, 1))
    add(TransactionType.EXPENSE, "1830", "food", date(2026, 6, 5))
    add(TransactionType.EXPENSE, "2000", "stocks", date(2026, 6, 6))
    add(TransactionType.EXPENSE, "1500", "food", date(2026, 5, 5))
    for month in (3, 4, 5, 6):
        add(TransactionType.EXPENSE, "65", "food", date(2026, month, 3), "Netflix")


@pytest.fixture
def page(qapp: QApplication, app_services: AppServices) -> Iterator[StatisticsPage]:
    widget = StatisticsPage(SPEC, app_services)
    widget.resize(1280, 900)
    widget.show()
    yield widget
    wait_until(lambda: not widget.loading)
    widget.close()
    widget.deleteLater()


def settle(page: StatisticsPage) -> None:
    """Wait for the background calculation to be rendered."""
    wait_until(lambda: not page.loading)


class TestViewModel:
    def test_cards_without_investment_categories(
        self, app_services: AppServices, populated: None
    ) -> None:
        report = app_services.statistics.report(DateRange(date(2026, 6, 1), TODAY))

        view = build_statistics_view(report)

        assert [s.label for s in view.stats] == ["Income", "Expenses", "Saved", "Invested",
                                                  "Net change"]
        assert view.stats[0].value == "+10,000.00 MAD"
        assert view.stats[1].value == "−3,895.00 MAD"
        assert view.stats[3].caption == "Mark investment categories to track this"
        assert view.period_label == "01 Jun 2026 – 15 Jun 2026 (15 days)"
        assert view.comparison_label == "Changes compare with 17 May 2026 – 31 May 2026"

    def test_cards_with_investments(
        self, app_services: AppServices, populated: None, cats: dict[str, Category]
    ) -> None:
        app_services.categories.set_investment(cats["stocks"].id, True)

        view = build_statistics_view(
            app_services.statistics.report(DateRange(date(2026, 6, 1), TODAY)))

        saved, invested = view.stats[2], view.stats[3]
        assert (saved.value, saved.caption) == ("+8,105.00 MAD", "Savings rate 81.1%")
        assert (invested.value, invested.caption) == (
            "2,000.00 MAD", "Investment rate 20.0% of income"
        )

    def test_month_rows_and_recurring(self, app_services: AppServices, populated: None) -> None:
        view = build_statistics_view(
            app_services.statistics.report(DateRange(date(2026, 5, 1), TODAY)))

        may, june = view.month_rows
        assert may[0] == "May 2026" and june[0] == "Jun 2026 (to date)"
        assert june[2] == "3,895.00 MAD"
        [netflix] = view.recurring_rows
        assert netflix[:3] == ("Netflix", "Food", "Month")
        assert "65.00 MAD per month in 1 recurring expense" in view.recurring_caption

    def test_overspent_and_empty(self, app_services: AppServices, bank: Account,
                                 cats: dict[str, Category]) -> None:
        app_services.transactions.create(TransactionDraft(
            bank.id, TransactionType.EXPENSE, "5", TODAY, cats["food"].id))

        view = build_statistics_view(app_services.statistics.report(
            app_services.statistics.range_for(StatsRange.DAYS_7)))

        assert (view.stats[2].label, view.stats[2].caption) == (
            "Overspent", "No income in this period"
        )
        assert view.stats[0].caption == "Nothing to compare with in the previous period"
        assert "No regular weekly or monthly expenses" in view.recurring_caption

    def test_previous_period_before_tracking(self, app_services: AppServices,
                                             populated: None) -> None:
        # The bank opened on 1 January: the 6 months before are not tracked.
        view = build_statistics_view(
            app_services.statistics.report(DateRange(date(2026, 1, 1), TODAY)))

        assert view.comparison_label.startswith("No comparison:")
        assert view.stats[1].caption == "Previous period is before tracking began"


class TestCharts:
    ROWS = [CategoryAmount(i, f"C{i}", m(str(100 - i)), None) for i in range(1, 8)]

    def test_donut_folds_the_tail_into_other(self) -> None:
        folded = fold_categories(self.ROWS)

        assert [r.name for r in folded] == ["C1", "C2", "C3", "C4", "C5", "Other"]
        assert folded[-1].amount == m("187") and folded[-1].category_id is None

    def test_colours_follow_the_category_across_ranges(self) -> None:
        all_ids = [1, 2, 3, 4, 5, 6, 7]
        wide = category_colours(fold_categories(self.ROWS), all_ids)
        narrow = category_colours([self.ROWS[2], self.ROWS[0]], all_ids)

        assert wide[-1] == OTHER_COLOR
        assert narrow == [wide[2], wide[0]]  # C3 and C1 keep their colours
        assert len(set(wide[:-1])) == 5 and set(wide[:-1]) <= set(CATEGORICAL)

    def test_colour_clash_takes_the_next_free_slot(self) -> None:
        # Positions 0 and 5 among all categories both map to slot 0.
        rows = [CategoryAmount(1, "A", m("2"), None), CategoryAmount(6, "F", m("1"), None)]

        first, second = category_colours(rows, [1, 2, 3, 4, 5, 6])

        assert first == CATEGORICAL[0] and second != first

    def test_donut_hover(self, qapp: QApplication) -> None:
        chart = CategoryShareChart()
        chart.render([CategoryAmount(1, "Food", m("30"), Decimal("0.75")),
                      CategoryAmount(2, "Rent", m("10"), Decimal("0.25"))], [1, 2])

        assert chart.hover_texts == ["Food\n30.00 MAD · 75.0%", "Rent\n10.00 MAD · 25.0%"]

    def test_change_labels_and_table(self) -> None:
        grew = CategoryChange(1, "Food", m("1500"), m("1830"))
        new = CategoryChange(2, "Travel", m("0"), m("2200"))
        gone = CategoryChange(3, "Gym", m("300"), m("0"))

        assert [change_label(c) for c in (grew, new, gone)] == ["+22.0%", "new", "−100.0%"]
        _headers, rows = category_change_table([grew])
        assert rows == [["Food", "1,500.00 MAD", "1,830.00 MAD", "+330.00 MAD", "+22.0%"]]

    def test_dumbbell_hover(self, qapp: QApplication) -> None:
        chart = CategoryChangeChart()
        chart.render([CategoryChange(1, "Food", m("1500"), m("1830"))])

        assert chart.hover_texts == [
            "Food\nPrevious: 1,500.00 MAD", "Food\nThis period: 1,830.00 MAD\n+22.0%"
        ]

    def test_trend_ticks_are_limited(self, qapp: QApplication) -> None:
        start = date(2026, 1, 1)
        buckets = tuple(
            TrendBucket(DateRange(start + timedelta(days=i), start + timedelta(days=i)), m("1"))
            for i in range(31)
        )
        chart = SpendingTrendChart()
        chart.render(SpendingTrend(Granularity.DAY, buckets, m("1"), None, TrendDirection.STABLE))

        assert len(chart.axes.get_xticks()) <= MAX_TREND_TICKS
        assert len(chart.hover_texts) == 31


class TestRangeBar:
    def test_default_and_custom(self, qapp: QApplication) -> None:
        bar = RangeBar(fixed_today)
        changes: list[None] = []
        bar.changed.connect(lambda: changes.append(None))

        assert bar.preset is DEFAULT_RANGE and bar.start_edit.isHidden()
        bar.buttons[StatsRange.CUSTOM].click()

        assert bar.preset is StatsRange.CUSTOM and not bar.start_edit.isHidden()
        assert bar.end_edit.maximumDate().toPython() == TODAY
        assert changes


class TestResponsiveRow:
    def test_wraps_to_fit(self, qapp: QApplication) -> None:
        widgets = [QWidget() for _ in range(5)]
        row = ResponsiveRow(widgets, min_item_width=170)

        assert row.columns_for(1000) == 5
        assert row.columns_for(700) == 3
        assert row.columns_for(100) == 1
        row.resizeEvent(QResizeEvent(QSize(700, 100), QSize(1000, 100)))
        assert row.columns == 3


class TestPage:
    def test_empty_state(self, page: StatisticsPage) -> None:
        page.on_shown()
        settle(page)

        assert not page.empty_state.isHidden()
        assert page.balance_card.isHidden()

    def test_populated_and_range_switch(self, page: StatisticsPage, populated: None) -> None:
        page.on_shown()
        settle(page)
        assert page.report is not None and page.report.period.days == 30

        page.range_bar.buttons[StatsRange.MONTHS_3].click()
        settle(page)

        assert page.report.period == DateRange(date(2026, 3, 16), TODAY)
        assert page.period_label.text().startswith("16 Mar 2026 – 15 Jun 2026 (92 days)")
        assert page.stat_cards[0].value == "+10,000.00 MAD"
        assert page.months_card.cell(0, 0) == "Mar 2026"
        assert page.recurring_card.cell(0, 0) == "Netflix"
        assert page.share_card.chart.hover_texts  # donut drawn

    def test_invalid_custom_range_shows_message(self, page: StatisticsPage, populated: None) -> None:
        page.on_shown()
        settle(page)
        page.range_bar.buttons[StatsRange.CUSTOM].click()

        page.range_bar.start_edit.setDate(page.range_bar.start_edit.date().addYears(-20))

        assert not page.range_error.isHidden()
        assert "ten years" in page.range_error.text()

    def test_investment_categories_dialog(
        self, page: StatisticsPage, app_services: AppServices, populated: None,
        cats: dict[str, Category], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        page.on_shown()
        settle(page)

        def tick_stocks(dialog: InvestmentCategoriesDialog) -> int:
            names = [dialog.list.item(i).text() for i in range(dialog.list.count())]
            assert names == ["Food", "Stocks"]  # expense categories only
            dialog.set_checked(cats["stocks"].id, True)
            return QDialog.DialogCode.Accepted if dialog.submit() else QDialog.DialogCode.Rejected

        monkeypatch.setattr(InvestmentCategoriesDialog, "exec", tick_stocks)
        page.investments_button.click()
        settle(page)

        assert app_services.categories.get(cats["stocks"].id).is_investment
        assert page.stat_cards[3].value == "2,000.00 MAD"
        assert "Investment rate 20.0%" in page.stat_cards[3].caption_label.text()

    def test_key_facts(self, page: StatisticsPage, populated: None) -> None:
        page.on_shown()
        settle(page)

        facts = page.facts_card.facts
        assert page.analysis is not None and facts == tuple(f.text for f in page.analysis.facts)
        assert any(text.startswith("Balance on 2026-06-15") for text in facts)
        page.range_bar.buttons[StatsRange.MONTHS_3].click()
        settle(page)
        assert page.analysis.period == page.report.period  # same range as the page

    def test_table_views(self, page: StatisticsPage, populated: None) -> None:
        page.on_shown()
        settle(page)

        page.changes_card.toggle_button.click()

        assert page.changes_card.stack.currentWidget() is page.changes_card.table
        # Stocks is not marked as investing here, so it is new spending: the biggest mover.
        assert page.changes_card.table.item(0, 0).text() == "Stocks"
        assert page.changes_card.table.item(0, 4).text() == "new"
        assert page.changes_card.table.item(1, 0).text() == "Food"


def test_unchecking_saves_too(qapp: QApplication, app_services: AppServices,
                              cats: dict[str, Category]) -> None:
    app_services.categories.set_investment(cats["stocks"].id, True)
    dialog = InvestmentCategoriesDialog(app_services)

    dialog.set_checked(cats["stocks"].id, False)
    assert dialog.submit()

    assert not app_services.categories.get(cats["stocks"].id).is_investment
    assert dialog.list.item(1).checkState() == Qt.CheckState.Unchecked


def test_page_stays_responsive_and_shows_the_latest_range(
    page: StatisticsPage, populated: None,
) -> None:
    page.on_shown()
    assert page.loading and page.loading_label.isVisible()  # calculating in the background
    page.range_bar.buttons[StatsRange.MONTHS_3].click()  # supersedes the first request
    settle(page)
    assert not page.loading_label.isVisible()
    assert page.report is not None and page.report.period.days == 92


def test_background_failures_are_reported(page: StatisticsPage, populated: None,
                                          app_services: AppServices,
                                          monkeypatch: pytest.MonkeyPatch) -> None:
    from money_manager.core.errors import DatabaseError
    from money_manager.ui import dialogs

    shown: list[str] = []
    monkeypatch.setattr(dialogs, "show_warning", lambda parent, title, msg: shown.append(msg))

    def broken(period: object) -> None:
        raise DatabaseError("A database operation failed; no changes were saved.")

    monkeypatch.setattr(app_services.statistics, "report", broken)
    page.refresh()
    settle(page)
    assert shown == ["A database operation failed; no changes were saved."]
    assert not page.loading_label.isVisible()

