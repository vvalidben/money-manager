"""Dashboard cards: allocation overview, financial health, recent transactions,
renewals."""

from collections.abc import Sequence
from decimal import Decimal

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from money_manager.ui.components.card import Card
from money_manager.ui.dashboard.view_model import AllocationRowView, HealthRowView, RenewalView
from money_manager.ui.goals.view_model import GoalCardView
from money_manager.ui.theme import Spacing, set_style_property
from money_manager.ui.transactions.rows import TransactionRow
from money_manager.ui.transactions.table_model import BADGE_SIZE, Column, TransactionTableModel
from money_manager.core.i18n import tr

ROW_HEIGHT = 40
SHARE_BAR_STEPS = 1000


def _label(text: str, object_name: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    return label


def _clear(layout: QGridLayout) -> None:
    """Remove every widget immediately (deleteLater alone leaves them visible a moment)."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget() if item is not None else None
        if widget is not None:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()


class _CardHeader(QWidget):
    def __init__(self, title: str, action_text: str | None = None) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_label(title, "CardHeading"))
        layout.addStretch(1)
        self.action_button: QPushButton | None = None
        if action_text:
            self.action_button = QPushButton(action_text)
            layout.addWidget(self.action_button)


class AllocationOverview(Card):
    """Each allocation and Available, with its amount and share of the balance."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.body.addWidget(_CardHeader(tr("Money organisation")))
        self.body.addWidget(_label(tr("How your total balance is allocated"), "MutedLabel"))
        self._grid = QGridLayout()
        self._grid.setHorizontalSpacing(Spacing.MD)
        self._grid.setVerticalSpacing(Spacing.SM)
        self._grid.setColumnStretch(0, 1)
        self.body.addLayout(self._grid)
        self.note_label = _label("", "MutedLabel")
        self.note_label.setWordWrap(True)
        self.body.addWidget(self.note_label)
        self.body.addStretch(1)
        self.rows: tuple[AllocationRowView, ...] = ()

    def set_rows(self, rows: Sequence[AllocationRowView], note: str | None) -> None:
        self.rows = tuple(rows)
        _clear(self._grid)
        for index, row in enumerate(rows):
            grid_row = index * 2
            name = _label(row.name, "AllocationAvailable" if row.is_available else "AllocationName")
            amount = _label(row.amount, "AllocationAmount")
            set_style_property(amount, "tone", "outflow" if row.is_negative else "neutral")
            amount.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            share = _label(row.share, "MutedLabel")
            share.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            share.setMinimumWidth(48)
            self._grid.addWidget(name, grid_row, 0)
            self._grid.addWidget(amount, grid_row, 1)
            self._grid.addWidget(share, grid_row, 2)
            self._grid.addWidget(_share_bar(row.bar_fraction, row.is_available), grid_row + 1, 0, 1, 3)
        self.note_label.setText(note or "")
        self.note_label.setVisible(bool(note))


def _share_bar(fraction: Decimal, is_available: bool) -> QProgressBar:
    bar = QProgressBar()
    bar.setObjectName("ShareBarAvailable" if is_available else "ShareBar")
    bar.setTextVisible(False)
    bar.setFixedHeight(6)
    bar.setRange(0, SHARE_BAR_STEPS)
    bar.setValue(int(fraction * SHARE_BAR_STEPS))  # drawing only
    return bar


class HealthCard(Card):
    """Basic financial-health metrics, each with a text + symbol level badge."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.body.addWidget(_CardHeader(tr("Financial health")))
        self.body.addWidget(_label(tr("Simple indicators based on your own data"), "MutedLabel"))
        self._grid = QGridLayout()
        self._grid.setHorizontalSpacing(Spacing.MD)
        self._grid.setVerticalSpacing(2)
        self._grid.setColumnStretch(0, 1)
        self.body.addLayout(self._grid)
        self.body.addStretch(1)
        self.rows: tuple[HealthRowView, ...] = ()

    def set_rows(self, rows: Sequence[HealthRowView]) -> None:
        self.rows = tuple(rows)
        _clear(self._grid)
        for index, row in enumerate(rows):
            grid_row = index * 2
            self._grid.addWidget(_label(row.label, "HealthLabel"), grid_row, 0)
            value = _label(row.value, "HealthValue")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._grid.addWidget(value, grid_row, 1)
            if row.level is not None:
                badge = _label(row.level_text, "LevelBadge")
                set_style_property(badge, "level", row.level.value)
                self._grid.addWidget(badge, grid_row, 2, Qt.AlignmentFlag.AlignRight)
            detail = _label(row.detail, "MutedLabel")
            detail.setWordWrap(True)
            detail.setContentsMargins(0, 0, 0, Spacing.SM)
            self._grid.addWidget(detail, grid_row + 1, 0, 1, 3)


class RecentTransactions(Card):
    """The latest transactions, formatted like the Transactions page."""

    view_all_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        header = _CardHeader(tr("Recent transactions"), tr("View all"))
        assert header.action_button is not None
        self.view_all_button = header.action_button
        self.view_all_button.clicked.connect(self.view_all_requested)
        self.body.addWidget(header)

        self.model = TransactionTableModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setObjectName("CompactTable")
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        self.table.setIconSize(QSize(BADGE_SIZE, BADGE_SIZE))  # category badges
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setColumnHidden(Column.TYPE, True)
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(Column.DESCRIPTION, QHeaderView.ResizeMode.Stretch)
        for column in (Column.DATE, Column.CATEGORY, Column.AMOUNT):
            header_view.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)

        self.empty_label = _label(tr("No transactions yet."), "MutedLabel")
        self.body.addWidget(self.table)
        self.body.addWidget(self.empty_label)
        self.body.addStretch(1)  # keep content at the top when the row is taller

    def set_rows(self, rows: Sequence[TransactionRow]) -> None:
        self.model.set_rows(rows)
        self.table.setFixedHeight(max(len(rows), 1) * ROW_HEIGHT + 4)
        self.table.setVisible(bool(rows))
        self.empty_label.setVisible(not rows)


DASHBOARD_GOALS = 3


class GoalsOverview(Card):
    """The most pressing goals (up to three) with their progress."""

    view_all_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        header = _CardHeader(tr("Goals"), tr("View all"))
        assert header.action_button is not None
        self.view_all_button = header.action_button
        self.view_all_button.clicked.connect(self.view_all_requested)
        self.body.addWidget(header)
        self._grid = QGridLayout()
        self._grid.setHorizontalSpacing(Spacing.LG)
        self._grid.setVerticalSpacing(Spacing.XS)
        self.body.addLayout(self._grid)
        self.empty_label = _label(
            tr("No goals yet. Create one to set money aside for something that matters."),
            "MutedLabel",
        )
        self.empty_label.setWordWrap(True)
        self.body.addWidget(self.empty_label)
        self.views: tuple[GoalCardView, ...] = ()

    def set_goals(self, views: Sequence[GoalCardView]) -> None:
        self.views = tuple(views[:DASHBOARD_GOALS])
        _clear(self._grid)
        for column, view in enumerate(self.views):
            name = _label(view.name, "AllocationAvailable")
            badge = _label(view.status_text, "LevelBadge")
            set_style_property(badge, "level", view.status_level)
            bar = QProgressBar()
            bar.setObjectName("GoalBar")
            bar.setTextVisible(False)
            bar.setFixedHeight(8)
            bar.setRange(0, SHARE_BAR_STEPS)
            bar.setValue(int(view.bar_fraction * SHARE_BAR_STEPS))  # drawing only
            self._grid.addWidget(name, 0, column)
            self._grid.addWidget(badge, 1, column, Qt.AlignmentFlag.AlignLeft)
            self._grid.addWidget(bar, 2, column)
            self._grid.addWidget(_label(f"{view.percent} · {view.amounts}", "MutedLabel"), 3, column)
            self._grid.addWidget(_label(view.deadline, "MutedLabel"), 4, column)
            self._grid.setColumnStretch(column, 1)
        self.empty_label.setVisible(not self.views)


class RenewingSoon(Card):
    """The next subscription payments on a pink tile, each with its date badge."""

    view_all_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setObjectName("RenewingTile")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.body.setSpacing(Spacing.XS)

        header = QHBoxLayout()
        header.addWidget(_label(tr("Renewing soon"), "TileHeading"))
        header.addStretch(1)
        self.view_all_button = QPushButton(tr("All subscriptions"))
        self.view_all_button.setObjectName("TilePill")
        self.view_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view_all_button.clicked.connect(self.view_all_requested)
        header.addWidget(self.view_all_button)
        self.body.addLayout(header)
        self.body.addSpacing(Spacing.XS)

        self._rows = QVBoxLayout()
        self._rows.setSpacing(0)
        self.body.addLayout(self._rows)
        self.empty_label = _label(tr("No payments due in the next 30 days."), "TileMuted")
        self.body.addWidget(self.empty_label)
        self.body.addStretch(1)
        self.rows: tuple[RenewalView, ...] = ()

    def set_rows(self, rows: Sequence[RenewalView]) -> None:
        self.rows = tuple(rows)
        while (item := self._rows.takeAt(0)) is not None:
            if item.widget() is not None:
                item.widget().deleteLater()
        for row in self.rows:
            self._rows.addWidget(self._row(row))
        self.empty_label.setVisible(not self.rows)

    @staticmethod
    def _row(view: RenewalView) -> QWidget:
        row = QWidget()
        row.setObjectName("TileRow")
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 9, 0, 9)
        layout.setSpacing(12)
        badge = _label(view.day, "DayBadge")
        badge.setFixedSize(40, 40)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(badge)
        text = QVBoxLayout()
        text.setSpacing(0)
        text.addWidget(_label(view.name, "TileText"))
        when = _label(view.when, "TileMuted")
        set_style_property(when, "overdue", view.overdue)
        text.addWidget(when)
        layout.addLayout(text, 1)
        layout.addWidget(_label(view.amount, "TileFigure"))
        row.setAccessibleName(f"{view.name}, {view.when}, {view.amount}")
        return row
