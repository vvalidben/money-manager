from collections.abc import Sequence

from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QGridLayout, QWidget

from money_manager.ui.theme import Spacing


class ResponsiveRow(QWidget):
    """Lays widgets out side by side, wrapping onto more rows when space runs out.

    The number of columns is the most that keeps every widget at least
    ``min_item_width`` wide, so the row never forces the page to overflow.
    """

    def __init__(
        self,
        widgets: Sequence[QWidget],
        min_item_width: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._widgets = list(widgets)
        self._min_item_width = min_item_width
        self._columns = 0
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(Spacing.MD)
        self._grid.setVerticalSpacing(Spacing.MD)
        self._arrange(len(self._widgets))

    @property
    def columns(self) -> int:
        return self._columns

    def columns_for(self, width: int) -> int:
        fits = (width + Spacing.MD) // (self._min_item_width + Spacing.MD)
        return max(1, min(len(self._widgets), fits))

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        columns = self.columns_for(event.size().width())
        if columns != self._columns:
            self._arrange(columns)
            self.updateGeometry()  # the height changes with the number of rows
        super().resizeEvent(event)

    def minimumSizeHint(self):  # noqa: N802, ANN201
        hint = super().minimumSizeHint()
        hint.setWidth(self._min_item_width)  # one column is always possible
        return hint

    def _arrange(self, columns: int) -> None:
        for widget in self._widgets:
            self._grid.removeWidget(widget)
        for index, widget in enumerate(self._widgets):
            self._grid.addWidget(widget, index // columns, index % columns)
        for column in range(len(self._widgets)):
            self._grid.setColumnStretch(column, 1 if column < columns else 0)
            self._grid.setColumnMinimumWidth(column, 0)
        self._columns = columns
