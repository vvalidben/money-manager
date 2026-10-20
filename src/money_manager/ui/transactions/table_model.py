"""Qt table model over already-formatted transaction rows.

Sorting is not done here: ``sort()`` only reports the requested order so the
page can ask the service for a correctly sorted (and paginated) result.
"""

from collections.abc import Sequence
from enum import IntEnum
from functools import lru_cache
from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap

from money_manager.domain.entities import Transaction
from money_manager.domain.enums import TransactionSort
from money_manager.ui.theme import FONT_FAMILY, Colors, identity_color, mono_font
from money_manager.ui.transactions.rows import NO_DESCRIPTION, TransactionRow
from money_manager.core.i18n import tr

ModelIndex = QModelIndex | QPersistentModelIndex


class Column(IntEnum):
    DATE = 0
    DESCRIPTION = 1
    CATEGORY = 2
    TYPE = 3
    AMOUNT = 4


HEADERS = {
    Column.DATE: tr("Date"),
    Column.DESCRIPTION: tr("Description"),
    Column.CATEGORY: tr("Category"),
    Column.TYPE: tr("Type"),
    Column.AMOUNT: tr("Amount"),
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
            case Qt.ItemDataRole.DecorationRole if column is Column.DESCRIPTION:
                return category_badge(_initial(row), identity_color(row.transaction.category_id))
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


BADGE_SIZE = 24


def _initial(row: TransactionRow) -> str:
    text = row.description if row.description != NO_DESCRIPTION else row.category
    return next((char.upper() for char in text if char.isalnum()), "·")


@lru_cache(maxsize=512)
def category_badge(letter: str, color: str, size: int = BADGE_SIZE, scale: int = 2) -> QPixmap:
    """A rounded square in the category's colour with the entry's initial (cached)."""
    pixmap = QPixmap(size * scale, size * scale)
    pixmap.setDevicePixelRatio(scale)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawRoundedRect(QRectF(0, 0, size, size), 7, 7)
    font = QFont(FONT_FAMILY)
    font.setPixelSize(size // 2)
    font.setWeight(QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(Colors.ON_ACCENT))
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, letter)
    painter.end()
    return pixmap


def _alignment(column: Column) -> Qt.AlignmentFlag:
    horizontal = Qt.AlignmentFlag.AlignRight if column is Column.AMOUNT else Qt.AlignmentFlag.AlignLeft
    return horizontal | Qt.AlignmentFlag.AlignVCenter
