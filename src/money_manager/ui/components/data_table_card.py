from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QWidget

from money_manager.ui.components.card import Card
from money_manager.ui.theme import Spacing

ROW_HEIGHT = 32
MAX_VISIBLE_ROWS = 12


class DataTableCard(Card):
    """A titled, read-only table that grows with its rows (up to a limit)."""

    def __init__(
        self, title: str, subtitle: str = "", parent: QWidget | None = None, *,
        selectable: bool = False,
    ) -> None:
        super().__init__(title, parent)
        self.body.setSpacing(Spacing.XS)
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("MutedLabel")
        self.subtitle_label.setWordWrap(True)
        self.body.addWidget(self.subtitle_label)

        self.table = QTableWidget()
        self.table.setObjectName("DataTable")
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        if selectable:
            self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        else:
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
            self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setHighlightSections(False)  # no bold header for the selected row
        self.table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        self.body.addWidget(self.table)

        self.empty_label = QLabel()
        self.empty_label.setObjectName("MutedLabel")
        self.body.addWidget(self.empty_label)

    def set_rows(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        empty_text: str = "",
        *,
        text_columns: int = 1,
    ) -> None:
        """The first ``text_columns`` columns are left-aligned text; the rest are figures."""
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setRowCount(len(rows))

        def alignment(column: int) -> Qt.AlignmentFlag:
            side = Qt.AlignmentFlag.AlignLeft if column < text_columns else Qt.AlignmentFlag.AlignRight
            return side | Qt.AlignmentFlag.AlignVCenter

        for column, title in enumerate(headers):
            header_item = QTableWidgetItem(title)
            header_item.setTextAlignment(alignment(column))
            self.table.setHorizontalHeaderItem(column, header_item)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for row_index, row in enumerate(rows):
            for column, text in enumerate(row):
                item = QTableWidgetItem(text)
                item.setTextAlignment(alignment(column))
                self.table.setItem(row_index, column, item)
        visible = min(len(rows), MAX_VISIBLE_ROWS)
        self.table.setFixedHeight(header.sizeHint().height() + visible * ROW_HEIGHT + 4)
        self.table.setVisible(bool(rows))
        self.empty_label.setText(empty_text)
        self.empty_label.setVisible(not rows and bool(empty_text))

    def selected_row(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def cell(self, row: int, column: int) -> str:
        item = self.table.item(row, column)
        return item.text() if item is not None else ""
