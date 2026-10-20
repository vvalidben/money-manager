"""Dialogs for debts and loans: a new or edited loan, and a repayment.

They only collect input; ``DebtService`` enforces every rule.
"""

from PySide6.QtCore import QDate, QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError, ValidationError
from money_manager.domain.debts import MAX_DEBT_NAME_LENGTH, Debt, DebtDirection
from money_manager.domain.money import parse_amount_text
from money_manager.services import AppServices
from money_manager.ui.components import FormField
from money_manager.ui.formatting import format_money
from money_manager.ui.theme import Spacing
from money_manager.ui.transactions.filter_bar import to_qdate
from money_manager.ui.transactions.transaction_dialog import AMOUNT_INPUT_PATTERN, side_by_side
from money_manager.core.i18n import tr

NO_ACCOUNT = tr("Not through an account (only track it)")


def _amount_edit(parent: QWidget) -> QLineEdit:
    edit = QLineEdit()
    edit.setPlaceholderText("0.00")
    edit.setValidator(QRegularExpressionValidator(QRegularExpression(AMOUNT_INPUT_PATTERN),
                                                  parent))
    return edit


def _date_edit(value: QDate) -> QDateEdit:
    edit = QDateEdit()
    edit.setCalendarPopup(True)
    edit.setDisplayFormat("dd/MM/yyyy")
    edit.setDate(value)
    return edit


def _account_combo(services: AppServices) -> QComboBox:
    combo = QComboBox()
    combo.addItem(NO_ACCOUNT, None)
    for account in services.accounts.list():
        combo.addItem(account.name, account.id)
    return combo


class _FormDialog(QDialog):
    """Shared layout: a note, inline errors, a grid of fields and Save / Cancel."""

    def _finish(self, note: str, rows: list[list[str]], save_text: str) -> None:
        intro = QLabel(note)
        intro.setObjectName("MutedLabel")
        intro.setWordWrap(True)
        self.form_error = QLabel()
        self.form_error.setObjectName("FormError")
        self.form_error.setWordWrap(True)
        self.form_error.hide()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setText(save_text)
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.setDefault(True)
        buttons.accepted.connect(self.submit)
        buttons.rejected.connect(self.reject)
        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.MD)
        grid.setVerticalSpacing(Spacing.SM)
        for row, keys in enumerate(rows):
            for column, key in enumerate(keys):
                span = 2 if len(keys) == 1 else 1
                grid.addWidget(self.fields[key], row, column, 1, span)
                grid.setAlignment(self.fields[key], Qt.AlignmentFlag.AlignTop)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        layout.addWidget(intro)
        layout.addWidget(self.form_error)
        layout.addLayout(grid)
        layout.addWidget(buttons)

    fields: dict[str, FormField]

    def submit(self) -> bool:  # pragma: no cover - overridden
        raise NotImplementedError

    def _run(self, action) -> bool:  # noqa: ANN001 - a callable that saves
        for field in self.fields.values():
            field.set_error(None)
        self.form_error.hide()
        try:
            action()
        except ValidationError as exc:
            field = self.fields.get(exc.field or "")
            if field is None:
                self.form_error.setText(str(exc))
                self.form_error.show()
            else:
                field.set_error(str(exc))
            return False
        except MoneyManagerError as exc:
            self.form_error.setText(str(exc))
            self.form_error.show()
            return False
        self.accept()
        return True


