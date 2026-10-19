from typing import Literal

from PySide6.QtCore import QAbstractAnimation
from PySide6.QtGui import QFont, QFontMetrics, QResizeEvent
from PySide6.QtWidgets import QLabel, QWidget

from money_manager.ui import motion
from money_manager.ui.components.card import Card
from money_manager.ui.theme import FILL_COLORS, FontSize, Spacing, mono_font, set_style_property

Tone = Literal["neutral", "inflow", "outflow"]

# Figure sizes, largest first: a figure never gets clipped, it steps down instead.
FIT_SIZES = (("", FontSize.STAT), ("m", FontSize.STAT_M), ("s", FontSize.STAT_S),
             ("xs", FontSize.STAT_XS))


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
        self._compact = compact
        self._value = "—"
        self._counting: QAbstractAnimation | None = None

        self.label = QLabel(label)
        self.label.setObjectName("StatLabel")
        self.value_label = QLabel(self._value)
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
        """The exact figure (never an intermediate one while counting up)."""
        return self._value

    def count_up(self) -> None:
        """Count the figure up from zero (when motion is on)."""
        self._stop_counting()
        self._counting = motion.count_up(self.value_label, self)

    def set_value(self, text: str, tone: Tone = "neutral") -> None:
        self._stop_counting()
        self._value = text
        self.value_label.setText(text)
        self._fit()
        set_style_property(self.value_label, "tone", tone)
        self.setAccessibleName(f"{self.label.text()}: {text}")

    def set_caption(self, text: str) -> None:
        self.caption_label.setText(text)
        self.setAccessibleDescription(text)
        self.caption_label.setVisible(bool(text))

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._fit()

    def _fit(self) -> None:
        """Pick the largest figure size at which the exact value fits the tile."""
        margins = self.body.contentsMargins()
        available = self.width() - margins.left() - margins.right()
        if available <= 0:
            return
        largest = FontSize.STAT_COMPACT if self._compact else FontSize.STAT
        candidates = [("", largest), *((name, size) for name, size in FIT_SIZES if size < largest)]
        chosen = candidates[-1][0]
        for name, size in candidates:
            font = mono_font(QFont())
            font.setPixelSize(size)
            font.setWeight(QFont.Weight.DemiBold)
            if QFontMetrics(font).horizontalAdvance(self._value) <= available:
                chosen = name
                break
        if self.value_label.property("fit") != chosen:
            set_style_property(self.value_label, "fit", chosen)

    def _stop_counting(self) -> None:
        if self._counting is not None:
            self._counting.stop()
            self._counting = None
            self.value_label.setText(self._value)

    def set_fill(self, fill: str | None) -> None:
        """Fill the tile with a named page colour (see ``theme.FILL_COLORS``), or clear it."""
        if fill is not None and fill not in FILL_COLORS:
            raise ValueError(f"Unknown fill colour: {fill!r}")
        self.fill = fill
        set_style_property(self, "fill", fill or "")
        for label in (self.label, self.value_label, self.caption_label):
            set_style_property(label, "onfill", fill is not None)
