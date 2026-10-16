"""Statistics page.

One ``StatisticsService.report()`` and one ``FinancialAnalysisService.analyze()``
call per refresh (page shown with changed data, or range changed) feed every
card, chart and table. They run on a worker thread so the window stays
responsive with large histories; the previous figures stay visible, marked
"Updating…", until the new ones arrive, and a newer request supersedes an
older one. The range selector sits above everything it scopes.
"""

import logging
from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError, ValidationError
from money_manager.domain.dashboard import MonthlyFlow
from money_manager.domain.financial_analysis import FinancialAnalysis
from money_manager.domain.periods import DateRange, StatsRange
from money_manager.domain.statistics import StatisticsReport
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.accounts.account_dialog import AccountDialog
from money_manager.ui.ai.background import BackgroundCall, run_in_background
from money_manager.ui.charts.analysis import (
    CategoryChangeChart,
    CategoryShareChart,
    SpendingTrendChart,
    category_change_table,
    category_share_table,
    spending_trend_table,
)
from money_manager.ui.charts.base import ChartCard
from money_manager.ui.charts.money import (
    BalanceHistoryChart,
    IncomeExpenseChart,
    balance_history_table,
    income_expense_table,
)
from money_manager.ui.components import AdaptiveRow, EmptyState, ResponsiveRow, StatCard
from money_manager.ui.components.data_table_card import DataTableCard
from money_manager.ui.components.facts_card import FactsCard
from money_manager.ui.pages.base_page import BasePage
from money_manager.ui.pages.registry import PageSpec
from money_manager.ui.statistics.investment_dialog import InvestmentCategoriesDialog
from money_manager.ui.statistics.range_bar import RangeBar
from money_manager.ui.statistics.view_model import (
    MONTH_HEADERS,
    RECURRING_HEADERS,
    StatisticsView,
    build_statistics_view,
)
from money_manager.ui.theme import SIDE_BY_SIDE_MIN_WIDTH, Spacing

logger = logging.getLogger(__name__)


