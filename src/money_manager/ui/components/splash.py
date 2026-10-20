"""Launch screen: four tiles pop in, the name appears and a bar fills.

Shown for about a second while the window is built, only when motion is on.
"""

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QGuiApplication, QLinearGradient, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from money_manager import APP_NAME
from money_manager.ui.theme import FONT_FAMILY, MONO_FONT_FAMILY, Colors
from money_manager.core.i18n import tr

INTRO_MS = 1100
FADE_MS = 300
TILE = 44
GAP = 8
TILE_COLORS = (Colors.ACCENT, Colors.SKY, Colors.CORAL, Colors.PINK)


def _ease_out_back(x: float) -> float:
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


class LaunchScreen(QWidget):
    intro_finished = Signal()

    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setFixedSize(380, 300)
        self.setWindowTitle(APP_NAME)
        self._progress = 0.0
        self._status = tr("Opening your data")
        self._intro = QPropertyAnimation(self, b"progress", self)
        self._intro.setDuration(INTRO_MS)
        self._intro.setStartValue(0.0)
        self._intro.setEndValue(1.0)
        self._intro.finished.connect(self._on_intro_done)
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(FADE_MS)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade.finished.connect(self.close)

    def start(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            self.move(screen.availableGeometry().center() - self.rect().center())
        self.show()
        self._intro.start()
        QTimer.singleShot(INTRO_MS * 2 // 3, self, lambda: self._set_status(tr("Ready")))

    def fade_out(self) -> None:
        self._fade.start()

    def _on_intro_done(self) -> None:
        self.intro_finished.emit()

    def _set_status(self, text: str) -> None:
        self._status = text
        self.update()

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float) -> None:
        self._progress = value
        self.update()

    progress = Property(float, _get_progress, _set_progress)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(Colors.INPUT_BORDER), 1))
        painter.setBrush(QColor(Colors.CONTENT_BG))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 28, 28)

        # Four tiles, each popping in a little after the previous one.
        left = (self.width() - (2 * TILE + GAP)) / 2
        top = 56.0
        painter.setPen(Qt.PenStyle.NoPen)
        for index, colour in enumerate(TILE_COLORS):
            local = min(max((self._progress - index * 0.1) / 0.45, 0.0), 1.0)
            scale = _ease_out_back(local) if local > 0 else 0.0
            if scale <= 0:
                continue
            column, row = index % 2, index // 2
            cx = left + column * (TILE + GAP) + TILE / 2
            cy = top + row * (TILE + GAP) + TILE / 2
            size = TILE * scale
            painter.setBrush(QColor(colour))
            painter.drawRoundedRect(QRectF(cx - size / 2, cy - size / 2, size, size),
                                    14 * scale, 14 * scale)

        text_opacity = min(max((self._progress - 0.35) / 0.35, 0.0), 1.0)
        painter.setOpacity(text_opacity)
        title = QFont(FONT_FAMILY)
        title.setPixelSize(24)
        title.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title)
        painter.setPen(QColor(Colors.TEXT))
        painter.drawText(QRectF(0, 172, self.width(), 32), Qt.AlignmentFlag.AlignCenter, APP_NAME)
        status = QFont(MONO_FONT_FAMILY)
        status.setPixelSize(12)
        painter.setFont(status)
        painter.setPen(QColor(Colors.TEXT_MUTED))
        painter.drawText(QRectF(0, 206, self.width(), 20), Qt.AlignmentFlag.AlignCenter,
                         self._status)
        painter.setOpacity(1.0)

        # The bar: a track and a lime → sky → pink fill.
        bar = QRectF((self.width() - 220) / 2, 246, 220, 4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(Colors.PROGRESS_TRACK))
        painter.drawRoundedRect(bar, 2, 2)
        gradient = QLinearGradient(bar.topLeft(), bar.topRight())
        gradient.setColorAt(0, QColor(Colors.ACCENT))
        gradient.setColorAt(0.5, QColor(Colors.SKY))
        gradient.setColorAt(1, QColor(Colors.PINK))
        painter.setBrush(gradient)
        filled = QRectF(bar.left(), bar.top(), bar.width() * self._progress, bar.height())
        painter.drawRoundedRect(filled, 2, 2)
        painter.end()
