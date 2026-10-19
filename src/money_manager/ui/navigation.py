"""Navigation rail: icon buttons that expand to show their labels.

The rail is 84 px wide and slides open to 268 px over the page while the mouse
is on it or it is reached with the keyboard (Tab). The current page's button is filled
with that page's colour.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import (
    QByteArray,
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QEnterEvent, QFocusEvent, QIcon, QPixmap, QResizeEvent, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from money_manager import APP_NAME, __version__
from money_manager.ui import motion
from money_manager.ui.theme import Colors, Spacing, page_fill, set_style_property

RAIL_WIDTH = 84
EXPANDED_WIDTH = 268
SIDEBAR_WIDTH = RAIL_WIDTH  # the space the rail takes in the window layout
BUTTON_HEIGHT = 38  # eleven pages must fit the smallest window
BRAND_SIZE = 44
ICON_SIZE = 20
ANIMATION_MS = 220
INDICATOR_MS = 420
KEYBOARD_FOCUS = (Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason,
                  Qt.FocusReason.ShortcutFocusReason)

# 24×24 line icons (stroke only), one per page; unknown pages get none.
ICON_PATHS = {
    "dashboard": "M3 3h7v7H3z M14 3h7v7h-7z M14 14h7v7h-7z M3 14h7v7H3z",
    "transactions": "M8 3 4 7l4 4 M4 7h16 M16 21l4-4-4-4 M20 17H4",
    "budgets": "M21 12A9 9 0 1 1 12 3v9z M15 3.5A9 9 0 0 1 20.5 9H15z",
    "accounts": "M3 21h18 M5 21V10 M9.5 21V10 M14.5 21V10 M19 21V10 M2 10l10-7 10 7z",
    "allocations": "M12 3 2 8l10 5 10-5z M2 13l10 5 10-5 M2 17.5l10 5 10-5",
    "goals": ("M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18 M12 7a5 5 0 1 0 0 10a5 5 0 1 0 0-10 "
              "M12 11a1 1 0 1 0 0 2a1 1 0 1 0 0-2"),
    "subscriptions": ("M17 2l4 4-4 4 M3 11v-1a4 4 0 0 1 4-4h14 M7 22l-4-4 4-4 "
                      "M21 13v1a4 4 0 0 1-4 4H3"),
    "investments": "M22 7l-8.5 8.5-5-5L2 17 M16 7h6v6",
    "statistics": "M3 3v18h18 M8 17v-5 M13 17V8 M18 17v-9",
    "ai_advisor": "M12 3l1.9 5.6 5.6 1.9-5.6 1.9L12 18l-1.9-5.6-5.6-1.9 5.6-1.9z",
    "settings": ("M4 21v-7 M4 10V3 M12 21v-9 M12 8V3 M20 21v-5 M20 12V3 M1 14h6 M9 8h6 "
                 "M17 16h6"),
}
SEARCH_PATH = "M11 3a8 8 0 1 0 0 16a8 8 0 1 0 0-16 M21 21l-4.3-4.3"
PLUS_PATH = "M5 12h14M12 5v14"


@dataclass(frozen=True, slots=True)
class NavItem:
    key: str
    label: str


def line_pixmap(path: str, colour: str, size: int = ICON_SIZE, stroke: float = 1.8,
                scale: int = 2) -> QPixmap:
    """Render a stroke-only 24×24 SVG path, sharp on high-DPI screens."""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size * scale}" '
           f'height="{size * scale}" viewBox="0 0 24 24"><path d="{path}" fill="none" '
           f'stroke="{colour}" stroke-width="{stroke}" stroke-linecap="round" '
           f'stroke-linejoin="round"/></svg>')
    pixmap = QPixmap()
    pixmap.loadFromData(QByteArray(svg.encode()), "SVG")
    pixmap.setDevicePixelRatio(scale)
    return pixmap


def line_icon(path: str, colour: str, size: int = ICON_SIZE, stroke: float = 1.8) -> QIcon:
    return QIcon(line_pixmap(path, colour, size, stroke))


def nav_icon(key: str) -> QIcon:
    path = ICON_PATHS.get(key)
    if path is None:
        return QIcon()
    icon = QIcon()
    icon.addPixmap(line_pixmap(path, Colors.SIDEBAR_TEXT), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(line_pixmap(path, Colors.NAV_ACTIVE_TEXT), QIcon.Mode.Normal, QIcon.State.On)
    icon.addPixmap(line_pixmap(path, Colors.TEXT), QIcon.Mode.Active, QIcon.State.Off)
    return icon


def dot_pixmap(colour: str, size: int = 6, scale: int = 2) -> QPixmap:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size * scale}" '
           f'height="{size * scale}" viewBox="0 0 10 10"><circle cx="5" cy="5" r="5" '
           f'fill="{colour}"/></svg>')
    pixmap = QPixmap()
    pixmap.loadFromData(QByteArray(svg.encode()), "SVG")
    pixmap.setDevicePixelRatio(scale)
    return pixmap


class Sidebar(QFrame):
    """Mutually exclusive navigation buttons in a rail that expands on demand.

    Emits ``page_selected(key)`` when the user clicks an item. Programmatic
    changes go through ``set_current`` and do not emit. The owner positions the
    rail (``place``); it is not part of a layout, so expanding overlays the page.
    """

    page_selected = Signal(str)

    def __init__(self, items: Sequence[NavItem], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.resize(RAIL_WIDTH, self.height())

        self._buttons: dict[str, QPushButton] = {}
        self._labels: dict[str, str] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._expanded = False
        self._animation = QPropertyAnimation(self, b"geometry", self)
        self._animation.setDuration(ANIMATION_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # The current page's pill: one coloured shape that glides between buttons.
        self._indicator = QFrame(self)
        self._indicator.setObjectName("NavIndicator")
        self._indicator.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._indicator.hide()
        self._indicator_animation = QPropertyAnimation(self._indicator, b"geometry", self)
        self._indicator_animation.setDuration(INDICATOR_MS)
        self._indicator_animation.setEasingCurve(QEasingCurve.Type.OutBack)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, Spacing.MD, 18, Spacing.MD)
        layout.setSpacing(4)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(14)
        mark = QLabel("M")
        mark.setObjectName("BrandMark")
        mark.setFixedSize(BRAND_SIZE, BRAND_SIZE)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setAccessibleName(APP_NAME)
        brand_row.addWidget(mark)
        self._brand_text = QWidget()
        brand_text = QVBoxLayout(self._brand_text)
        brand_text.setContentsMargins(0, 0, 0, 0)
        brand_text.setSpacing(0)
        brand_text.addWidget(self._label(APP_NAME, "SidebarBrand"))
        brand_text.addWidget(self._label("Personal finance, kept local", "SidebarTagline"))
        brand_row.addWidget(self._brand_text, 1)
        layout.addLayout(brand_row)
        layout.addSpacing(14)

        for item in items:
            layout.addWidget(self._create_button(item))
        layout.addStretch(1)
        layout.addLayout(self._footer())

        self._show_labels(False)

    # ------------------------------------------------------------ navigation

    def keys(self) -> list[str]:
        return list(self._buttons)

    def button(self, key: str) -> QPushButton:
        return self._buttons[key]

    def current_key(self) -> str | None:
        for key, button in self._buttons.items():
            if button.isChecked():
                return key
        return None

    def set_current(self, key: str) -> None:
        self._buttons[key].setChecked(True)
        set_style_property(self._indicator, "fill", page_fill(key))
        self._place_indicator(animated=self._indicator.isVisible())

    def _place_indicator(self, *, animated: bool) -> None:
        key = self.current_key()
        if key is None or not self.isVisible():
            return
        target = self._buttons[key].geometry()
        self._indicator_animation.stop()
        if animated and motion.enabled():
            self._indicator_animation.setStartValue(self._indicator.geometry())
            self._indicator_animation.setEndValue(target)
            self._indicator_animation.start()
        else:
            self._indicator.setGeometry(target)
        self._indicator.show()
        self._indicator.lower()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._place_indicator(animated=False)  # buttons widen and narrow with the rail

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        QTimer.singleShot(0, self, lambda: self._place_indicator(animated=False))

    # ------------------------------------------------------------ expansion

    @property
    def expanded(self) -> bool:
        return self._expanded

    def place(self, height: int) -> None:
        """Keep the rail at the left edge, full height, at its current width."""
        self._animation.stop()
        self.setGeometry(0, 0, EXPANDED_WIDTH if self._expanded else RAIL_WIDTH, height)
        if not self._expanded:
            self._show_labels(False)
        self.raise_()

    def set_expanded(self, expanded: bool) -> None:
        if expanded == self._expanded:
            return
        self._expanded = expanded
        self._show_labels(expanded)  # labels appear and go at once, never clipped mid-slide
        self._animation.stop()
        self._animation.setStartValue(self.geometry())
        self._animation.setEndValue(
            QRect(0, 0, EXPANDED_WIDTH if expanded else RAIL_WIDTH, self.height()))
        self.raise_()
        self._animation.start()

    def enterEvent(self, event: QEnterEvent) -> None:  # noqa: N802
        self.set_expanded(True)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # noqa: N802
        if not self._has_focus_inside():
            self.set_expanded(False)
        super().leaveEvent(event)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        """Open when a button is reached with the keyboard; close when focus leaves."""
        if isinstance(event, QFocusEvent):
            if event.type() == QEvent.Type.FocusIn and event.reason() in KEYBOARD_FOCUS:
                self.set_expanded(True)
            elif event.type() == QEvent.Type.FocusOut:
                QTimer.singleShot(0, self, self._collapse_unless_used)
        return False  # observe only; the button handles the event as usual

    def _collapse_unless_used(self) -> None:
        if not self.underMouse() and not self._has_focus_inside():
            self.set_expanded(False)

    def _has_focus_inside(self) -> bool:
        focused = QApplication.focusWidget()
        return focused is not None and self.isAncestorOf(focused)

    def _show_labels(self, visible: bool) -> None:
        self._brand_text.setVisible(visible)
        self._status_label.setVisible(visible)
        for key, button in self._buttons.items():
            button.setText(self._labels[key] if visible else "")

    # ------------------------------------------------------------ building

    def _create_button(self, item: NavItem) -> QPushButton:
        if item.key in self._buttons:
            raise ValueError(f"Duplicate navigation key: {item.key!r}")

        button = QPushButton(item.label)
        button.setObjectName("NavButton")
        button.setProperty("page", item.key)
        button.setAccessibleName(item.label)
        button.setCheckable(True)
        # Keyboard focus only: a click must not leave focus (and the rail open) here.
        button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        button.installEventFilter(self)
        button.setFixedHeight(BUTTON_HEIGHT)
        button.setIcon(nav_icon(item.key))
        button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda _checked=False, key=item.key: self.page_selected.emit(key))

        self._group.addButton(button)
        self._buttons[item.key] = button
        self._labels[item.key] = item.label
        return button

    def _footer(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(21, 0, 0, 0)
        row.setSpacing(Spacing.SM)
        dot = QLabel()
        dot.setPixmap(dot_pixmap(Colors.MINT))
        dot.setToolTip(f"Offline · stored on this computer · version {__version__}")
        row.addWidget(dot)
        self._status_label = self._label("Offline · stored on this PC", "SidebarFooter")
        self._status_label.setToolTip(f"Version {__version__}")
        row.addWidget(self._status_label, 1)
        return row

    @staticmethod
    def _label(text: str, object_name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        return label
