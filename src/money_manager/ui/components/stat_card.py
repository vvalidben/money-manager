from typing import Literal

from PySide6.QtWidgets import QLabel, QWidget

from money_manager.ui.components.card import Card
from money_manager.ui.theme import FILL_COLORS, Spacing, set_style_property

Tone = Literal["neutral", "inflow", "outflow"]


class StatCard(Card):
    """One labelled figure on a rounded tile, the value in the figures face.

    ``set_fill`` turns it into a page's headline tile: filled with the page's
    colour, dark text."""

    def __init__(self, label: str, parent: QWidget | None = None, *, compact: bool = False) -> None:
        super().__init__(parent=parent)
        self.setObjectName("StatColumn")
        self.body.setSpacing(Spacing.XS)
        self.body.setContentsMargins(20, 18, 20, 18)
        if compact:
            self.body.setContentsMargins(18, 14, 18, 14)
            self.body.setSpacing(2)
        self.fill: str | None = None

        self.label = QLabel(label)
        self.label.setObjectName("StatLabel")
        self.value_label = QLabel("—")
        self.value_label.setObjectName("StatValueCompact" if compact else "StatValue")
        self.caption_label = QLabel()
        self.caption_label.setObjectName("MutedLabel")
        self.caption_label.setWordWrap(True)
        self.caption_label.hide()

        self.body.addWidget(self.label)
        self.body.addWidget(self.value_label)
        self.body.addWidget(self.caption_label)
        self.body.addStretch(1)  # keep cards in a row top-aligned when captions wrap

    @property
    def value(self) -> str:
        return self.value_label.text()

    def set_value(self, text: str, tone: Tone = "neutral") -> None:
        self.value_label.setText(text)
        set_style_property(self.value_label, "tone", tone)
        self.setAccessibleName(f"{self.label.text()}: {text}")

    def set_caption(self, text: str) -> None:
        self.caption_label.setText(text)
        self.setAccessibleDescription(text)
        self.caption_label.setVisible(bool(text))

    def set_fill(self, fill: str | None) -> None:
        """Fill the tile with a named page colour (see ``theme.FILL_COLORS``), or clear it."""
        if fill is not None and fill not in FILL_COLORS:
            raise ValueError(f"Unknown fill colour: {fill!r}")
        self.fill = fill
        set_style_property(self, "fill", fill or "")
        for label in (self.label, self.value_label, self.caption_label):
            set_style_property(label, "onfill", fill is not None)
