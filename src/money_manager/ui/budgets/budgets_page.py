"""Budgets page: monthly limits per expense category and this month's spending."""

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError
from money_manager.domain.budgets import BudgetSummary
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.budgets.budget_dialog import BudgetDialog
from money_manager.ui.budgets.view_model import BudgetCardView, budget_card_view, summary_stats
from money_manager.ui.components import Card, EmptyState, ResponsiveRow, StatCard
from money_manager.ui.navigation import dot_pixmap
from money_manager.ui.pages.base_page import BasePage
from money_manager.ui.pages.registry import PageSpec
from money_manager.ui.theme import Spacing, identity_color, set_style_property

logger = logging.getLogger(__name__)

BAR_STEPS = 1000
BUDGET_CARD_MIN_WIDTH = 380


class BudgetCard(Card):
    edit_requested = Signal(int)
    remove_requested = Signal(int)

    def __init__(self, view: BudgetCardView, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.view = view
        self.body.setSpacing(Spacing.SM)

        dot = QLabel()
        dot.setPixmap(dot_pixmap(identity_color(view.category_id), 10))
        title = QLabel(view.name)
        title.setObjectName("CardHeading")
        self.chip = QLabel(view.status)
        self.chip.setObjectName("LevelBadge")
        set_style_property(self.chip, "level", view.chip_level)
        header = QHBoxLayout()
        header.setSpacing(Spacing.SM)
        header.addWidget(dot)
        header.addWidget(title, 1)
        header.addWidget(self.chip)
        self.body.addLayout(header)

        amounts = QHBoxLayout()
        amounts.setSpacing(Spacing.SM)
        self.spent_label = QLabel(view.spent)
        self.spent_label.setObjectName("AllocationAmount")
        limit = QLabel(view.limit)
        limit.setObjectName("MutedLabel")
        percent = QLabel(view.percent)
        percent.setObjectName("AllocationAmount")
        amounts.addWidget(self.spent_label)
        amounts.addWidget(limit)
        amounts.addStretch(1)
        amounts.addWidget(percent)
        self.body.addLayout(amounts)

        self.bar = QProgressBar()
        self.bar.setObjectName("BudgetBar")
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        self.bar.setRange(0, BAR_STEPS)
        self.bar.setValue(int(view.bar_fraction * BAR_STEPS))  # drawing only
        set_style_property(self.bar, "level", view.bar_level)
        self.bar.setAccessibleName(f"{view.name}: {view.percent} of the monthly limit")
        self.body.addWidget(self.bar)

        for text in (view.left, view.projection):
            if text:
                label = QLabel(text)
                label.setObjectName("MutedLabel")
                label.setWordWrap(True)
                self.body.addWidget(label)

        actions = QHBoxLayout()
        actions.addStretch(1)
        edit = QPushButton("Edit")
        edit.clicked.connect(lambda: self.edit_requested.emit(view.category_id))
        remove = QPushButton("Remove")
        remove.setObjectName("DangerButton")
        remove.clicked.connect(lambda: self.remove_requested.emit(view.category_id))
        actions.addWidget(edit)
        actions.addWidget(remove)
        self.body.addStretch(1)
        self.body.addLayout(actions)


class BudgetsPage(BasePage):
    def __init__(self, spec: PageSpec, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(spec, parent, fill=True)
        self._services = services
        self.summary: BudgetSummary | None = None
        self.cards: list[BudgetCard] = []

        self.new_button = QPushButton("New budget")
        self.new_button.setObjectName("PrimaryButton")
        self.new_button.clicked.connect(self.create_budget)
        self.new_button.setToolTip("New budget (Ctrl+N)")
        self.header.add_action(self.new_button)
        self.primary_button = self.new_button

        self.stat_cards = tuple(StatCard("", compact=True) for _ in range(4))
        self.stats_row = ResponsiveRow(self.stat_cards, min_item_width=190)
        self.empty_state = EmptyState(
            "No budgets yet",
            "Set a monthly limit for a spending category, such as groceries or eating out, "
            "and see at a glance how much is left this month.",
            badge=None,
            action_text="Create a budget",
        )
        self.empty_state.action_clicked.connect(self.create_budget)

        self.cards_host = QWidget()
        self.cards_host.setObjectName("TransparentArea")
        self.cards_layout = QVBoxLayout(self.cards_host)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)

        content = QWidget()
        content.setObjectName("TransparentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, Spacing.SM, 0)
        content_layout.setSpacing(Spacing.MD)
        content_layout.addWidget(self.stats_row)
        content_layout.addWidget(self.empty_state)
        content_layout.addWidget(self.cards_host)
        content_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        self.add_content(scroll, stretch=1)

    def on_shown(self) -> None:
        if self.already_current(self._services.freshness()):
            return
        self.refresh()

    def refresh(self) -> None:
        try:
            summary = self._services.budgets.overview()
        except MoneyManagerError as exc:
            logger.warning("Could not load budgets: %s", exc)
            dialogs.show_warning(self, "Could not load budgets", str(exc))
            return
        self.summary = summary
        for card, stat in zip(self.stat_cards, summary_stats(summary), strict=True):
            card.label.setText(stat.label)
            card.set_value(stat.value, stat.tone)
            card.set_caption(stat.caption)
        self._rebuild_cards(summary)
        has_budgets = bool(summary.statuses)
        self.empty_state.setVisible(not has_budgets)
        self.new_button.setVisible(has_budgets)  # the empty state has its own button
        self.stats_row.setVisible(has_budgets)
        self.cards_host.setVisible(has_budgets)

    def card_for(self, category_id: int) -> BudgetCard:
        return next(card for card in self.cards if card.view.category_id == category_id)

    def _rebuild_cards(self, summary: BudgetSummary) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self.cards = []
        for status in summary.statuses:
            card = BudgetCard(budget_card_view(status))
            card.edit_requested.connect(self.edit_budget)
            card.remove_requested.connect(self.remove_budget)
            self.cards.append(card)
        if self.cards:
            self.cards_layout.addWidget(ResponsiveRow(self.cards, BUDGET_CARD_MIN_WIDTH))

    # ------------------------------------------------------------ actions

    def create_budget(self) -> None:
        dialog = self.make_budget_dialog(None)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved is not None:
            self.refresh()
            card = self.card_for(dialog.saved.category_id)
            self.notice.emit("Budget saved", f"{card.view.name} · {card.view.limit_amount} a month")

    def edit_budget(self, category_id: int) -> None:
        dialog = self.make_budget_dialog(category_id)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved is not None:
            self.refresh()
            card = self.card_for(category_id)
            self.notice.emit("Budget updated", f"{card.view.name} · {card.view.limit_amount} a month")

    def remove_budget(self, category_id: int) -> None:
        card = self.card_for(category_id)
        message = (f"Remove the budget for {card.view.name}?\n\nYour spending and the category "
                   "itself are not affected.")
        if not dialogs.confirm_destructive(self, "Remove budget", message, "Remove"):
            return
        try:
            self._services.budgets.remove(category_id)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, "Could not remove the budget", str(exc))
            return
        self.refresh()
        self.notice.emit("Budget removed", card.view.name)

    # Separate so tests can substitute non-modal fakes.
    def make_budget_dialog(self, category_id: int | None) -> BudgetDialog:
        limit = ""
        if category_id is not None and self.summary is not None:
            status = next(s for s in self.summary.statuses
                          if s.budget.category_id == category_id)
            limit = str(status.budget.limit.amount)
        return BudgetDialog(self._services, category_id=category_id, current_limit=limit,
                            parent=self)
