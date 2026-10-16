from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from money_manager.ui.components.card import Card
from money_manager.ui.theme import Spacing


class EmptyState(Card):
    """Card explaining why a section is empty, with an optional call to action.

    Centred with generous spacing so an empty page reads as a deliberate
    starting point rather than a missing section.
    """

    action_clicked = Signal()

    def __init__(
        self,
        heading: str,
        message: str,
        badge: str | None = "Coming soon",
        action_text: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.setObjectName("EmptyState")
        self.body.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        self.body.setSpacing(Spacing.SM)
        centre = Qt.AlignmentFlag.AlignHCenter

        self.badge_label = QLabel(badge or "")
        self.badge_label.setObjectName("Badge")
        self.badge_label.setVisible(badge is not None)
        self.body.addWidget(self.badge_label, alignment=centre)

        self.heading_label = QLabel()
        self.heading_label.setObjectName("EmptyHeading")
        self.heading_label.setAlignment(centre)
        self.heading_label.setWordWrap(True)
        self.body.addWidget(self.heading_label)

        self.message_label = QLabel()
        self.message_label.setObjectName("CardBody")
        self.message_label.setAlignment(centre)
        self.message_label.setWordWrap(True)
        self.body.addWidget(self.message_label)

        self.action_button = QPushButton()
        self.action_button.setObjectName("PrimaryButton")
        self.action_button.clicked.connect(self.action_clicked)
        self.body.addSpacing(Spacing.XS)
        self.body.addWidget(self.action_button, alignment=centre)

        self.set_content(heading, message, action_text)

    def set_content(self, heading: str, message: str, action_text: str | None = None) -> None:
        self.heading_label.setText(heading)
        self.message_label.setText(message)
        self.action_button.setText(action_text or "")
        self.action_button.setVisible(action_text is not None)
        self.setAccessibleName(heading)
        self.setAccessibleDescription(message)
