"""Motion: page entrances, counting figures, filling bars and short notices.

Every animation ends in exactly the state the widget would have without it, so
turning motion off changes nothing but the movement. Motion is off when:

* the user switched off *Animations* in Settings (``set_user_enabled``);
* Windows' "Show animations in Windows" is off (accessibility setting);
* ``MONEY_MANAGER_MOTION=off`` is set (used by the tests and the self-test).

Figures shown while counting are decorative; the exact value is set at the end
and is the only value exposed to code and assistive technology.
"""

import logging
import os
import re
import sys
from collections.abc import Iterable, Sequence

from PySide6.QtCore import (
    Property,
    QAbstractAnimation,
    QEasingCurve,
    QObject,
    QParallelAnimationGroup,
    QPauseAnimation,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QSequentialAnimationGroup,
    QVariantAnimation,
)
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsEffect, QLabel, QProgressBar, QWidget

logger = logging.getLogger(__name__)

MOTION_ENV = "MONEY_MANAGER_MOTION"
ENTRANCE_MS = 420
STAGGER_MS = 55
MAX_STAGGERED = 10  # later tiles share the last delay, so long pages are not slow
RISE_PX = 14
COUNT_MS = 900
FILL_MS = 900

_user_enabled = True
_NUMBER = re.compile(r"^(?P<before>\D*?)(?P<number>\d[\d,]*(?:\.(?P<decimals>\d+))?)(?P<after>.*)$",
                     re.DOTALL)


def set_user_enabled(enabled: bool) -> None:
    global _user_enabled
    _user_enabled = enabled


def user_enabled() -> bool:
    return _user_enabled


def system_allows() -> bool:
    """False when Windows' "Show animations in Windows" is switched off."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes

        value = ctypes.c_int(1)
        spi_getclientareaanimation = 0x1042
        if ctypes.windll.user32.SystemParametersInfoW(spi_getclientareaanimation, 0,
                                                      ctypes.byref(value), 0):
            return bool(value.value)
    except (AttributeError, OSError):
        logger.debug("Could not read the Windows animation setting", exc_info=True)
    return True


def enabled() -> bool:
    if os.environ.get(MOTION_ENV, "").strip().lower() in ("off", "0", "false", "no"):
        return False
    return _user_enabled and system_allows()


# ------------------------------------------------------------------ entrances

class RiseEffect(QGraphicsEffect):
    """Draws its widget faded and lowered by a fraction of ``RISE_PX``.

    Only the painting moves: the widget keeps its real place in the layout, so
    a layout change during an entrance can never leave it out of position."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._progress = 0.0

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float) -> None:
        self._progress = value
        self.update()

    progress = Property(float, _get_progress, _set_progress)

    def boundingRectFor(self, rect: QRectF) -> QRectF:  # noqa: N802
        return rect.adjusted(0, 0, 0, RISE_PX)

    def draw(self, painter: QPainter) -> None:
        painter.save()
        painter.setOpacity(self._progress)
        painter.translate(0, (1 - self._progress) * RISE_PX)
        self.drawSource(painter)
        painter.restore()


def entrance(widgets: Sequence[QWidget], owner: QObject) -> QAbstractAnimation | None:
    """Fade the widgets in and lift them into place, one after another.

    Returns the running animation (owned by ``owner``) or None without motion.
    Call ``finish`` on it to jump to the end state at once."""
    if not enabled():
        return None
    targets = [w for w in widgets if w.isVisible() and w.graphicsEffect() is None]
    group = QParallelAnimationGroup(owner)
    for index, widget in enumerate(targets):
        effect = RiseEffect(widget)
        widget.setGraphicsEffect(effect)
        rise = QPropertyAnimation(effect, b"progress")
        rise.setDuration(ENTRANCE_MS)
        rise.setStartValue(0.0)
        rise.setEndValue(1.0)
        rise.setEasingCurve(QEasingCurve.Type.OutCubic)
        step = QSequentialAnimationGroup()
        step.addAnimation(QPauseAnimation(min(index, MAX_STAGGERED) * STAGGER_MS))
        step.addAnimation(rise)
        group.addAnimation(step)
    group._targets = targets  # type: ignore[attr-defined]
    group.finished.connect(lambda: _clear_effects(group))
    group.start()
    return group


def finish(animation: QAbstractAnimation | None) -> None:
    """Jump an entrance (or any animation) to its end state."""
    if animation is None:
        return
    if animation.state() != QAbstractAnimation.State.Stopped:
        animation.setCurrentTime(animation.totalDuration())
        animation.stop()
    if isinstance(animation, QParallelAnimationGroup):
        _clear_effects(animation)


def _clear_effects(group: QParallelAnimationGroup) -> None:
    """Effects cost repainting and soften text: remove them once done."""
    for widget in getattr(group, "_targets", []):
        try:
            effect = widget.graphicsEffect()
        except RuntimeError:  # the widget was deleted meanwhile
            continue
        if isinstance(effect, RiseEffect):
            widget.setGraphicsEffect(None)  # type: ignore[arg-type]
    group._targets = []  # type: ignore[attr-defined]


def top_level_tiles(root: QWidget, tile_types: tuple[type, ...]) -> list[QWidget]:
    """Visible tiles under ``root`` that are not inside another tile, top to bottom."""
    tiles = []
    for widget in root.findChildren(QWidget):
        if not isinstance(widget, tile_types) or not widget.isVisible():
            continue
        parent = widget.parentWidget()
        nested = False
        while parent is not None and parent is not root:
            if isinstance(parent, tile_types):
                nested = True
                break
            parent = parent.parentWidget()
        if not nested:
            tiles.append(widget)
    tiles.sort(key=lambda w: (w.mapTo(root, QPoint(0, 0)).y(), w.mapTo(root, QPoint(0, 0)).x()))
    return tiles


# ------------------------------------------------------------------ figures

def split_number(text: str) -> tuple[str, float, int, str] | None:
    """("−", 1300.0, 2, " MAD") for "−1,300.00 MAD"; None when there is no number."""
    match = _NUMBER.match(text)
    if match is None:
        return None
    number = match.group("number").replace(",", "")
    decimals = len(match.group("decimals") or "")
    return match.group("before"), float(number), decimals, match.group("after")


def count_up(label: QLabel, owner: QObject, duration: int = COUNT_MS) -> QAbstractAnimation | None:
    """Count the label's figure up from zero, ending on its exact text.

    The caller stops the returned animation if the figure changes meanwhile
    (a stopped animation leaves the new text alone)."""
    final = label.text()
    parts = split_number(final)
    if not enabled() or parts is None or parts[1] == 0:
        return None
    before, value, decimals, after = parts
    animation = QVariantAnimation(owner)
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.valueChanged.connect(lambda progress: label.setText(
        f"{before}{value * float(progress):,.{decimals}f}{after}"))
    animation.finished.connect(lambda: label.setText(final))
    label.setText(f"{before}{0:,.{decimals}f}{after}")  # no flash of the final figure first
    animation.start()
    return animation


def fill(bars: Iterable[QProgressBar], owner: QObject, duration: int = FILL_MS) -> None:
    """Grow progress bars from empty to their current value."""
    if not enabled():
        return
    for index, bar in enumerate(bars):
        target = bar.value()
        if target <= bar.minimum():
            continue
        animation = QPropertyAnimation(bar, b"value", owner)
        animation.setDuration(duration + index * 60)
        animation.setStartValue(bar.minimum())
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
