"""Dashboard page.

One ``DashboardService.overview()`` call per refresh feeds every widget; the
page refreshes only when it is shown, so hidden pages cost no queries.
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QGridLayout, QScrollArea, QVBoxLayout, QWidget

from money_manager.core.errors import MoneyManagerError
from money_manager.domain.dashboard import DashboardOverview
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.accounts.account_dialog import AccountDialog
from money_manager.ui.components import AdaptiveRow, EmptyState, ResponsiveRow, StatCard
from money_manager.ui.charts.base import ChartCard
from money_manager.ui.charts.money import (
    BalanceHistoryChart,
    CategorySpendingChart,
    IncomeExpenseChart,
    balance_history_table,
    category_spending_table,
    income_expense_table,
)
from money_manager.ui.dashboard.view_model import (
    DashboardView,
    RenewalView,
    build_dashboard_view,
    renewal_views,
)
from money_manager.ui.dashboard.widgets import (
    AllocationOverview,
    GoalsOverview,
    HealthCard,
    RecentTransactions,
    RenewingSoon,
)
from money_manager.ui.goals.view_model import goal_card_view
from money_manager.ui.pages.base_page import BasePage
from money_manager.ui.pages.registry import (
    GOALS_PAGE_KEY,
    SUBSCRIPTIONS_PAGE_KEY,
    TRANSACTIONS_PAGE_KEY,
    PageSpec,
)
from money_manager.ui.theme import SIDE_BY_SIDE_MIN_WIDTH, Spacing
from money_manager.ui.transactions.rows import TransferSide, build_rows, transfer_sides

logger = logging.getLogger(__name__)


class DashboardPage(BasePage):
    def __init__(self, spec: PageSpec, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(spec, parent, fill=True)
        self._services = services
        self.overview: DashboardOverview | None = None
        self.view: DashboardView | None = None
        self.renewals: tuple[RenewalView, ...] = ()
        self.transfer_labels: dict[int, TransferSide] = {}

        self.stat_cards = tuple(StatCard("") for _ in range(4))
        self.flows_card = ChartCard(
            "Income vs expenses", "Last 6 months · adjustments excluded", IncomeExpenseChart()
        )
        self.allocation_card = AllocationOverview()
        self.balance_card = ChartCard(
            "Balance history", "Total balance at the end of each day", BalanceHistoryChart()
        )
        self.spending_card = ChartCard(
            "Spending by category", "This month · top 5, the rest grouped as Other",
            CategorySpendingChart(),
        )
        self.recent_card = RecentTransactions()
        self.recent_card.view_all_requested.connect(
            lambda: self.navigate_requested.emit(TRANSACTIONS_PAGE_KEY)
        )
        self.health_card = HealthCard()
        self.goals_card = GoalsOverview()
        self.goals_card.view_all_requested.connect(
            lambda: self.navigate_requested.emit(GOALS_PAGE_KEY)
        )
        self.renewing_card = RenewingSoon()
        self.renewing_card.view_all_requested.connect(
            lambda: self.navigate_requested.emit(SUBSCRIPTIONS_PAGE_KEY)
        )

        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.MD)
        grid.setVerticalSpacing(Spacing.MD)
        self.stats_row = ResponsiveRow(self.stat_cards, min_item_width=210)
        grid.addWidget(self.stats_row, 0, 0, 1, 12)  # 12-column grid
        self.pair_rows = [
            AdaptiveRow([(left, 7), (right, 5)], SIDE_BY_SIDE_MIN_WIDTH)
            for left, right in ((self.flows_card, self.allocation_card),
                                (self.balance_card, self.spending_card),
                                (self.recent_card, self.health_card),
                                (self.goals_card, self.renewing_card))
        ]
        for row, pair in enumerate(self.pair_rows, start=1):
            grid.addWidget(pair, row, 0, 1, 12)
        for column in range(12):
            grid.setColumnStretch(column, 1)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, Spacing.SM, 0)  # room for the scrollbar
        content_layout.addLayout(grid)
        content_layout.addStretch(1)

        self.empty_state = EmptyState(
            "Create an account to get started",
            "The dashboard summarises your real balance, income, spending and allocations. "
            "Add the account you want to track first.",
            badge=None,
            action_text="Create account",
        )
        self.empty_state.action_clicked.connect(self.create_account)
        content_layout.insertWidget(0, self.empty_state)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.content)
        scroll.viewport().setAutoFillBackground(False)
        self.content.setObjectName("TransparentArea")
        self.add_content(scroll, stretch=1)
        self._grid_widgets = [self.stats_row, self.flows_card, self.allocation_card,
                              self.balance_card, self.spending_card, self.recent_card,
                              self.health_card, self.goals_card, self.renewing_card]

    def on_shown(self) -> None:
        # Nothing changed since the page was last shown: keep what is on screen.
        if self.already_current(self._services.freshness()):
            return
        self.refresh()

    def refresh(self) -> None:
        try:
            overview = self._services.dashboard.overview()
            self.renewals = renewal_views(self._services.subscriptions.upcoming())
            names = {account.id: account.name for account in self._services.accounts.list()}
            self.transfer_labels = transfer_sides(
                self._services.account_transfers.by_transaction(), names)
        except MoneyManagerError as exc:
            logger.warning("Could not load the dashboard: %s", exc)
            dialogs.show_warning(self, "Could not load the dashboard", str(exc))
            return
        self.overview = overview
        self.view = build_dashboard_view(overview)
        self._render(overview, self.view)

    def create_account(self) -> None:
        dialog = AccountDialog(self._services, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _render(self, overview: DashboardOverview, view: DashboardView) -> None:
        self.header.subtitle_label.setText(view.subtitle)
        self.empty_state.setVisible(not overview.has_accounts)
        for widget in self._grid_widgets:
            widget.setVisible(overview.has_accounts)
        if not overview.has_accounts:
            return

        for card, stat in zip(self.stat_cards, view.stats, strict=True):
            card.label.setText(stat.label)
            card.set_value(stat.value, stat.tone)
            card.set_caption(stat.caption)

        self.flows_card.chart.render(overview.monthly_flows)
        self.flows_card.set_table(income_expense_table(overview.monthly_flows))
        self.balance_card.chart.render(overview.balance_history)
        self.balance_card.set_table(balance_history_table(overview.balance_history))
        self.spending_card.chart.render(overview.spending_by_category)
        self.spending_card.set_table(category_spending_table(overview.spending_by_category))

        self.allocation_card.set_rows(view.allocation_rows, view.allocation_note)
        self.health_card.set_rows(view.health_rows)
        self.goals_card.set_goals([goal_card_view(goal) for goal in overview.goals])
        self.renewing_card.set_rows(self.renewals)
        self.recent_card.set_rows(
            build_rows(overview.recent_transactions, overview.category_names,
                       overview.allocation_names, self.transfer_labels)
        )
