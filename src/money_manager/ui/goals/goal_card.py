from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from money_manager.ui.components.card import Card
from money_manager.ui.components.progress_ring import ProgressRing
from money_manager.ui.goals.view_model import GoalCardView
from money_manager.ui.theme import Spacing, identity_color, set_style_property
from money_manager.core.i18n import tr


class GoalCard(Card):
    """One goal: a progress ring in the goal's colour, status, amounts, deadline,
    pace and actions."""

    add_requested = Signal(int)
    withdraw_requested = Signal(int)
    set_amount_requested = Signal(int)
    edit_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, view: GoalCardView, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.view = view
        self.body.setSpacing(Spacing.MD)

        self.ring = ProgressRing(112, 9)
        self.ring.set_progress(float(view.bar_fraction), view.percent,
                               identity_color(view.goal_id))  # drawing only

        title = QLabel(view.name)
        title.setObjectName("CardHeading")
        title.setWordWrap(True)
        self.badge = QLabel(view.status_text)
        self.badge.setObjectName("LevelBadge")
        set_style_property(self.badge, "level", view.status_level)
        header = QHBoxLayout()
        header.setSpacing(Spacing.SM)
        header.addWidget(title, 1)
        header.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignTop)

        details = QVBoxLayout()
        details.setSpacing(6)
        details.addLayout(header)
        if view.description:
            description = QLabel(view.description)
            description.setObjectName("CardBody")
            description.setWordWrap(True)
            details.addWidget(description)
        self.amounts_label = QLabel(view.amounts)
        self.amounts_label.setObjectName("AllocationAmount")
        self.amounts_label.setWordWrap(True)
        details.addWidget(self.amounts_label)
        for text in (view.remaining, view.deadline, view.pace, view.tracking):
            label = QLabel(text)
            label.setObjectName("MutedLabel")
            label.setWordWrap(True)
            details.addWidget(label)
        details.addStretch(1)

        top = QHBoxLayout()
        top.setSpacing(Spacing.LG)
        top.addWidget(self.ring, 0, Qt.AlignmentFlag.AlignTop)
        top.addLayout(details, 1)
        self.body.addLayout(top)

        actions = QHBoxLayout()
        actions.setSpacing(Spacing.SM)
        if view.is_manual:
            self.primary_button = self._button(tr("Update amount"), self.set_amount_requested,
                                               primary=True)
            actions.addWidget(self.primary_button)
        else:
            self.primary_button = self._button(tr("Add money"), self.add_requested, primary=True)
            actions.addWidget(self.primary_button)
            actions.addWidget(self._button(tr("Withdraw"), self.withdraw_requested))
        actions.addStretch(1)
        actions.addWidget(self._button(tr("Edit"), self.edit_requested))
        self.delete_button = self._button(tr("Delete"), self.delete_requested)
        self.delete_button.setObjectName("DangerButton")
        actions.addWidget(self.delete_button)
        self.body.addStretch(1)
        self.body.addLayout(actions)

    def _button(self, text: str, signal: Signal, *, primary: bool = False) -> QPushButton:
        button = QPushButton(text)
        if primary:
            button.setObjectName("PrimaryButton")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda _checked=False: signal.emit(self.view.goal_id))
        return button
