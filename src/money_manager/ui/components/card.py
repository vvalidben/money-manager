from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from money_manager.ui.theme import Spacing


class Card(QFrame):
    """White rounded panel with an optional heading; add content to ``body``."""

    def __init__(self, heading: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)  # border lights up on hover

        self._body = QVBoxLayout(self)
        self._body.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        self._body.setSpacing(Spacing.SM)

        if heading is not None:
            heading_label = QLabel(heading)
            heading_label.setObjectName("CardHeading")
            self._body.addWidget(heading_label)

    @property
    def body(self) -> QVBoxLayout:
        return self._body
