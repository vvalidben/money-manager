from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QWidget

from money_manager.ui.components.card import Card
from money_manager.ui.goals.view_model import GoalCardView
from money_manager.ui.theme import Spacing, set_style_property

BAR_STEPS = 1000


class GoalCard(Card):
    """One goal: status, progress bar, amounts, deadline, pace and actions."""

    add_requested = Signal(int)
    withdraw_requested = Signal(int)
    set_amount_requested = Signal(int)
    edit_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, view: GoalCardView, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.view = view
        self.body.setSpacing(Spacing.SM)

        title = QLabel(view.name)
        title.setObjectName("CardHeading")
        title.setWordWrap(True)
        self.badge = QLabel(view.status_text)
        self.badge.setObjectName("LevelBadge")
        set_style_property(self.badge, "level", view.status_level)
        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.badge)
        self.body.addLayout(header)

        if view.description:
            description = QLabel(view.description)
            description.setObjectName("CardBody")
            description.setWordWrap(True)
            self.body.addWidget(description)

        self.bar = QProgressBar()
        self.bar.setObjectName("GoalBar")
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        self.bar.setRange(0, BAR_STEPS)
        self.bar.setValue(int(view.bar_fraction * BAR_STEPS))  # drawing only
        self.body.addWidget(self.bar)

        amounts = QHBoxLayout()
        self.amounts_label = QLabel(view.amounts)
        self.amounts_label.setObjectName("AllocationAmount")
        self.amounts_label.setWordWrap(True)
        self.percent_label = QLabel(view.percent)
        self.percent_label.setObjectName("AllocationAmount")
        # The label takes the free width, so it wraps only when it really runs out of room.
        amounts.addWidget(self.amounts_label, 1)
        amounts.addWidget(self.percent_label, 0, Qt.AlignmentFlag.AlignTop)
        self.body.addLayout(amounts)

        for text in (view.remaining, view.deadline, view.pace, view.tracking):
            label = QLabel(text)
            label.setObjectName("MutedLabel")
            label.setWordWrap(True)
            self.body.addWidget(label)

        actions = QHBoxLayout()
        actions.setSpacing(Spacing.SM)
        if view.is_manual:
            self.primary_button = self._button("Update amount", self.set_amount_requested,
                                               primary=True)
            actions.addWidget(self.primary_button)
        else:
            self.primary_button = self._button("Add money", self.add_requested, primary=True)
            actions.addWidget(self.primary_button)
            actions.addWidget(self._button("Withdraw", self.withdraw_requested))
        actions.addStretch(1)
        actions.addWidget(self._button("Edit", self.edit_requested))
        self.delete_button = self._button("Delete", self.delete_requested)
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
