from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from money_manager.ui import motion
from money_manager.ui.theme import Colors, Spacing

SHOW_MS = 2800
MARGIN = 24
SLIDE_PX = 18


def _check_label() -> QLabel:
    from money_manager.ui.navigation import line_pixmap  # avoids an import cycle

    label = QLabel()
    label.setObjectName("ToastCheck")
    label.setFixedSize(32, 32)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setPixmap(line_pixmap("M5 12.5l4.5 4.5L19 7.5", Colors.ON_ACCENT, 18, 2.6))
    return label


class Toast(QFrame):
    """A short confirmation that slides up at the bottom of ``host`` and fades away."""

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self.setObjectName("Toast")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._host = host

        self.title_label = QLabel()
        self.title_label.setObjectName("ToastTitle")
        self.detail_label = QLabel()
        self.detail_label.setObjectName("ToastDetail")
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(self.title_label)
        text.addWidget(self.detail_label)
        row = QHBoxLayout(self)
        row.setContentsMargins(Spacing.MD, 12, Spacing.LG, 12)
        row.setSpacing(12)
        row.addWidget(_check_label())
        row.addLayout(text)

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._leave)
        self._animation: QAbstractAnimation | None = None
        self.hide()

    @property
    def message(self) -> tuple[str, str]:
        return self.title_label.text(), self.detail_label.text()

    def show_message(self, title: str, detail: str = "") -> None:
        self.title_label.setText(title)
        self.detail_label.setText(detail)
        self.detail_label.setVisible(bool(detail))
        self.setAccessibleName(f"{title}. {detail}" if detail else title)
        self._stop()
        self.show()  # size after showing, once styled: the hint is right only then
        self.ensurePolished()
        self.layout().activate()
        self.resize(self.sizeHint())
        end = self._resting_position()
        self.raise_()
        if motion.enabled():
            self._animate(end + QPoint(0, SLIDE_PX), end, 0.0, 1.0, 320)
        else:
            self.move(end)
            self._effect.setOpacity(1.0)
        self._timer.start(SHOW_MS)

    def _resting_position(self) -> QPoint:
        """Bottom centre, where pages keep no controls (footers sit left and right)."""
        return QPoint((self._host.width() - self.width()) // 2,
                      self._host.height() - self.height() - MARGIN)

    def _leave(self) -> None:
        if not motion.enabled():
            self.hide()
            return
        self._animate(self.pos(), self.pos() + QPoint(0, SLIDE_PX // 2), 1.0, 0.0, 240)
        assert self._animation is not None
        self._animation.finished.connect(self.hide)

    def _animate(self, start: QPoint, end: QPoint, fade_from: float, fade_to: float,
                 duration: int) -> None:
        group = QParallelAnimationGroup(self)
        slide = QPropertyAnimation(self, b"pos")
        slide.setStartValue(start)
        slide.setEndValue(end)
        slide.setDuration(duration)
        slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        fade = QPropertyAnimation(self._effect, b"opacity")
        fade.setStartValue(fade_from)
        fade.setEndValue(fade_to)
        fade.setDuration(duration)
        group.addAnimation(slide)
        group.addAnimation(fade)
        self._animation = group
        group.start()

    def _stop(self) -> None:
        self._timer.stop()
        if self._animation is not None:
            self._animation.stop()
            self._animation = None
        self._effect.setOpacity(1.0)
