"""Qt table model over already-formatted transaction rows.

Sorting is not done here: ``sort()`` only reports the requested order so the
page can ask the service for a correctly sorted (and paginated) result.
"""

from collections.abc import Sequence
from enum import IntEnum
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt, Signal
from PySide6.QtGui import QColor, QFont

from money_manager.domain.entities import Transaction
from money_manager.domain.enums import TransactionSort
from money_manager.ui.theme import Colors, mono_font
from money_manager.ui.transactions.rows import NO_DESCRIPTION, TransactionRow

ModelIndex = QModelIndex | QPersistentModelIndex


class Column(IntEnum):
    DATE = 0
    DESCRIPTION = 1
    CATEGORY = 2
    TYPE = 3
    AMOUNT = 4


HEADERS = {
    Column.DATE: "Date",
    Column.DESCRIPTION: "Description",
    Column.CATEGORY: "Category",
    Column.TYPE: "Type",
    Column.AMOUNT: "Amount",
}
SORT_KEYS = {
    Column.DATE: TransactionSort.DATE,
    Column.DESCRIPTION: TransactionSort.DESCRIPTION,
    Column.CATEGORY: TransactionSort.CATEGORY,
    Column.TYPE: TransactionSort.TYPE,
    Column.AMOUNT: TransactionSort.AMOUNT,
}


class TransactionTableModel(QAbstractTableModel):
    sort_requested = Signal(object, bool)  # (TransactionSort, descending)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._rows: list[TransactionRow] = []
        self._amount_font = mono_font()  # figures face, as in the design
        self._amount_font.setWeight(QFont.Weight.Medium)

    def set_rows(self, rows: Sequence[TransactionRow]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def row_at(self, row: int) -> TransactionRow:
        return self._rows[row]

    def transaction_at(self, row: int) -> Transaction:
        return self._rows[row].transaction

    def row_of(self, transaction_id: int) -> int | None:
        for index, row in enumerate(self._rows):
            if row.transaction.id == transaction_id:
                return index
        return None

    def rowCount(self, parent: ModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: ModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(Column)

    def headerData(  # noqa: N802
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if orientation != Qt.Orientation.Horizontal:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return HEADERS[Column(section)]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return _alignment(Column(section))
        return None

    def data(self, index: ModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        column = Column(index.column())
        match role:
            case Qt.ItemDataRole.DisplayRole:
                return _display(row, column)
            case Qt.ItemDataRole.ForegroundRole:
                if column in (Column.TYPE, Column.AMOUNT):
                    return QColor(Colors.INFLOW if row.is_inflow else Colors.OUTFLOW)
                if column is Column.DESCRIPTION and row.description == NO_DESCRIPTION:
                    return QColor(Colors.TEXT_MUTED)
            case Qt.ItemDataRole.FontRole if column is Column.AMOUNT:
                return self._amount_font
            case Qt.ItemDataRole.TextAlignmentRole:
                return _alignment(column)
            case Qt.ItemDataRole.ToolTipRole:
                return row.tooltip or None
            case Qt.ItemDataRole.UserRole:
                return row.transaction
        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        self.sort_requested.emit(
            SORT_KEYS[Column(column)], order == Qt.SortOrder.DescendingOrder
        )


def _display(row: TransactionRow, column: Column) -> str:
    match column:
        case Column.DATE:
            return row.date
        case Column.DESCRIPTION:
            return row.description
        case Column.CATEGORY:
            return row.category
        case Column.TYPE:
            return row.type
        case Column.AMOUNT:
            return row.amount


def _alignment(column: Column) -> Qt.AlignmentFlag:
    horizontal = Qt.AlignmentFlag.AlignRight if column is Column.AMOUNT else Qt.AlignmentFlag.AlignLeft
    return horizontal | Qt.AlignmentFlag.AlignVCenter
