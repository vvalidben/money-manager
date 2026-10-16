from collections.abc import Sequence

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from money_manager.ui.components.card import Card
from money_manager.ui.theme import Spacing


class FactsCard(Card):
    """A list of measurable statements produced by the financial-health engine."""

    def __init__(self, title: str, subtitle: str, parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        caption = QLabel(subtitle)
        caption.setObjectName("MutedLabel")
        caption.setWordWrap(True)
        self.body.addWidget(caption)
        self._list = QVBoxLayout()
        self._list.setSpacing(Spacing.XS)
        self.body.addLayout(self._list)
        self.facts: tuple[str, ...] = ()

    def set_facts(self, facts: Sequence[str]) -> None:
        while self._list.count():
            item = self._list.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self.facts = tuple(facts)
        for text in self.facts:
            label = QLabel(f"•  {text}")
            label.setObjectName("CardBody")
            label.setWordWrap(True)
            self._list.addWidget(label)
