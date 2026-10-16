"""Subscriptions page: totals, upcoming payments, the subscription list and cost breakdown.

All figures come from ``SubscriptionService.statistics()`` (one call per
refresh). Payments are only recorded when the user confirms them here.
"""

import logging
from collections.abc import Callable
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError
from money_manager.domain.subscriptions import Subscription, SubscriptionStats
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.charts.base import ChartCard
from money_manager.ui.charts.money import CategorySpendingChart, category_spending_table
from money_manager.ui.components import AdaptiveRow, Card, EmptyState, ResponsiveRow, StatCard
from money_manager.ui.pages.base_page import BasePage
from money_manager.ui.pages.registry import PageSpec
from money_manager.ui.subscriptions.payment_dialog import RecordPaymentDialog
from money_manager.ui.subscriptions.subscription_dialog import SubscriptionDialog
from money_manager.ui.subscriptions.view_model import (
    TABLE_HEADERS,
    UpcomingRowView,
    category_cost_rows,
    subscription_row,
    summary_stats,
    upcoming_row,
)
from money_manager.ui.theme import SIDE_BY_SIDE_MIN_WIDTH, Spacing

logger = logging.getLogger(__name__)

MAX_UPCOMING_ROWS = 12
SKIP = "skip"
AMOUNT_COLUMNS = (2, 4)


def _alignment(column: int) -> Qt.AlignmentFlag:
    side = Qt.AlignmentFlag.AlignRight if column in AMOUNT_COLUMNS else Qt.AlignmentFlag.AlignLeft
    return side | Qt.AlignmentFlag.AlignVCenter


class UpcomingPaymentsCard(Card):
    """Due and overdue payments, each with Record / Skip when it is next in line."""

    def __init__(self, page: "SubscriptionsPage") -> None:
        super().__init__("Upcoming payments")
        self._page = page
        self.subtitle = QLabel("Confirm each payment when it happens: Record creates the "
                               "expense, Skip moves on without one.")
        self.subtitle.setObjectName("MutedLabel")
        self.subtitle.setWordWrap(True)
        self.body.addWidget(self.subtitle)
        self._grid = QGridLayout()
        self._grid.setHorizontalSpacing(Spacing.MD)
        self._grid.setVerticalSpacing(Spacing.XS)
        self._grid.setColumnStretch(1, 1)
        self.body.addLayout(self._grid)
        self.empty_label = QLabel("Nothing due in this period.")
        self.empty_label.setObjectName("MutedLabel")
        self.body.addWidget(self.empty_label)
        self.body.addStretch(1)
        self.rows: list[UpcomingRowView] = []
        self.record_buttons: list[QPushButton] = []
        self.skip_buttons: list[QPushButton] = []

    def set_rows(self, rows: list[UpcomingRowView]) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self.rows = rows[:MAX_UPCOMING_ROWS]
        self.record_buttons, self.skip_buttons = [], []
        for index, row in enumerate(self.rows):
            when = QLabel(row.when)
            when.setObjectName("FieldError" if row.is_overdue else "MutedLabel")
            when.setWordWrap(True)  # narrow windows: the date text wraps instead of clipping
            name = QLabel(row.name)
            name.setObjectName("AllocationName")
            name.setWordWrap(True)
            amount = QLabel(row.amount)
            amount.setObjectName("AllocationAmount")
            amount.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            record = QPushButton("Record")
            skip = QPushButton("Skip")
            for button in (record, skip):
                button.setEnabled(row.can_be_confirmed)
                if not row.can_be_confirmed:
                    button.setToolTip("Confirm the earlier payment of this subscription first.")
            record.clicked.connect(lambda _c=False, r=row: self._page.record_payment(
                r.subscription_id, r.due_date))
            skip.clicked.connect(lambda _c=False, r=row: self._page.skip_payment(
                r.subscription_id, r.due_date))
            self.record_buttons.append(record)
            self.skip_buttons.append(skip)
            for column, widget in enumerate((when, name, amount, record, skip)):
                self._grid.addWidget(widget, index, column)
        self.empty_label.setVisible(not self.rows)


