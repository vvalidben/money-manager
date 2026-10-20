"""The "Loans and debts" card on the Accounts page."""

import logging

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError
from money_manager.domain.debts import Debt, DebtDirection, DebtSummary
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.components import Card, FlowRow
from money_manager.ui.debts.dialogs import DebtDialog, RepaymentDialog
from money_manager.ui.formatting import format_date, format_money, format_signed_money
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

COLUMNS = [tr("Who or what"), tr("Kind"), tr("Amount"), tr("Repaid"), tr("Left"), tr("Repay by"), tr("Status")]


def status_text(debt: Debt, today) -> str:  # noqa: ANN001 - a date
    if debt.is_settled:
        return tr("Repaid")
    if debt.is_overdue(today):
        return tr("Overdue")
    return tr("Open")


def summary_text(summary: DebtSummary) -> str:
    return (tr("Owed to you: {0} · You owe: {1} · In your net worth: {2}", format_money(summary.owed_to_you), format_money(summary.you_owe), format_signed_money(summary.net)))


class LoansCard(Card):
    changed = Signal(str, str)  # notice title, detail

    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(tr("Loans and debts"), parent)
        self._services = services
        self.debts: list[Debt] = []
        intro = QLabel(tr("Money you lent to someone or borrowed — a friend, a car loan. What is "
                       "left counts in your net worth."))
        intro.setObjectName("CardBody")
        intro.setWordWrap(True)
        self.body.addWidget(intro)
        self.summary_label = QLabel()
        self.summary_label.setObjectName("MutedLabel")
        self.summary_label.setWordWrap(True)
        self.body.addWidget(self.summary_label)
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setObjectName("DataTable")
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setMinimumHeight(150)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, len(COLUMNS)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self.table.doubleClicked.connect(lambda _i: self.repay_selected())
        self.body.addWidget(self.table)
        self.empty_label = QLabel(tr("No loans or debts recorded."))
        self.empty_label.setObjectName("MutedLabel")
        self.body.addWidget(self.empty_label)

        self.new_button = QPushButton(tr("New loan…"))
        self.new_button.clicked.connect(self.create)
        self.repay_button = QPushButton(tr("Record repayment…"))
        self.repay_button.clicked.connect(self.repay_selected)
        self.edit_button = QPushButton(tr("Edit…"))
        self.edit_button.clicked.connect(self.edit_selected)
        self.undo_button = QPushButton(tr("Undo last repayment"))
        self.undo_button.clicked.connect(self.undo_last_payment)
        self.delete_button = QPushButton(tr("Delete"))
        self.delete_button.setObjectName("DangerButton")
        self.delete_button.clicked.connect(self.delete_selected)
        self.body.addWidget(FlowRow([self.new_button, self.repay_button, self.edit_button,
                                     self.undo_button, self.delete_button]))

    def load(self) -> None:
        try:
            self.debts = self._services.debts.list()
            summary = self._services.debts.summary()
        except MoneyManagerError as exc:
            logger.warning("Could not load loans: %s", exc)
            self.summary_label.setText(str(exc))
            return
        today = self._services.today()
        self.table.setRowCount(len(self.debts))
        for row, debt in enumerate(self.debts):
            lent = debt.direction is DebtDirection.LENT
            cells = [debt.name, tr("Lent") if lent else tr("Borrowed"), format_money(debt.amount),
                     format_money(debt.repaid), format_money(debt.remaining),
                     "—" if debt.due_date is None else format_date(debt.due_date),
                     status_text(debt, today)]
            for column, text in enumerate(cells):
                self.table.setItem(row, column, QTableWidgetItem(text))
        self.summary_label.setText(summary_text(summary))
        self.summary_label.setVisible(bool(self.debts))
        self.table.setVisible(bool(self.debts))
        self.empty_label.setVisible(not self.debts)
        self._update_buttons()

    def selected(self) -> Debt | None:
        rows = self.table.selectionModel().selectedRows()
        return self.debts[rows[0].row()] if rows else None

    def _update_buttons(self) -> None:
        debt = self.selected()
        for button in (self.edit_button, self.delete_button):
            button.setEnabled(debt is not None)
        self.repay_button.setEnabled(debt is not None and not debt.is_settled)
        self.undo_button.setEnabled(debt is not None and bool(debt.payments))

    # Separate so tests can substitute non-modal fakes.
    def make_debt_dialog(self, debt: Debt | None) -> DebtDialog:
        return DebtDialog(self._services, debt, parent=self)

    def make_repayment_dialog(self, debt: Debt) -> RepaymentDialog:
        return RepaymentDialog(self._services, debt, parent=self)

    def create(self) -> None:
        dialog = self.make_debt_dialog(None)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved is not None:
            self.changed.emit(tr("Loan recorded"), f"{dialog.saved.name} · "
                                               f"{format_money(dialog.saved.amount)}")

    def edit_selected(self) -> None:
        debt = self.selected()
        if debt is None:
            return
        dialog = self.make_debt_dialog(debt)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved is not None:
            self.changed.emit(tr("Loan updated"), dialog.saved.name)

    def repay_selected(self) -> None:
        debt = self.selected()
        if debt is None or debt.is_settled:
            return
        dialog = self.make_repayment_dialog(debt)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved is not None:
            saved = dialog.saved
            detail = (tr("fully repaid") if saved.is_settled
                      else f"{format_money(saved.remaining)} left")
            self.changed.emit(tr("Repayment recorded"), f"{saved.name} · {detail}")

    def undo_last_payment(self) -> None:
        debt = self.selected()
        if debt is None or not debt.payments:
            return
        last = debt.payments[-1]
        if not dialogs.confirm_destructive(
                self, tr("Undo repayment"),
                tr("Remove the repayment of {0} on {1}? If it moved money through an "
                   "account, that adjustment is removed too.", format_money(last.amount), format_date(last.paid_on)), tr("Remove")):
            return
        try:
            self._services.debts.delete_payment(last.id)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, tr("Could not remove the repayment"), str(exc))
            return
        self.changed.emit(tr("Repayment removed"), debt.name)

    def delete_selected(self) -> None:
        debt = self.selected()
        if debt is None or not dialogs.confirm_destructive(
                self, tr("Delete loan"),
                tr("Delete “{0}” and its repayments? Money already moved through your "
                   "accounts stays recorded.", debt.name)):
            return
        try:
            self._services.debts.delete(debt.id)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, tr("Could not delete the loan"), str(exc))
            return
        self.changed.emit(tr("Loan deleted"), debt.name)