class StatisticsPage(BasePage):
    def __init__(self, spec: PageSpec, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(spec, parent, fill=True)
        self._services = services
        self.report: StatisticsReport | None = None
        self.analysis: FinancialAnalysis | None = None
        self.view: StatisticsView | None = None
        self._generation = 0  # the latest requested refresh; older results are dropped
        self._calls: list[BackgroundCall] = []

        # Filter row (scopes everything below)
        self.range_bar = RangeBar(services.today)
        self.range_bar.changed.connect(self.refresh)
        self.investments_button = QPushButton("Investment categories…")
        self.investments_button.clicked.connect(self.edit_investment_categories)
        self.range_error = QLabel()
        self.range_error.setObjectName("FieldError")
        self.range_error.hide()
        filter_row = QWidget()
        filter_layout = QHBoxLayout(filter_row)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.addWidget(self.range_bar, 1)
        filter_layout.addWidget(self.investments_button)

        self.period_label = QLabel()
        self.period_label.setObjectName("MutedLabel")
        self.loading_label = QLabel("Updating…")
        self.loading_label.setObjectName("MutedLabel")
        self.loading_label.hide()
        period_row = QWidget()
        period_layout = QHBoxLayout(period_row)
        period_layout.setContentsMargins(0, 0, 0, 0)
        period_layout.addWidget(self.period_label)
        period_layout.addWidget(self.loading_label)
        period_layout.addStretch(1)

        # Cards
        self.stat_cards = tuple(StatCard("", compact=True) for _ in range(5))
        self.balance_card = ChartCard("Balance trend", "", BalanceHistoryChart())
        self.share_card = ChartCard(
            "Spending by category", "Investments excluded · top 5, the rest as Other",
            CategoryShareChart(),
        )
        self.flows_card = ChartCard(
            "Income vs expenses", "Calendar months in the range", IncomeExpenseChart()
        )
        self.trend_card = ChartCard("Spending trend", "", SpendingTrendChart())
        self.changes_card = ChartCard("Category changes", "", CategoryChangeChart(height_px=300))
        self.months_card = DataTableCard(
            "Monthly comparison",
            "Spending change compares with the previous month (the current month with the "
            "same days of last month).",
        )
        self.recurring_card = DataTableCard("Recurring spending")
        self.facts_card = FactsCard(
            "Key facts",
            "Measured from your own data by fixed rules — no AI, no judgements.",
        )

        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.MD)
        grid.setVerticalSpacing(Spacing.MD)
        stats_row = ResponsiveRow(self.stat_cards, min_item_width=170)
        grid.addWidget(stats_row, 0, 0, 1, 12)
        grid.addWidget(self.facts_card, 1, 0, 1, 12)
        for row, (left, right) in enumerate(((self.balance_card, self.share_card),
                                             (self.flows_card, self.trend_card)), start=2):
            grid.addWidget(AdaptiveRow([(left, 7), (right, 5)], SIDE_BY_SIDE_MIN_WIDTH), row, 0, 1, 12)
        grid.addWidget(self.changes_card, 4, 0, 1, 12)
        grid.addWidget(self.months_card, 5, 0, 1, 12)
        grid.addWidget(self.recurring_card, 6, 0, 1, 12)
        for column in range(12):
            grid.setColumnStretch(column, 1)

        self.empty_state = EmptyState(
            "Create an account to get started",
            "Statistics are calculated from your recorded transactions. Add the account "
            "you want to track first.",
            badge=None,
            action_text="Create account",
        )
        self.empty_state.action_clicked.connect(self.create_account)

        self.content = QWidget()
        self.content.setObjectName("TransparentArea")
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, Spacing.SM, 0)
        content_layout.addWidget(self.empty_state)
        content_layout.addLayout(grid)
        content_layout.addStretch(1)
        self._grid_widgets = [stats_row, self.facts_card, self.balance_card, self.share_card,
                              self.flows_card,
                              self.trend_card, self.changes_card, self.months_card,
                              self.recurring_card]

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.content)

        self.add_content(filter_row)
        self.add_content(self.range_error)
        self.add_content(period_row)
        self.add_content(scroll, stretch=1)

    # ------------------------------------------------------------ public API

    def on_shown(self) -> None:
        # Nothing changed since the page was last shown: keep what is on screen.
        if self.already_current(self._services.freshness()):
            return
        self.refresh()

    def selected_range(self) -> DateRange:
        preset = self.range_bar.preset
        if preset is StatsRange.CUSTOM:
            return self._services.statistics.custom_range(*self.range_bar.custom_dates())
        return self._services.statistics.range_for(preset)

    @property
    def loading(self) -> bool:
        return any(call.running for call in self._calls)

    def refresh(self) -> None:
        """Recalculate for the selected range on a worker thread."""
        try:
            period = self.selected_range()
        except ValidationError as exc:
            self._show_range_error(str(exc))
            return
        self._generation += 1
        statistics, analysis = self._services.statistics, self._services.analysis
        call = run_in_background(
            lambda: (statistics.report(period), analysis.analyze(period)),
            partial(self._loaded, self._generation), partial(self._failed, self._generation),
            owner=self)
        self._calls = [c for c in self._calls if c.running] + [call]
        self._set_loading(True)

    def _loaded(self, generation: int,
                result: tuple[StatisticsReport, FinancialAnalysis]) -> None:
        if generation != self._generation:
            return  # a newer range was chosen meanwhile
        self._set_loading(False)
        report, analysis = result
        self.range_error.hide()
        self.report = report
        self.view = build_statistics_view(report)
        self.analysis = analysis
        self.facts_card.set_facts([fact.text for fact in analysis.facts])
        self._render(report, self.view)

    def _failed(self, generation: int, exc: BaseException) -> None:
        if generation != self._generation:
            return
        self._set_loading(False)
        if isinstance(exc, ValidationError):
            self._show_range_error(str(exc))
        elif isinstance(exc, MoneyManagerError):
            logger.warning("Could not compute statistics: %s", exc)
            dialogs.show_warning(self, "Could not compute statistics", str(exc))
        else:
            logger.error("Statistics failed unexpectedly", exc_info=exc)
            dialogs.show_warning(self, "Could not compute statistics",
                                 dialogs.UNEXPECTED_ERROR_MESSAGE)

    def _show_range_error(self, message: str) -> None:
        self.range_error.setText(message)
        self.range_error.show()

    def _set_loading(self, loading: bool) -> None:
        self.loading_label.setVisible(loading)
        if loading:
            self.setCursor(Qt.CursorShape.BusyCursor)
        else:
            self.unsetCursor()

    def edit_investment_categories(self) -> None:
        dialog = InvestmentCategoriesDialog(self._services, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def create_account(self) -> None:
        dialog = AccountDialog(self._services, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    # --------------------------------------------------------------- render

    def _render(self, report: StatisticsReport, view: StatisticsView) -> None:
        self.empty_state.setVisible(not report.has_accounts)
        for widget in self._grid_widgets:
            widget.setVisible(report.has_accounts)
        self.period_label.setText(f"{view.period_label} · {view.comparison_label}")
        if not report.has_accounts:
            return

        for card, stat in zip(self.stat_cards, view.stats, strict=True):
            card.label.setText(stat.label)
            card.set_value(stat.value, stat.tone)
            card.set_caption(stat.caption)

        self.balance_card.subtitle_label.setText(view.balance_caption)
        self.balance_card.chart.render(report.balance.points)
        self.balance_card.set_table(balance_history_table(report.balance.points))

        self.share_card.chart.render(report.spending_by_category, list(report.category_names))
        self.share_card.set_table(category_share_table(report.spending_by_category))

        flows = [MonthlyFlow(m.month, m.totals.income, m.totals.expenses) for m in report.months]
        partial = bool(report.months) and report.months[-1].is_partial
        self.flows_card.chart.render(flows, last_is_partial=partial)
        self.flows_card.set_table(income_expense_table(flows))

        self.trend_card.subtitle_label.setText(view.trend_caption)
        self.trend_card.chart.render(report.trend)
        self.trend_card.set_table(spending_trend_table(report.trend))

        self.changes_card.subtitle_label.setText(
            f"Spending per category, this period vs the previous one · {view.comparison_label}"
        )
        self.changes_card.chart.render(report.category_changes)
        self.changes_card.set_table(category_change_table(report.category_changes))

        self.months_card.set_rows(MONTH_HEADERS, view.month_rows)
        self.recurring_card.subtitle_label.setText(view.recurring_caption)
        self.recurring_card.set_rows(RECURRING_HEADERS, view.recurring_rows, text_columns=3)