class SubscriptionsPage(BasePage):
    def __init__(self, spec: PageSpec, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(spec, parent, fill=True)
        self._services = services
        self.stats: SubscriptionStats | None = None
        self._subscriptions: list[Subscription] = []

        self.new_button = QPushButton("New subscription")
        self.new_button.setObjectName("PrimaryButton")
        self.new_button.clicked.connect(self.create_subscription)
        self.new_button.setToolTip("New subscription (Ctrl+N)")
        self.header.add_action(self.new_button)
        self.primary_button = self.new_button

        self.stat_cards = tuple(StatCard("", compact=True) for _ in range(4))
        self.stats_row = ResponsiveRow(self.stat_cards, min_item_width=190)
        self.upcoming_card = UpcomingPaymentsCard(self)
        self.cost_card = ChartCard("Monthly cost by category", "Active subscriptions only",
                                   CategorySpendingChart())

        # Subscription list with row actions
        self.list_card = Card("All subscriptions")
        self.table = QTableWidget()
        self.table.setObjectName("DataTable")
        self.table.setColumnCount(len(TABLE_HEADERS))
        for column, title in enumerate(TABLE_HEADERS):
            header_item = QTableWidgetItem(title)
            header_item.setTextAlignment(_alignment(column))
            self.table.setHorizontalHeaderItem(column, header_item)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setHighlightSections(False)  # no bold header for the selected row
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self._update_actions)
        self.table.doubleClicked.connect(lambda _index: self.edit_selected())
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_selected)
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.toggle_selected)
        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("DangerButton")
        self.delete_button.clicked.connect(self.delete_selected)
        actions = QHBoxLayout()
        actions.addStretch(1)
        for button in (self.edit_button, self.pause_button, self.delete_button):
            actions.addWidget(button)
        self.list_card.body.addWidget(self.table)
        self.list_card.body.addLayout(actions)

        self.empty_state = EmptyState(
            "No subscriptions yet",
            "Add Netflix, your phone plan, internet or any other regular payment to see what "
            "they cost per month and when the next ones are due.",
            badge=None,
            action_text="Add subscription",
        )
        self.empty_state.action_clicked.connect(self.create_subscription)

        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.MD)
        grid.setVerticalSpacing(Spacing.MD)
        grid.addWidget(self.stats_row, 0, 0, 1, 12)
        self.overview_row = AdaptiveRow([(self.upcoming_card, 7), (self.cost_card, 5)],
                                        SIDE_BY_SIDE_MIN_WIDTH)
        grid.addWidget(self.overview_row, 1, 0, 1, 12)
        grid.addWidget(self.list_card, 2, 0, 1, 12)
        for column in range(12):
            grid.setColumnStretch(column, 1)
        self._grid_widgets = [self.stats_row, self.overview_row, self.list_card]

        content = QWidget()
        content.setObjectName("TransparentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, Spacing.SM, 0)
        content_layout.addWidget(self.empty_state)
        content_layout.addLayout(grid)
        content_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)

        self.add_content(scroll, stretch=1)

    # ------------------------------------------------------------ loading

    def on_shown(self) -> None:
        # Nothing changed since the page was last shown: keep what is on screen.
        if self.already_current(self._services.freshness()):
            return
        self.refresh()

    def refresh(self) -> None:
        try:
            stats = self._services.subscriptions.statistics()
            names = {c.id: c.name for c in self._services.categories.list(include_archived=True)}
        except MoneyManagerError as exc:
            logger.warning("Could not load subscriptions: %s", exc)
            dialogs.show_warning(self, "Could not load subscriptions", str(exc))
            return
        self.stats = stats
        self._subscriptions = list(stats.subscriptions)
        has_any = bool(self._subscriptions)
        self.empty_state.setVisible(not has_any)
        self.new_button.setVisible(has_any)  # the empty state has its own button
        for widget in self._grid_widgets:
            widget.setVisible(has_any)
        if not has_any:
            return

        for card, stat in zip(self.stat_cards, summary_stats(stats), strict=True):
            card.label.setText(stat.label)
            card.set_value(stat.value, stat.tone)
            card.set_caption(stat.caption)
        self.upcoming_card.set_rows([upcoming_row(p) for p in stats.upcoming])
        rows = category_cost_rows(stats)
        self.cost_card.chart.render(rows)
        self.cost_card.set_table(category_spending_table(rows))
        self._fill_table(names)

    def _fill_table(self, names: dict[int, str]) -> None:
        today = self._services.today()
        self.table.setRowCount(len(self._subscriptions))
        for row, subscription in enumerate(self._subscriptions):
            for column, text in enumerate(subscription_row(subscription, names, today)):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, subscription.id)
                item.setTextAlignment(_alignment(column))
                self.table.setItem(row, column, item)
        self.table.setFixedHeight(
            self.table.horizontalHeader().sizeHint().height()
            + max(len(self._subscriptions), 1) * 34 + 4
        )
        self._update_actions()

    # ------------------------------------------------------------ actions

    def selected(self) -> Subscription | None:
        rows = self.table.selectionModel().selectedRows()
        return self._subscriptions[rows[0].row()] if rows else None

    def select(self, subscription_id: int) -> None:
        for row, subscription in enumerate(self._subscriptions):
            if subscription.id == subscription_id:
                self.table.selectRow(row)

    def create_subscription(self) -> None:
        if self.make_dialog(None).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def edit_selected(self) -> None:
        subscription = self.selected()
        if subscription is not None and self.make_dialog(subscription).exec() == \
                QDialog.DialogCode.Accepted:
            self.refresh()

    def toggle_selected(self) -> None:
        subscription = self.selected()
        if subscription is None:
            return
        self._run(lambda: self._services.subscriptions.set_active(
            subscription.id, not subscription.is_active))
        self.select(subscription.id)

    def delete_selected(self) -> None:
        subscription = self.selected()
        if subscription is None:
            return
        if not dialogs.confirm_destructive(
            self, "Delete subscription",
            f"Delete the subscription “{subscription.name}”? Expenses already recorded for it "
            "stay in your transactions.",
        ):
            return
        self._run(lambda: self._services.subscriptions.delete(subscription.id))

    def record_payment(self, subscription_id: int, due_date: date) -> None:
        subscription = next((s for s in self._subscriptions if s.id == subscription_id), None)
        if subscription is None:
            return
        dialog = RecordPaymentDialog(self._services, subscription, due_date, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def skip_payment(self, subscription_id: int, due_date: date) -> None:
        subscription = next((s for s in self._subscriptions if s.id == subscription_id), None)
        if subscription is None:
            return
        choice = dialogs.choose(
            self, "Skip payment",
            f"Skip the payment of “{subscription.name}” due {due_date:%d %b %Y}? No expense is "
            "recorded — use this if you already entered it or it was not charged.",
            [(SKIP, "Skip payment")],
        )
        if choice == SKIP:
            self._run(lambda: self._services.subscriptions.skip_payment(subscription_id, due_date))

    def make_dialog(self, subscription: Subscription | None) -> SubscriptionDialog:
        return SubscriptionDialog(self._services, subscription=subscription, parent=self)

    def _run(self, action: Callable[[], object]) -> None:
        try:
            action()
        except MoneyManagerError as exc:
            dialogs.show_warning(self, "Could not update the subscription", str(exc))
        self.refresh()

    def _update_actions(self) -> None:
        subscription = self.selected()
        for button in (self.edit_button, self.pause_button, self.delete_button):
            button.setEnabled(subscription is not None)
        self.pause_button.setText("Resume" if subscription and not subscription.is_active
                                  else "Pause")
