from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QFont, QPixmap, QResizeEvent
from PySide6.QtWidgets import QBoxLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from money_manager.ui.components.flow import FlowRow
from money_manager.ui.theme import Colors, Spacing


def diamond_pixmap(colour: str, size: int = 10, scale: int = 2) -> QPixmap:
    """The page's colour mark: a small rounded square turned 45°."""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size * scale}" '
           f'height="{size * scale}" viewBox="0 0 14 14"><rect x="3" y="3" width="8" '
           f'height="8" rx="2" transform="rotate(45 7 7)" fill="{colour}"/></svg>')
    pixmap = QPixmap()
    pixmap.loadFromData(QByteArray(svg.encode()), "SVG")
    pixmap.setDevicePixelRatio(scale)
    return pixmap


class PageHeader(QWidget):
    """The page's colour mark and one-line description above its title, with the
    page's own actions on the right (``add_action``) followed by the window-wide
    controls (``attach``). When the window is too narrow for one row, the actions
    move under the title and wrap."""

    def __init__(self, title: str, subtitle: str, parent: QWidget | None = None, *,
                 color: str = Colors.ACCENT) -> None:
        super().__init__(parent)

        self.mark = QLabel()
        self.mark.setPixmap(diamond_pixmap(color))
        self.mark.setFixedWidth(12)
        self.mark.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.mark.setContentsMargins(0, 3, 0, 0)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("PageKicker")
        self.subtitle_label.setWordWrap(True)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("PageTitle")
        self.title_label.setAccessibleName(title)
        font = self.title_label.font()
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 98)
        self.title_label.setFont(font)

        kicker = QHBoxLayout()
        kicker.setContentsMargins(0, 0, 0, 0)
        kicker.setSpacing(Spacing.SM)
        kicker.addWidget(self.mark)
        kicker.addWidget(self.subtitle_label, 1)

        self._text = QWidget()
        text = QVBoxLayout(self._text)
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(6)
        text.addLayout(kicker)
        text.addWidget(self.title_label)

        self.actions = FlowRow(spacing=Spacing.SM)

        self._row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(Spacing.MD)
        self._row.addWidget(self._text, 1)
        self._row.addWidget(self.actions, 0, Qt.AlignmentFlag.AlignBottom)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, Spacing.XS)
        layout.addLayout(self._row)

    def add_action(self, widget: QWidget) -> None:
        self.actions.add(widget)
        self._relayout(self.width())

    def attach(self, widget: QWidget) -> None:
        """Show a window-wide control (search, Ask AI, New entry) after the page's actions."""
        self.actions.add(widget)
        widget.show()
        self._relayout(self.width())

    def detach(self, widget: QWidget) -> None:
        self.actions.flow.removeWidget(widget)
        self._relayout(self.width())

    @property
    def stacked(self) -> bool:
        return self._row.direction() == QBoxLayout.Direction.TopToBottom

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        self._relayout(event.size().width())
        super().resizeEvent(event)

    def _relayout(self, width: int) -> None:
        needed = (self.title_label.sizeHint().width() + self._row.spacing()
                  + self.actions.sizeHint().width())
        stacked = width < needed
        if stacked == self.stacked:
            return
        self._row.setDirection(QBoxLayout.Direction.TopToBottom if stacked
                               else QBoxLayout.Direction.LeftToRight)
        self._row.setAlignment(self.actions, Qt.AlignmentFlag.AlignLeft if stacked
                               else Qt.AlignmentFlag.AlignBottom)
        self.updateGeometry()
