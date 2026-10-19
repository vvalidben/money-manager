"""Transactions page: summary figures, filters, sortable paged table, actions.

All numbers shown come from services (balances, filtered totals, counts);
the page only decides what to display.
"""

import logging
from dataclasses import replace

from PySide6.QtCore import QItemSelectionModel, QSize, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError
from money_manager.domain.entities import (
    Allocation,
    Category,
    Transaction,
    TransactionPage,
    TransactionQuery,
)
from money_manager.domain.enums import TransactionSort
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.accounts.account_dialog import AccountDialog
from money_manager.ui.components import ResponsiveRow, EmptyState, StatCard
from money_manager.ui.formatting import format_date, format_money, format_signed_money
from money_manager.ui.pages.base_page import BasePage
from money_manager.ui.pages.registry import PageSpec
from money_manager.ui.theme import Spacing
from money_manager.ui.transactions.filter_bar import FilterBar
from money_manager.ui.transactions.rows import TransactionRow, build_rows, transfer_sides
from money_manager.ui.transactions.table_model import BADGE_SIZE, Column, TransactionTableModel
from money_manager.ui.transactions.transaction_dialog import TransactionDialog
from money_manager.ui.transactions.transfer_dialog import TransferDialog

logger = logging.getLogger(__name__)

PAGE_SIZE = 50
EMPTY_STATE_INDEX = 1


