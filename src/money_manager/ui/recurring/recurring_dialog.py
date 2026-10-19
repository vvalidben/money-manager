"""Recurring entries: the list of schedules, with add, edit, pause and delete."""

import logging

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError
from money_manager.domain.enums import TransactionType
from money_manager.domain.recurring import RecordOutcome, RecurringEntry
from money_manager.domain.subscriptions import Frequency
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.formatting import format_date, format_signed_money
from money_manager.ui.recurring.entry_dialog import RecurringEntryDialog
from money_manager.ui.theme import Spacing

logger = logging.getLogger(__name__)

COLUMNS = ["Description", "Amount", "Repeats", "Next date", "Account", "Status"]


def repeats_text(entry: RecurringEntry) -> str:
    day = entry.anchor_day
    return {
        Frequency.WEEKLY: f"Weekly ({entry.next_date:%A}s)",
        Frequency.MONTHLY: f"Monthly, day {day}",
        Frequency.QUARTERLY: f"Every 3 months, day {day}",
        Frequency.YEARLY: f"Yearly, {entry.next_date:%d %b}",
    }[entry.frequency]


def outcome_text(outcome: RecordOutcome) -> str:
    parts = []
    if outcome.recorded:
        parts.append(f"{outcome.recorded} recorded" if outcome.recorded != 1 else "1 recorded")
    for problem in outcome.problems:
        parts.append(f"“{problem.description}” on {format_date(problem.due)} could not be "
                     f"recorded: {problem.message}")
    return " · ".join(parts)


class RecurringDialog(QDialog):
    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._services = services
        self.changed = False  # entries were added, changed or recorded
        self.entries: list[RecurringEntry] = []
        self.setWindowTitle("Recurring entries")
        self.setModal(True)
        self.resize(820, 460)

        intro = QLabel("Income and expenses that repeat — salary, rent, savings — are recorded "
                       "automatically on each date. Subscriptions you confirm one by one stay on "
                       "the Subscriptions page.")
        intro.setObjectName("MutedLabel")
        intro.setWordWrap(True)
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setObjectName("DataTable")
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, len(COLUMNS)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self.table.doubleClicked.connect(lambda _index: self.edit_selected())
        self.empty_label = QLabel("No recurring entries yet. Add your salary or rent to have "
                                  "them recorded for you.")
        self.empty_label.setObjectName("MutedLabel")
        self.status_label = QLabel()
        self.status_label.setObjectName("MutedLabel")
        self.status_label.setWordWrap(True)

        self.add_button = QPushButton("Add…")
        self.add_button.setObjectName("PrimaryButton")
        self.add_button.clicked.connect(self.add)
        self.edit_button = QPushButton("Edit…")
        self.edit_button.clicked.connect(self.edit_selected)
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.toggle_selected)
        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("DangerButton")
        self.delete_button.clicked.connect(self.delete_selected)
        actions = QHBoxLayout()
        for button in (self.add_button, self.edit_button, self.pause_button, self.delete_button):
            actions.addWidget(button)
        actions.addStretch(1)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        actions.addWidget(close)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        layout.addWidget(intro)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.status_label)
        layout.addLayout(actions)
        self.load()

    def load(self) -> None:
        try:
            self.entries = self._services.recurring.list()
            accounts = {a.id: a.name for a in self._services.accounts.list()}
        except MoneyManagerError as exc:
            self.entries, accounts = [], {}
            self.status_label.setText(str(exc))
        self.table.setRowCount(len(self.entries))
        for row, entry in enumerate(self.entries):
            signed = entry.amount if entry.type is TransactionType.INCOME else -entry.amount
            cells = [entry.description, format_signed_money(signed), repeats_text(entry),
                     format_date(entry.next_date), accounts.get(entry.account_id, "?"),
                     "Active" if entry.is_active else "Paused"]
            for column, text in enumerate(cells):
                self.table.setItem(row, column, QTableWidgetItem(text))
        self.table.setVisible(bool(self.entries))
        self.empty_label.setVisible(not self.entries)
        self._update_buttons()

    def selected(self) -> RecurringEntry | None:
        rows = self.table.selectionModel().selectedRows()
        return self.entries[rows[0].row()] if rows else None

    def _update_buttons(self) -> None:
        entry = self.selected()
        for button in (self.edit_button, self.pause_button, self.delete_button):
            button.setEnabled(entry is not None)
        self.pause_button.setText("Resume" if entry is not None and not entry.is_active
                                  else "Pause")

    def add(self) -> None:
        if not self._services.accounts.list():
            dialogs.show_info(self, "Recurring entries", "Create an account first.")
            return
        self._edit(None)

    def edit_selected(self) -> None:
        entry = self.selected()
        if entry is not None:
            self._edit(entry)

    def _edit(self, entry: RecurringEntry | None) -> None:
        dialog = self.make_entry_dialog(entry)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.saved is None:
            return
        self.changed = True
        self._record_due()
        self.load()

    def make_entry_dialog(self, entry: RecurringEntry | None) -> RecurringEntryDialog:
        return RecurringEntryDialog(self._services, entry, parent=self)

    def toggle_selected(self) -> None:
        entry = self.selected()
        if entry is None:
            return
        try:
            self._services.recurring.set_active(entry.id, not entry.is_active)
        except MoneyManagerError as exc:
            self.status_label.setText(str(exc))
            return
        self.changed = True
        self.load()

    def delete_selected(self) -> None:
        entry = self.selected()
        if entry is None or not dialogs.confirm_destructive(
                self, "Delete recurring entry",
                f"Stop recording “{entry.description}”? Entries already recorded are kept."):
            return
        try:
            self._services.recurring.delete(entry.id)
        except MoneyManagerError as exc:
            self.status_label.setText(str(exc))
            return
        self.changed = True
        self.load()

    def _record_due(self) -> None:
        """A first date in the past records the dates since then right away."""
        try:
            outcome = self._services.recurring.record_due()
        except MoneyManagerError as exc:
            self.status_label.setText(str(exc))
            return
        text = outcome_text(outcome)
        self.status_label.setText(f"Recorded now: {text}." if outcome.recorded
                                  else text)
