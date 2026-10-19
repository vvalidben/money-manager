from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from money_manager.ui import motion
from money_manager.ui.theme import MONO_FONT_FAMILY, Colors


class ProgressRing(QWidget):
    """A ring that fills clockwise from the top, with the percentage inside.

    ``fraction`` is for drawing only (0…1, capped); ``text`` is the exact
    percentage shown in the middle."""

    def __init__(self, diameter: int = 112, thickness: int = 9,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._diameter = diameter
        self._thickness = thickness
        self._shown = 0.0
        self._target = 0.0
        self._color = QColor(Colors.ACCENT)
        self._text = ""
        self._animation: QPropertyAnimation | None = None
        self.setFixedSize(diameter, diameter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._diameter, self._diameter)

    @property
    def fraction(self) -> float:
        return self._target

    @property
    def text(self) -> str:
        return self._text

    def set_progress(self, fraction: float, text: str, color: str) -> None:
        self._target = min(max(fraction, 0.0), 1.0)
        self._text = text
        self._color = QColor(color)
        self.setAccessibleName(f"{text} complete")
        if self._animation is not None:
            self._animation.stop()
        self._set_shown(self._target)

    def sweep_in(self) -> None:
        """Draw the arc from empty to its value (when motion is on)."""
        if not motion.enabled() or self._target <= 0:
            return
        self._animation = QPropertyAnimation(self, b"shown", self)
        self._animation.setDuration(motion.FILL_MS + 300)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(self._target)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()

    def _get_shown(self) -> float:
        return self._shown

    def _set_shown(self, value: float) -> None:
        self._shown = value
        self.update()

    shown = Property(float, _get_shown, _set_shown)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        inset = self._thickness / 2 + 1
        rect = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)

        track = QPen(QColor(Colors.PROGRESS_TRACK), self._thickness)
        painter.setPen(track)
        painter.drawEllipse(rect)

        if self._shown > 0:
            arc = QPen(self._color, self._thickness)
            arc.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc)
            painter.drawArc(rect, 90 * 16, -round(self._shown * 360 * 16))

        font = QFont(MONO_FONT_FAMILY)
        font.setPixelSize(max(12, self._diameter // 5))
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(Colors.TEXT))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._text)
        painter.end()