class TransactionsPage(BasePage):
    def __init__(self, spec: PageSpec, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(spec, parent, fill=True)
        self._services = services
        self._query = TransactionQuery(limit=PAGE_SIZE)
        self._page: TransactionPage | None = None
        self._has_accounts = False
        self._categories: list[Category] = []
        self._allocations: list[Allocation] = []

        # Summary figures
        self.balance_card = StatCard("Total balance", compact=True)
        self.income_card = StatCard("Income in view", compact=True)
        self.expenses_card = StatCard("Expenses in view", compact=True)
        self.summary_row = ResponsiveRow(
            (self.balance_card, self.income_card, self.expenses_card), min_item_width=190)

        # Filters and primary action
        self.filter_bar = FilterBar(services.today)
        self.filter_bar.changed.connect(self._on_filters_changed)
        self.search_field = self.filter_bar.search_edit
        self.add_button = QPushButton("Add transaction")
        self.add_button.setObjectName("PrimaryButton")
        self.add_button.clicked.connect(self.add_transaction)
        self.add_button.setToolTip("Add transaction (Ctrl+N)")
        self.header.add_action(self.add_button)
        self.primary_button = self.add_button
        self.transfer_button = QPushButton("Transfer")
        self.transfer_button.setToolTip("Move money between two of your accounts")
        self.transfer_button.clicked.connect(self.transfer_between_accounts)
        self.header.add_action(self.transfer_button)
        self.new_account_button = QPushButton("New account")
        self.new_account_button.setToolTip("Add another account, e.g. cash or a card")
        self.new_account_button.clicked.connect(self.add_account)
        self.header.add_action(self.new_account_button)
        self._account_names: dict[int, str] = {}

        # Table
        self.model = TransactionTableModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setIconSize(QSize(BADGE_SIZE, BADGE_SIZE))  # category badges
        header = self.table.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionResizeMode(Column.DESCRIPTION, QHeaderView.ResizeMode.Stretch)
        for column, width in ((Column.DATE, 120), (Column.CATEGORY, 170), (Column.TYPE, 130),
                              (Column.AMOUNT, 170)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(column, width)
        header.setSortIndicator(Column.DATE, Qt.SortOrder.DescendingOrder)
        self.table.setSortingEnabled(True)  # calls model.sort once; not connected yet
        self.model.sort_requested.connect(self._on_sort_requested)
        self.table.doubleClicked.connect(lambda _index: self.edit_selected())
        self.table.selectionModel().selectionChanged.connect(self._update_actions)
        QShortcut(QKeySequence(QKeySequence.StandardKey.Delete), self.table, self.delete_selected)
        QShortcut(QKeySequence(Qt.Key.Key_Return), self.table, self.edit_selected)

        self.empty_state = EmptyState("", "", badge=None)
        self.empty_state.action_clicked.connect(self._on_empty_action)
        empty_container = QWidget()  # keeps the card compact at the top
        empty_layout = QVBoxLayout(empty_container)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.addWidget(self.empty_state)
        empty_layout.addStretch(1)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.table)
        self.stack.addWidget(empty_container)

        # Row actions and paging
        self.result_label = QLabel()
        self.result_label.setObjectName("MutedLabel")
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_selected)
        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("DangerButton")
        self.delete_button.clicked.connect(self.delete_selected)
        self.previous_button = QPushButton("‹ Previous")
        self.previous_button.clicked.connect(lambda: self._go_to_offset(-PAGE_SIZE))
        self.next_button = QPushButton("Next ›")
        self.next_button.clicked.connect(lambda: self._go_to_offset(PAGE_SIZE))
        self.footer = _hbox(
            self.result_label,
            self.edit_button,
            self.delete_button,
            self.previous_button,
            self.next_button,
            stretch_first=True,
        )

        self.add_content(self.summary_row)
        self.add_content(self.filter_bar)
        self.add_content(self.stack, stretch=1)
        self.add_content(self.footer)
        # Data is loaded in on_shown(), so a hidden page costs no queries.

    # ------------------------------------------------------------ public API

    @property
    def current_page(self) -> TransactionPage | None:
        return self._page

    @property
    def query(self) -> TransactionQuery:
        return self._query

    def on_shown(self) -> None:
        # Nothing changed since the page was last shown: keep what is on screen.
        if self.already_current(self._services.freshness()):
            return
        self.reload()

    def reload(self) -> None:
        """Refresh lookup lists, the current page of results and the summary."""
        accounts = self._services.accounts.list()
        self._has_accounts = bool(accounts)
        self._account_names = {account.id: account.name for account in accounts}
        self.transfer_button.setEnabled(len(accounts) > 1)
        self.transfer_button.setToolTip(
            "Move money between two of your accounts" if len(accounts) > 1
            else "Add a second account (New account) to transfer between them")
        self.filter_bar.set_accounts(accounts)
        self._categories = self._services.categories.list(include_archived=True)
        self.filter_bar.set_categories(self._categories)
        self._allocations = self._services.allocations.list(include_archived=True)
        self._query = replace(self._query, filters=self.filter_bar.filters())
        self._load()

    def selected_transaction(self) -> Transaction | None:
        rows = self.table.selectionModel().selectedRows()
        return self.model.transaction_at(rows[0].row()) if rows else None

    def select_transaction(self, transaction_id: int) -> None:
        row = self.model.row_of(transaction_id)
        if row is not None:
            self.table.selectionModel().select(
                self.model.index(row, 0),
                QItemSelectionModel.SelectionFlag.ClearAndSelect
                | QItemSelectionModel.SelectionFlag.Rows,
            )

    def add_transaction(self) -> None:
        if not self._has_accounts:
            self.create_account()
            return
        dialog = self.make_transaction_dialog(None)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved is not None:
            self._after_change(dialog.saved.id)
            self._announce("Entry added", dialog.saved.id)

    def selected_row(self) -> TransactionRow | None:
        rows = self.table.selectionModel().selectedRows()
        return self.model.row_at(rows[0].row()) if rows else None

    def edit_selected(self) -> None:
        transaction = self.selected_transaction()
        if transaction is None:
            return
        row = self.selected_row()
        if row is not None and row.transfer_id is not None:
            dialogs.show_info(self, "Transfers cannot be edited",
                              "This entry is one side of a transfer between your accounts. "
                              "To change it, delete the transfer and record it again.")
            return
        dialog = self.make_transaction_dialog(transaction)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved is not None:
            self._after_change(dialog.saved.id)
            self._announce("Entry updated", dialog.saved.id)

    def delete_selected(self) -> None:
        transaction = self.selected_transaction()
        if transaction is None:
            return
        row = self.model.row_at(self.table.selectionModel().selectedRows()[0].row())
        if row.transfer_id is not None:
            self._delete_transfer(row)
            return
        message = (
            f"Delete this transaction?\n\n{row.date} · {row.description} · {row.amount}\n\n"
            "Your balance will be recalculated. This cannot be undone."
        )
        if not dialogs.confirm_destructive(self, "Delete transaction", message):
            return
        try:
            self._services.transactions.delete(transaction.id)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, "Could not delete transaction", str(exc))
            return
        self._after_change(None)
        self.notice.emit("Entry deleted", f"{row.amount} · {row.description}")

    def _announce(self, title: str, transaction_id: int) -> None:
        """Confirm a change with the entry as the list shows it (if it is in view)."""
        index = self.model.row_of(transaction_id)
        if index is None:
            self.notice.emit(title, "")
            return
        row = self.model.row_at(index)
        self.notice.emit(title, f"{row.amount} · {row.description}")

    def _delete_transfer(self, row: TransactionRow) -> None:
        assert row.transfer_id is not None
        transfer = self._services.account_transfers.get(row.transfer_id)
        route = (f"{self._account_names.get(transfer.from_account_id, '?')} → "
                 f"{self._account_names.get(transfer.to_account_id, '?')}")
        amount = format_money(transfer.amount)
        message = (f"Delete this transfer?\n\n{row.date} · {route} · {amount}\n\n"
                   "Both sides are removed and both balances are recalculated. "
                   "This cannot be undone.")
        if not dialogs.confirm_destructive(self, "Delete transfer", message):
            return
        try:
            self._services.account_transfers.delete(transfer.id)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, "Could not delete the transfer", str(exc))
            return
        self._after_change(None)
        self.notice.emit("Transfer deleted", f"{amount} · {route}")

    def transfer_between_accounts(self) -> None:
        if len(self._account_names) < 2:
            dialogs.show_info(self, "Add a second account",
                              "A transfer moves money between two of your accounts. Add the "
                              "other account first (New account), e.g. your cash or a card.")
            return
        dialog = self.make_transfer_dialog()
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved is not None:
            transfer = dialog.saved
            self._after_change(transfer.out_transaction_id)
            route = (f"{self._account_names.get(transfer.from_account_id, '?')} → "
                     f"{self._account_names.get(transfer.to_account_id, '?')}")
            self.notice.emit("Transfer recorded", f"{format_money(transfer.amount)} · {route}")

    def add_account(self) -> None:
        dialog = self.make_account_dialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()
            saved = getattr(dialog, "saved", None)
            self.notice.emit("Account created", saved.name if saved is not None else "")

    def create_account(self) -> None:
        dialog = self.make_account_dialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload()

    # Factories are separate so tests can substitute non-modal fakes.
    def make_transaction_dialog(self, transaction: Transaction | None) -> TransactionDialog:
        return TransactionDialog(self._services, transaction=transaction, parent=self)

    def make_account_dialog(self) -> AccountDialog:
        return AccountDialog(self._services, parent=self)

    def make_transfer_dialog(self) -> TransferDialog:
        return TransferDialog(self._services, parent=self)

    # --------------------------------------------------------------- loading

    def _load(self) -> None:
        try:
            page = self._services.transactions.search(self._query)
            if not page.items and page.offset > 0:  # e.g. the last item on a page was deleted
                self._query = replace(self._query, offset=max(page.offset - PAGE_SIZE, 0))
                page = self._services.transactions.search(self._query)
            total_balance = self._services.balances.total_balance()
            sides = transfer_sides(self._services.account_transfers.by_transaction(),
                                   self._account_names)
        except MoneyManagerError as exc:
            logger.warning("Could not load transactions: %s", exc)
            dialogs.show_warning(self, "Could not load transactions", str(exc))
            return
        self._page = page

        category_names = {c.id: c.name for c in self._categories}
        allocation_names = {a.id: a.name for a in self._allocations}
        self.model.set_rows(build_rows(page.items, category_names, allocation_names, sides))

        self.balance_card.set_value(
            format_money(total_balance), "outflow" if total_balance.is_negative() else "neutral"
        )
        self.income_card.set_value(format_signed_money(page.income), "inflow")
        self.expenses_card.set_value(format_signed_money(-page.expenses), "outflow")
        self._update_period_labels()

        self._update_empty_state(page)
        self._update_paging(page)
        self._update_actions()
        self.add_button.setEnabled(self._has_accounts)

    def _update_period_labels(self) -> None:
        filters = self._query.filters
        if filters.start is None and filters.end is None:
            suffix = "all time"
        elif filters.start is not None and filters.end is not None:
            suffix = f"{format_date(filters.start)} – {format_date(filters.end)}"
        else:
            suffix = "selected period"
        self.income_card.label.setText(f"Income · {suffix}")
        self.expenses_card.label.setText(f"Expenses · {suffix}")

    def _update_empty_state(self, page: TransactionPage) -> None:
        # Without an account there is nothing to summarise, filter or page through.
        for widget in (self.summary_row, self.filter_bar, self.footer, self.add_button,
                       self.transfer_button, self.new_account_button):
            widget.setVisible(self._has_accounts)
        if not self._has_accounts:
            self.empty_state.set_content(
                "Create an account to get started",
                "Transactions are recorded against an account, such as your bank account "
                "or cash. Enter its current balance and start tracking from today.",
                "Create account",
            )
        elif page.total_count == 0 and not self.filter_bar.is_filtered():
            self.empty_state.set_content(
                "No transactions yet",
                "Record your first income or expense. Your balance updates automatically.",
                "Add transaction",
            )
        elif page.total_count == 0:
            self.empty_state.set_content(
                "No matching transactions",
                "Nothing matches the current search and filters.",
                "Clear filters",
            )
        else:
            self.stack.setCurrentWidget(self.table)
            return
        self.stack.setCurrentIndex(EMPTY_STATE_INDEX)

    @property
    def showing_empty_state(self) -> bool:
        return self.stack.currentIndex() == EMPTY_STATE_INDEX

    def _update_paging(self, page: TransactionPage) -> None:
        if page.total_count:
            self.result_label.setText(
                f"Showing {page.first_index}–{page.last_index} of {page.total_count}"
            )
        else:
            self.result_label.setText("")
        self.previous_button.setEnabled(page.has_previous)
        self.next_button.setEnabled(page.has_next)
        paged = page.total_count > PAGE_SIZE
        self.previous_button.setVisible(paged)
        self.next_button.setVisible(paged)

    def _update_actions(self) -> None:
        has_selection = self.selected_transaction() is not None
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    # ---------------------------------------------------------------- events

    def _after_change(self, select_id: int | None) -> None:
        self.reload()
        if select_id is not None:
            self.select_transaction(select_id)

    def _on_filters_changed(self) -> None:
        self._query = replace(self._query, filters=self.filter_bar.filters(), offset=0)
        self._load()

    def _on_sort_requested(self, sort: TransactionSort, descending: bool) -> None:
        self._query = replace(self._query, sort=sort, descending=descending, offset=0)
        self._load()

    def _go_to_offset(self, delta: int) -> None:
        self._query = replace(self._query, offset=max(self._query.offset + delta, 0))
        self._load()

    def _on_empty_action(self) -> None:
        if not self._has_accounts:
            self.create_account()
        elif self.filter_bar.is_filtered():
            self.filter_bar.clear()
        else:
            self.add_transaction()


def _hbox(*widgets: QWidget, stretch_first: bool = False) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(Spacing.SM if stretch_first else Spacing.MD)
    for index, widget in enumerate(widgets):
        layout.addWidget(widget, 1 if (stretch_first and index == 0) or not stretch_first else 0)
    return container
