"""Layouts that adapt to the available width instead of forcing the page wider.

``FlowRow`` places widgets left to right and wraps them onto the next line when
they do not fit (filter bars, button rows). ``AdaptiveRow`` shows widgets side
by side on wide windows and stacks them on narrow ones (pairs of cards).
Both report a small minimum width, so a page never needs to scroll sideways.
"""

from collections.abc import Sequence

from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QBoxLayout,
    QComboBox,
    QLayout,
    QLayoutItem,
    QSizePolicy,
    QWidget,
)

from money_manager.ui.theme import Spacing


class FlowLayout(QLayout):
    def __init__(self, parent: QWidget | None = None, spacing: int = Spacing.SM) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._spacing = spacing
        self.setContentsMargins(0, 0, 0, 0)

    # QLayout interface
    def addItem(self, item: QLayoutItem) -> None:  # noqa: N802
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self) -> Qt.Orientation:  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._arrange(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._arrange(rect, apply=True)

    def sizeHint(self) -> QSize:  # noqa: N802
        width = sum(i.sizeHint().width() for i in self._visible()) + self._spacing * max(
            0, len(self._visible()) - 1)
        height = max((i.sizeHint().height() for i in self._visible()), default=0)
        margins = self.contentsMargins()
        return QSize(width + margins.left() + margins.right(),
                     height + margins.top() + margins.bottom())

    def minimumSize(self) -> QSize:  # noqa: N802
        size = QSize()
        for item in self._visible():
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def _visible(self) -> list[QLayoutItem]:
        return [i for i in self._items if i.widget() is None or not i.widget().isHidden()]

    def _arrange(self, rect: QRect, *, apply: bool) -> int:
        margins: QMargins = self.contentsMargins()
        area = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x, y, line_height = area.x(), area.y(), 0
        for item in self._visible():
            hint = item.sizeHint()
            width = min(hint.width(), area.width()) if area.width() > 0 else hint.width()
            if x > area.x() and x + width > area.right() + 1:
                x = area.x()
                y += line_height + self._spacing
                line_height = 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), QSize(width, hint.height())))
            x += width + self._spacing
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + margins.bottom()


class FlowRow(QWidget):
    """Widgets left to right, wrapping onto new lines when the row is too narrow."""

    def __init__(self, widgets: Sequence[QWidget] = (), parent: QWidget | None = None,
                 spacing: int = Spacing.SM) -> None:
        super().__init__(parent)
        self.flow = FlowLayout(self, spacing)
        policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        for widget in widgets:
            self.add(widget)

    def add(self, widget: QWidget) -> None:
        self.flow.addWidget(widget)


class AdaptiveRow(QWidget):
    """Side by side when at least ``breakpoint`` pixels wide, stacked otherwise."""

    def __init__(self, widgets: Sequence[tuple[QWidget, int]], breakpoint: int,
                 parent: QWidget | None = None, spacing: int = Spacing.MD, *,
                 align_top: bool = False) -> None:
        super().__init__(parent)
        self._widgets = list(widgets)
        self._breakpoint = breakpoint
        self._box = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self._box.setContentsMargins(0, 0, 0, 0)
        self._box.setSpacing(spacing)
        for widget, stretch in self._widgets:
            if align_top:
                self._box.addWidget(widget, stretch, Qt.AlignmentFlag.AlignTop)
            else:
                self._box.addWidget(widget, stretch)

    @property
    def stacked(self) -> bool:
        return self._box.direction() == QBoxLayout.Direction.TopToBottom

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        """Stacked, the row needs only as much width as its widest child."""
        widest = max((w.minimumSizeHint().width() for w, _ in self._widgets), default=0)
        hint = super().minimumSizeHint()
        return QSize(widest, hint.height())

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        side_by_side = (sum(w.minimumSizeHint().width() for w, _ in self._widgets)
                        + self._box.spacing() * (len(self._widgets) - 1))
        stacked = event.size().width() < max(self._breakpoint, side_by_side)
        if stacked != self.stacked:
            self._box.setDirection(QBoxLayout.Direction.TopToBottom if stacked
                                   else QBoxLayout.Direction.LeftToRight)
            for index, (_widget, stretch) in enumerate(self._widgets):
                self._box.setStretch(index, 0 if stacked else stretch)
            self.updateGeometry()
        super().resizeEvent(event)


def compact_combo(combo: QComboBox, characters: int = 12) -> None:
    """Let a combo box be narrower than its longest item (it is elided when needed)."""
    combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    combo.setMinimumContentsLength(characters)

