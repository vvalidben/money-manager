"""Investments page: portfolio summary, holdings, and the selected holding's history.

All figures come from ``InvestmentService`` (no market data, no advice).
"""

import logging
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError
from money_manager.domain.investments import (
    EntryKind,
    InvestmentEntry,
    InvestmentPosition,
    PortfolioSummary,
    Valuation,
)
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.charts.analysis import CategoryShareChart, category_share_table
from money_manager.ui.charts.base import ChartCard
from money_manager.ui.components import AdaptiveRow, FlowRow, Card, EmptyState, ResponsiveRow, StatCard
from money_manager.ui.components.data_table_card import DataTableCard
from money_manager.ui.investments.dialogs import EntryDialog, InvestmentDialog, ValueDialog
from money_manager.ui.investments.view_model import (
    ENTRY_HEADERS,
    HOLDING_HEADERS,
    KIND_IDS,
    KIND_TEXT,
    VALUE_HEADERS,
    entry_row,
    holding_row,
    position_status,
    summary_stats,
    value_by_kind,
    value_row,
)
from money_manager.ui.pages.base_page import BasePage
from money_manager.ui.pages.registry import PageSpec
from money_manager.ui.theme import SIDE_BY_SIDE_MIN_WIDTH, Spacing
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

TEXT_COLUMNS = 2  # name and type; the rest are figures
ROW_HEIGHT = 34


