"""Goals page: summary, one card per goal, and create / edit / money actions."""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError
from money_manager.domain.goals import GoalProgress, GoalsSummary
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.components import EmptyState, ResponsiveRow, StatCard
from money_manager.ui.goals.amount_dialog import AmountAction, GoalAmountDialog
from money_manager.ui.goals.goal_card import GoalCard
from money_manager.ui.goals.goal_dialog import GoalDialog
from money_manager.ui.goals.view_model import goal_card_view, summary_stats
from money_manager.ui.pages.base_page import BasePage
from money_manager.ui.pages.registry import PageSpec
from money_manager.ui.theme import Spacing

logger = logging.getLogger(__name__)

GOAL_CARD_MIN_WIDTH = 380
KEEP_MONEY = "keep"
RELEASE_MONEY = "release"


class GoalsPage(BasePage):
    def __init__(self, spec: PageSpec, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(spec, parent, fill=True)
        self._services = services
        self.summary: GoalsSummary | None = None
        self.cards: list[GoalCard] = []

        self.new_button = QPushButton("New goal")
        self.new_button.setObjectName("PrimaryButton")
        self.new_button.clicked.connect(self.create_goal)
        self.new_button.setToolTip("New goal (Ctrl+N)")
        self.header.add_action(self.new_button)
        self.primary_button = self.new_button

        self.stat_cards = tuple(StatCard("", compact=True) for _ in range(4))
        self.stats_row = ResponsiveRow(self.stat_cards, min_item_width=190)

        self.empty_state = EmptyState(
            "No goals yet",
            "Create a goal such as an emergency fund, a trip or a new laptop. Keep its money "
            "in an allocation and track your progress towards the target.",
            badge=None,
            action_text="Create goal",
        )
        self.empty_state.action_clicked.connect(self.create_goal)

        self.cards_host = QWidget()
        self.cards_host.setObjectName("TransparentArea")
        self.cards_layout = QVBoxLayout(self.cards_host)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(Spacing.MD)

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

    # ------------------------------------------------------------ loading

    def on_shown(self) -> None:
        # Nothing changed since the page was last shown: keep what is on screen.
        if self.already_current(self._services.freshness()):
            return
        self.refresh()

    def refresh(self) -> None:
        try:
            summary = self._services.goals.summary()
        except MoneyManagerError as exc:
            logger.warning("Could not load goals: %s", exc)
            dialogs.show_warning(self, "Could not load goals", str(exc))
            return
        self.summary = summary
        for card, stat in zip(self.stat_cards, summary_stats(summary), strict=True):
            card.label.setText(stat.label)
            card.set_value(stat.value, stat.tone)
            card.set_caption(stat.caption)
        self._rebuild_cards(summary.goals)
        has_goals = bool(summary.goals)
        self.empty_state.setVisible(not has_goals)
        self.new_button.setVisible(has_goals)  # the empty state has its own button
        self.stats_row.setVisible(has_goals)
        self.cards_host.setVisible(has_goals)

    def card_for(self, goal_id: int) -> GoalCard:
        return next(card for card in self.cards if card.view.goal_id == goal_id)

    def _rebuild_cards(self, goals: tuple[GoalProgress, ...]) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self.cards = []
        for goal in goals:
            card = GoalCard(goal_card_view(goal))
            card.add_requested.connect(lambda gid: self.change_amount(gid, AmountAction.ADD))
            card.withdraw_requested.connect(
                lambda gid: self.change_amount(gid, AmountAction.WITHDRAW))
            card.set_amount_requested.connect(lambda gid: self.change_amount(gid, AmountAction.SET))
            card.edit_requested.connect(self.edit_goal)
            card.delete_requested.connect(self.delete_goal)
            self.cards.append(card)
        if self.cards:
            self.cards_layout.addWidget(ResponsiveRow(self.cards, GOAL_CARD_MIN_WIDTH))

    # ------------------------------------------------------------ actions

    def create_goal(self) -> None:
        if self.make_goal_dialog(None).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def edit_goal(self, goal_id: int) -> None:
        goal = self._goal(goal_id)
        if goal is not None and self.make_goal_dialog(goal).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def change_amount(self, goal_id: int, action: AmountAction) -> None:
        goal = self._goal(goal_id)
        if goal is None:
            return
        dialog = GoalAmountDialog(self._services, goal, action, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def delete_goal(self, goal_id: int) -> None:
        goal = self._goal(goal_id)
        if goal is None:
            return
        name = goal.goal.name
        if goal.goal.is_manual:
            if not dialogs.confirm_destructive(
                self, "Delete goal", f"Delete the goal “{name}”? This cannot be undone."
            ):
                return
            release = False
        else:
            choice = dialogs.choose(
                self,
                "Delete goal",
                f"Delete the goal “{name}”? Its money stays in your balance either way.",
                [
                    (KEEP_MONEY, f"Keep the money in “{goal.allocation_name}”"),
                    (RELEASE_MONEY, "Move the money back to Available"),
                ],
            )
            if choice is None:
                return
            release = choice == RELEASE_MONEY
        try:
            self._services.goals.delete(goal_id, release_money=release)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, "Could not delete goal", str(exc))
            return
        self.refresh()

    def make_goal_dialog(self, goal: GoalProgress | None) -> GoalDialog:
        return GoalDialog(self._services, goal=goal, parent=self)

    def _goal(self, goal_id: int) -> GoalProgress | None:
        try:
            return self._services.goals.get(goal_id)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, "Goal not available", str(exc))
            self.refresh()
            return None