class DebtDialog(_FormDialog):
    """A new loan (lent or borrowed), or the name, due date and notes of one."""

    def __init__(self, services: AppServices, debt: Debt | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._services = services
        self._debt = debt
        self.saved: Debt | None = None
        self.setWindowTitle(tr("Edit loan") if debt else tr("New loan"))
        self.setModal(True)
        self.setMinimumWidth(520)
        today = to_qdate(services.today())

        self.direction_combo = QComboBox()
        self.direction_combo.addItem(tr("I lent money (someone owes me)"), DebtDirection.LENT.value)
        self.direction_combo.addItem(tr("I borrowed money (I owe it)"), DebtDirection.BORROWED.value)
        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(MAX_DEBT_NAME_LENGTH)
        self.name_edit.setPlaceholderText(tr("e.g. Sami, Car loan"))
        self.amount_edit = _amount_edit(self)
        currency = QLabel(services.base_currency)
        currency.setObjectName("MutedLabel")
        self.start_edit = _date_edit(today)
        self.start_edit.setMaximumDate(today)
        self.due_box = QCheckBox(tr("Due by"))
        self.due_edit = _date_edit(today.addMonths(3))
        self.due_edit.setEnabled(False)
        self.due_box.toggled.connect(self.due_edit.setEnabled)
        self.account_combo = _account_combo(services)
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText(tr("Optional"))

        self.fields = {
            "direction": FormField(tr("Kind"), self.direction_combo),
            "name": FormField(tr("Who or what"), self.name_edit),
            "amount": FormField(tr("Amount"), side_by_side(self.amount_edit, currency),
                                highlight=self.amount_edit),
            "start_date": FormField(tr("Date"), self.start_edit),
            "due_date": FormField(tr("Repay by"), side_by_side(self.due_box, self.due_edit),
                                  highlight=self.due_edit),
            "account_id": FormField(tr("Money moved through"), self.account_combo),
            "notes": FormField(tr("Notes"), self.notes_edit),
        }
        if debt is None:
            rows = [["direction"], ["name", "amount"], ["start_date", "due_date"],
                    ["account_id"], ["notes"]]
            note = (tr("Choose an account if the money went out of it (or came into it): it is "
                    "recorded as a balance adjustment, never as income or spending. Loans "
                    "count in your net worth."))
        else:
            rows = [["name", "due_date"], ["notes"]]
            note = tr("The amount and the date stay as recorded; repayments lower what is left.")
            for key in ("direction", "amount", "start_date", "account_id"):
                self.fields[key].hide()
            self.name_edit.setText(debt.name)
            self.notes_edit.setText(debt.notes)
            if debt.due_date is not None:
                self.due_box.setChecked(True)
                self.due_edit.setDate(to_qdate(debt.due_date))
        self._finish(note, rows, tr("Save"))

    def submit(self) -> bool:
        due = self.due_edit.date().toPython() if self.due_box.isChecked() else None

        def save() -> None:
            if self._debt is None:
                self.saved = self._services.debts.create(
                    self.name_edit.text(), direction=self.direction_combo.currentData(),
                    amount=parse_amount_text(self.amount_edit.text()),
                    start_date=self.start_edit.date().toPython(), due_date=due,
                    notes=self.notes_edit.text(), account_id=self.account_combo.currentData())
            else:
                self.saved = self._services.debts.update(
                    self._debt.id, self.name_edit.text(), due_date=due,
                    notes=self.notes_edit.text())

        return self._run(save)


class RepaymentDialog(_FormDialog):
    def __init__(self, services: AppServices, debt: Debt, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._services = services
        self._debt = debt
        self.saved: Debt | None = None
        lent = debt.direction is DebtDirection.LENT
        self.setWindowTitle(tr("Repayment from {0}", debt.name) if lent else tr("Repayment to {0}", debt.name))
        self.setModal(True)
        self.setMinimumWidth(480)
        self.amount_edit = _amount_edit(self)
        self.amount_edit.setText(f"{debt.remaining.amount:.2f}")
        currency = QLabel(services.base_currency)
        currency.setObjectName("MutedLabel")
        today = to_qdate(services.today())
        self.date_edit = _date_edit(today)
        self.date_edit.setMaximumDate(today)
        self.account_combo = _account_combo(services)
        if self.account_combo.count() > 1:
            self.account_combo.setCurrentIndex(1)
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText(tr("Optional"))
        self.fields = {
            "amount": FormField(tr("Amount"), side_by_side(self.amount_edit, currency),
                                highlight=self.amount_edit),
            "paid_on": FormField(tr("Date"), self.date_edit),
            "account_id": FormField(tr("Received into") if lent else tr("Paid from"),
                                    self.account_combo),
            "note": FormField(tr("Note"), self.note_edit),
        }
        self._finish(tr("Left to repay: {0}.", format_money(debt.remaining)),
                     [["amount", "paid_on"], ["account_id"], ["note"]], tr("Record"))

    def submit(self) -> bool:
        def save() -> None:
            self.saved = self._services.debts.record_payment(
                self._debt.id, parse_amount_text(self.amount_edit.text()),
                self.date_edit.date().toPython(), account_id=self.account_combo.currentData(),
                note=self.note_edit.text())

        return self._run(save)