class InvestmentsPage(BasePage):
    def __init__(self, spec: PageSpec, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(spec, parent, fill=True)
        self._services = services
        self.summary: PortfolioSummary | None = None
        self.positions: list[InvestmentPosition] = []
        self._selected_id: int | None = None
        self._entries: list[InvestmentEntry] = []
        self._valuations: list[Valuation] = []

        self.new_button = QPushButton(tr("New investment"))
        self.new_button.setObjectName("PrimaryButton")
        self.new_button.clicked.connect(self.create_investment)
        self.new_button.setToolTip(tr("New investment (Ctrl+N)"))
        self.header.add_action(self.new_button)
        self.primary_button = self.new_button

        self.stat_cards = tuple(StatCard("", compact=True) for _ in range(4))
        self.stats_row = ResponsiveRow(self.stat_cards, min_item_width=200)

        # Holdings
        self.holdings_card = Card(tr("Holdings"))
        self.table = QTableWidget()
        self.table.setObjectName("DataTable")
        self.table.setColumnCount(len(HOLDING_HEADERS))
        for column, title in enumerate(HOLDING_HEADERS):
            header_item = QTableWidgetItem(title)
            header_item.setTextAlignment(_alignment(column))
            self.table.setHorizontalHeaderItem(column, header_item)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setHighlightSections(False)  # no bold header for the selected row
        self.table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # name takes the rest
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.doubleClicked.connect(lambda _index: self.edit_selected())
        self.show_archived = QPushButton(tr("Show archived"))
        self.show_archived.setCheckable(True)
        self.show_archived.toggled.connect(lambda _checked: self.refresh())
        holdings_actions = QHBoxLayout()
        holdings_actions.addStretch(1)
        holdings_actions.addWidget(self.show_archived)
        self.holdings_card.body.addWidget(self.table)
        self.holdings_card.body.addLayout(holdings_actions)

        self.kind_card = ChartCard(tr("Value by type"), tr("Latest known values"),
                                   CategoryShareChart(center_label="value"))

        # Selected holding
        self.detail_card = Card()
        self.detail_title = QLabel()
        self.detail_title.setObjectName("CardHeading")
        self.detail_status = QLabel()
        self.detail_status.setObjectName("MutedLabel")
        self.detail_status.setWordWrap(True)
        self.detail_notes = QLabel()
        self.detail_notes.setObjectName("CardBody")
        self.detail_notes.setWordWrap(True)
        self.contribute_button = self._button(tr("Add contribution"), self.add_contribution, True)
        self.withdraw_button = self._button(tr("Withdraw"), self.add_withdrawal)
        self.value_button = self._button(tr("Update value"), self.update_value)
        self.edit_button = self._button(tr("Edit"), self.edit_selected)
        self.archive_button = self._button(tr("Archive"), self.toggle_archived)
        self.delete_button = self._button(tr("Delete"), self.delete_selected)
        self.delete_button.setObjectName("DangerButton")
        # Two groups that wrap as units on narrow windows.
        detail_actions = FlowRow([
            _group(self.contribute_button, self.withdraw_button, self.value_button),
            _group(self.edit_button, self.archive_button, self.delete_button),
        ])
        self.detail_card.body.addWidget(self.detail_title)
        self.detail_card.body.addWidget(self.detail_notes)
        self.detail_card.body.addWidget(self.detail_status)
        self.detail_card.body.addWidget(detail_actions)

        self.entries_card = DataTableCard(
            tr("Contributions & withdrawals"),
            tr("Deleting a contribution paid from your accounts also deletes its expense."),
            selectable=True,
        )
        self.delete_entry_button = self._button(tr("Delete selected"), self.delete_selected_entry)
        self.entries_card.body.addWidget(self.delete_entry_button, 0, Qt.AlignmentFlag.AlignRight)
        self.values_card = DataTableCard(tr("Value history"), selectable=True)
        self.delete_value_button = self._button(tr("Delete selected"), self.delete_selected_value)
        self.values_card.body.addWidget(self.delete_value_button, 0, Qt.AlignmentFlag.AlignRight)

        self.empty_state = EmptyState(
            tr("No investments yet"),
            tr("Track stocks, ETFs, crypto, gold or anything else: record what you put in and, "
            "from time to time, what it is worth. Profit and return appear once a value is "
            "entered."),
            badge=None,
            action_text=tr("Add investment"),
        )
        self.empty_state.action_clicked.connect(self.create_investment)

        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.MD)
        grid.setVerticalSpacing(Spacing.MD)
        grid.addWidget(self.stats_row, 0, 0, 1, 12)
        grid.addWidget(self.holdings_card, 1, 0, 1, 12)
        details = QWidget()
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(Spacing.MD)
        for card in (self.detail_card, self.entries_card, self.values_card):
            details_layout.addWidget(card)
        details_layout.addStretch(1)
        self.details_row = AdaptiveRow([(details, 8), (self.kind_card, 4)], SIDE_BY_SIDE_MIN_WIDTH,
                                       align_top=True)
        grid.addWidget(self.details_row, 2, 0, 1, 12)
        for column in range(12):
            grid.setColumnStretch(column, 1)
        self._grid_widgets = [self.stats_row, self.holdings_card, self.kind_card, self.detail_card,
                              self.entries_card, self.values_card]

        content = QWidget()
        content.setObjectName("TransparentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, Spacing.SM, 0)
        content_layout.addWidget(self.empty_state)
        content_layout.addLayout(grid)
        content_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)

        self.add_content(scroll, stretch=1)

    # ------------------------------------------------------------ loading

    def on_shown(self) -> None:
        # Nothing changed since the page was last shown: keep what is on screen.
        if self.already_current(self._services.freshness()):
            return
        self.refresh()

    def refresh(self) -> None:
        try:
            summary = self._services.investments.summary()
            everything = self._services.investments.list(include_archived=True)
        except MoneyManagerError as exc:
            logger.warning("Could not load investments: %s", exc)
            dialogs.show_warning(self, tr("Could not load investments"), str(exc))
            return
        self.summary = summary
        show_archived = self.show_archived.isChecked()
        self.positions = [p for p in everything if show_archived or not p.investment.is_archived]
        # Archived-only holdings still count: the list must stay reachable to restore them.
        has_any = bool(everything)
        self.empty_state.setVisible(not has_any)
        self.new_button.setVisible(has_any)  # the empty state has its own button
        for widget in self._grid_widgets:
            widget.setVisible(has_any)
        if not has_any:
            return

        for card, stat in zip(self.stat_cards, summary_stats(summary), strict=True):
            card.label.setText(stat.label)
            card.set_value(stat.value, stat.tone)
            card.set_caption(stat.caption)
        rows = value_by_kind(summary)
        self.kind_card.chart.render(rows, list(KIND_IDS.values()))
        self.kind_card.set_table(category_share_table(rows))
        self._fill_holdings()

    def _fill_holdings(self) -> None:
        keep = self._selected_id
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.positions))
        for row, position in enumerate(self.positions):
            texts = holding_row(position)
            if position.investment.is_archived:
                texts = (texts[0] + " (archived)", *texts[1:])
            for column, text in enumerate(texts):
                item = QTableWidgetItem(text)
                item.setTextAlignment(_alignment(column))
                self.table.setItem(row, column, item)
        self.table.setFixedHeight(self.table.horizontalHeader().sizeHint().height()
                                  + max(len(self.positions), 1) * ROW_HEIGHT + 4)
        self.table.blockSignals(False)
        ids = [p.investment.id for p in self.positions]
        row = ids.index(keep) if keep in ids else (0 if ids else None)
        if row is not None:
            self.table.selectRow(row)
        self._on_selection_changed()

    # ------------------------------------------------------------ selection

    def selected(self) -> InvestmentPosition | None:
        rows = self.table.selectionModel().selectedRows()
        return self.positions[rows[0].row()] if rows else None

    def select(self, investment_id: int) -> None:
        for row, position in enumerate(self.positions):
            if position.investment.id == investment_id:
                self.table.selectRow(row)

    def _on_selection_changed(self) -> None:
        position = self.selected()
        self._selected_id = position.investment.id if position else None
        for widget in (self.detail_card, self.entries_card, self.values_card):
            widget.setVisible(position is not None)
        if position is None:
            return
        investment = position.investment
        self.detail_title.setText(f"{investment.name} · {KIND_TEXT[investment.kind]}")
        self.detail_notes.setText(investment.notes)
        self.detail_notes.setVisible(bool(investment.notes))
        self.detail_status.setText(position_status(position))
        active = not investment.is_archived
        for button in (self.contribute_button, self.withdraw_button, self.value_button):
            button.setEnabled(active)
        self.archive_button.setText(tr("Archive") if active else tr("Restore"))
        entries = list(reversed(position.entries))  # newest first
        self._entries = entries
        self.entries_card.set_rows(ENTRY_HEADERS, [entry_row(e) for e in entries],
                                   tr("No contributions yet."), text_columns=4)
        valuations = sorted(position.valuations, key=lambda v: (v.valued_on, v.id), reverse=True)
        self._valuations = valuations
        self.values_card.set_rows(VALUE_HEADERS, [value_row(v) for v in valuations],
                                  tr("No value entered yet."))
        self.delete_entry_button.setVisible(bool(entries))
        self.delete_value_button.setVisible(bool(valuations))

    # ------------------------------------------------------------ actions

    def create_investment(self) -> None:
        dialog = InvestmentDialog(self._services, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved is not None:
            self._selected_id = dialog.saved.investment.id
            self.refresh()

    def edit_selected(self) -> None:
        position = self.selected()
        if position is not None:
            self._exec(InvestmentDialog(self._services, position=position, parent=self))

    def add_contribution(self) -> None:
        position = self.selected()
        if position is not None:
            self._exec(EntryDialog(self._services, position, EntryKind.CONTRIBUTION, parent=self))

    def add_withdrawal(self) -> None:
        position = self.selected()
        if position is not None:
            self._exec(EntryDialog(self._services, position, EntryKind.WITHDRAWAL, parent=self))

    def update_value(self) -> None:
        position = self.selected()
        if position is not None:
            self._exec(ValueDialog(self._services, position, parent=self))

    def toggle_archived(self) -> None:
        position = self.selected()
        if position is None:
            return
        archive = not position.investment.is_archived
        self._run(lambda: self._services.investments.set_archived(position.investment.id, archive))

    def delete_selected(self) -> None:
        position = self.selected()
        if position is None:
            return
        if dialogs.confirm_destructive(
            self, tr("Delete investment"),
            tr("Delete “{0}” and its history? Expenses already recorded for its "
               "contributions stay in your transactions.", position.investment.name),
        ):
            self._selected_id = None
            self._run(lambda: self._services.investments.delete(position.investment.id))

    def delete_selected_entry(self) -> None:
        row = self.entries_card.selected_row()
        if row is None:
            return
        entry = self._entries[row]
        extra = (tr(" Its expense will be deleted too and your balance recalculated.")
                 if entry.transaction_id is not None else "")
        if dialogs.confirm_destructive(self, tr("Delete entry"),
                                       tr("Delete this {0}?{1}", tr(entry.kind.value), extra)):
            self._run(lambda: self._services.investments.delete_entry(entry.id))

    def delete_selected_value(self) -> None:
        row = self.values_card.selected_row()
        if row is None:
            return
        valuation = self._valuations[row]
        if dialogs.confirm_destructive(self, tr("Delete value"), tr("Delete this value?")):
            self._run(lambda: self._services.investments.delete_valuation(valuation.id))

    def _exec(self, dialog: QDialog) -> None:
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _run(self, action: Callable[[], object]) -> None:
        try:
            action()
        except MoneyManagerError as exc:
            dialogs.show_warning(self, tr("Could not update the investment"), str(exc))
        self.refresh()

    @staticmethod
    def _button(text: str, handler: Callable[[], None], primary: bool = False) -> QPushButton:
        button = QPushButton(text)
        if primary:
            button.setObjectName("PrimaryButton")
        button.clicked.connect(lambda _checked=False: handler())
        return button


def _alignment(column: int) -> Qt.AlignmentFlag:
    side = Qt.AlignmentFlag.AlignLeft if column < TEXT_COLUMNS else Qt.AlignmentFlag.AlignRight
    return side | Qt.AlignmentFlag.AlignVCenter


def _group(*buttons: QPushButton) -> QWidget:
    box = QWidget()
    layout = QHBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(Spacing.SM)
    for button in buttons:
        layout.addWidget(button)
    return box

