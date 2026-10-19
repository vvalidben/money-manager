from PySide6.QtCore import QAbstractAnimation, Signal
from PySide6.QtWidgets import QLineEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget

from money_manager.ui import motion
from money_manager.ui.components import Card, PageHeader, StatCard
from money_manager.ui.components.progress_ring import ProgressRing
from money_manager.ui.pages.registry import PageSpec
from money_manager.ui.theme import Spacing, page_color


class BasePage(QWidget):
    """Common page layout: header on top, content below.

    With ``fill=False`` free space collects at the bottom; with ``fill=True``
    content added with a stretch (e.g. a table) grows to fill the page.
    Emit ``navigate_requested(page_key)`` to ask the main window to switch pages.
    """

    navigate_requested = Signal(str)
    # (title, detail): a short confirmation the window shows briefly, e.g. "Entry added".
    notice = Signal(str, str)
    # Set by pages: Ctrl+N clicks the primary button, Ctrl+F focuses the search field.
    primary_button: QPushButton | None = None
    search_field: QLineEdit | None = None

    def __init__(self, spec: PageSpec, parent: QWidget | None = None, *, fill: bool = False) -> None:
        super().__init__(parent)
        self._spec = spec
        self._entrance: QAbstractAnimation | None = None
        self.header = PageHeader(spec.title, spec.subtitle, color=page_color(spec.key))

        self._content = QVBoxLayout()
        self._content.setSpacing(Spacing.MD)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        layout.setSpacing(Spacing.LG)
        layout.addWidget(self.header)
        layout.addLayout(self._content, 1 if fill else 0)
        if not fill:
            layout.addStretch(1)

    @property
    def spec(self) -> PageSpec:
        return self._spec

    def add_content(self, widget: QWidget, stretch: int = 0) -> None:
        self._content.addWidget(widget, stretch)

    def on_shown(self) -> None:
        """Called each time the page becomes visible; refresh data here."""

    def play_entrance(self) -> None:
        """Bring the page in: tiles rise one after another, figures count up,
        bars and rings fill. Does nothing when motion is off."""
        if not motion.enabled() or not self.isVisible():
            return
        motion.finish(self._entrance)
        tiles = [self.header, *motion.top_level_tiles(self, (Card,))]
        self._entrance = motion.entrance(tiles, self)
        for figure in self.findChildren(StatCard):
            if figure.isVisible():
                figure.count_up()
        motion.fill((bar for bar in self.findChildren(QProgressBar) if bar.isVisible()), self)
        for ring in self.findChildren(ProgressRing):
            if ring.isVisible():
                ring.sweep_in()

    def trigger_primary(self) -> bool:
        button = self.primary_button
        if button is None or not button.isVisible() or not button.isEnabled():
            return False
        button.click()
        return True

    def focus_search(self) -> bool:
        field = self.search_field
        if field is None or not field.isVisible():
            return False
        field.setFocus()
        field.selectAll()
        return True

    def force_refresh(self) -> None:
        """Recalculate even if nothing seems to have changed (F5)."""
        self._shown_state = None
        self.on_shown()

    def already_current(self, state: object) -> bool:
        """True when the page was last refreshed for this ``state`` (typically
        ``AppServices.freshness()``); otherwise remembers it and returns False."""
        if getattr(self, "_shown_state", None) == state:
            return True
        self._shown_state = state
        return False
