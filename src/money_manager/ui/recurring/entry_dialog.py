"""Add or edit a recurring entry (income or expense recorded on a schedule).

The dialog only collects input; ``RecurringService`` enforces every rule.
"""

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
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
from money_manager.domain.enums import CategoryKind, TransactionType
from money_manager.domain.money import parse_amount_text
from money_manager.domain.recurring import RecurringEntry
from money_manager.domain.subscriptions import Frequency
from money_manager.domain.validation import MAX_DESCRIPTION_LENGTH
from money_manager.services import AppServices
from money_manager.ui.components import FormField
from money_manager.ui.theme import Spacing
from money_manager.ui.transactions.filter_bar import to_qdate
from money_manager.ui.transactions.transaction_dialog import AMOUNT_INPUT_PATTERN, side_by_side
from money_manager.core.i18n import tr

FREQUENCY_LABELS = {Frequency.WEEKLY: tr("Every week"), Frequency.MONTHLY: tr("Every month"),
                    Frequency.QUARTERLY: tr("Every 3 months"), Frequency.YEARLY: tr("Every year")}


class RecurringEntryDialog(QDialog):
    def __init__(self, services: AppServices, entry: RecurringEntry | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._services = services
        self._original = entry
        self.saved: RecurringEntry | None = None
        self.setWindowTitle(tr("Edit recurring entry") if entry else tr("New recurring entry"))
        self.setModal(True)
        self.setMinimumWidth(500)

        self.type_combo = QComboBox()
        self.type_combo.addItem(tr("Expense"), TransactionType.EXPENSE.value)
        self.type_combo.addItem(tr("Income"), TransactionType.INCOME.value)
        self.description_edit = QLineEdit()
        self.description_edit.setMaxLength(MAX_DESCRIPTION_LENGTH)
        self.description_edit.setPlaceholderText(tr("e.g. Rent, Salary"))
        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("0.00")
        self.amount_edit.setValidator(
            QRegularExpressionValidator(QRegularExpression(AMOUNT_INPUT_PATTERN), self))
        currency = QLabel(services.base_currency)
        currency.setObjectName("MutedLabel")
        self.account_combo = QComboBox()
        for account in services.accounts.list():
            self.account_combo.addItem(account.name, account.id)
        self.category_combo = QComboBox()
        self.frequency_combo = QComboBox()
        for frequency, label in FREQUENCY_LABELS.items():
            self.frequency_combo.addItem(label, frequency.value)
        self.frequency_combo.setCurrentIndex(1)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setDate(to_qdate(services.today()))

        self.fields: dict[str, FormField] = {
            "type": FormField(tr("Type"), self.type_combo),
            "description": FormField(tr("Description"), self.description_edit),
            "amount": FormField(tr("Amount"), side_by_side(self.amount_edit, currency),
                                highlight=self.amount_edit),
            "account_id": FormField(tr("Account"), self.account_combo),
            "category_id": FormField(tr("Category"), self.category_combo),
            "frequency": FormField(tr("Repeats"), self.frequency_combo),
            "first_date": FormField(tr("Next date") if entry else tr("First date"), self.date_edit),
        }
        note = QLabel(tr("Recorded automatically on each date — when Money Manager is open, or the "
                      "next time it starts. A first date in the past records the dates since "
                      "then (up to a year)."))
        note.setObjectName("MutedLabel")
        note.setWordWrap(True)
        self.form_error = QLabel()
        self.form_error.setObjectName("FormError")
        self.form_error.setWordWrap(True)
        self.form_error.hide()

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.save_button = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.setDefault(True)
        self.buttons.accepted.connect(self.submit)
        self.buttons.rejected.connect(self.reject)

        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.MD)
        grid.setVerticalSpacing(Spacing.SM)
        for row, (left, right) in enumerate((("type", "description"), ("amount", "account_id"),
                                             ("category_id", "frequency"))):
            grid.addWidget(self.fields[left], row, 0)
            grid.addWidget(self.fields[right], row, 1)
        grid.addWidget(self.fields["first_date"], 3, 0)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        for field in self.fields.values():
            grid.setAlignment(field, Qt.AlignmentFlag.AlignTop)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        layout.addWidget(note)
        layout.addWidget(self.form_error)
        layout.addLayout(grid)
        layout.addWidget(self.buttons)

        self.type_combo.currentIndexChanged.connect(lambda _i: self._fill_categories())
        if entry is not None:
            self._load(entry)
        else:
            self._fill_categories()
        for key, signal in (("amount", self.amount_edit.textChanged),
                            ("description", self.description_edit.textChanged),
                            ("first_date", self.date_edit.dateChanged),
                            ("category_id", self.category_combo.currentIndexChanged)):
            signal.connect(lambda *_args, key=key: self.fields[key].set_error(None))

    def _load(self, entry: RecurringEntry) -> None:
        self.type_combo.setCurrentIndex(self.type_combo.findData(entry.type.value))
        self.description_edit.setText(entry.description)
        self.amount_edit.setText(f"{entry.amount.amount:.2f}")
        self.account_combo.setCurrentIndex(max(self.account_combo.findData(entry.account_id), 0))
        self.frequency_combo.setCurrentIndex(self.frequency_combo.findData(entry.frequency.value))
        self.date_edit.setDate(to_qdate(entry.next_date))
        self._fill_categories(entry.category_id)

    def _fill_categories(self, select_id: int | None = None) -> None:
        kind = (CategoryKind.INCOME if self.type_combo.currentData() == TransactionType.INCOME
                else CategoryKind.EXPENSE)
        keep = select_id if select_id is not None else self.category_combo.currentData()
        self.category_combo.clear()
        for category in self._services.categories.list(include_archived=True):
            if category.kind is kind and (not category.is_archived or category.id == keep):
                self.category_combo.addItem(category.name, category.id)
        index = self.category_combo.findData(keep)
        self.category_combo.setCurrentIndex(index if index >= 0 else 0)
        self.category_combo.setPlaceholderText(
            tr("No category yet — add one first") if self.category_combo.count() == 0 else "")

    def submit(self) -> bool:
        for field in self.fields.values():
            field.set_error(None)
        self.form_error.hide()
        values = dict(type=self.type_combo.currentData(),
                      amount=parse_amount_text(self.amount_edit.text()),
                      account_id=self.account_combo.currentData(),
                      category_id=self.category_combo.currentData(),
                      frequency=self.frequency_combo.currentData())
        day = self.date_edit.date().toPython()
        try:
            if self._original is None:
                self.saved = self._services.recurring.create(
                    self.description_edit.text(), first_date=day, **values)
            else:
                self.saved = self._services.recurring.update(
                    self._original.id, self.description_edit.text(), next_date=day, **values)
        except ValidationError as exc:
            field = self.fields.get("first_date" if exc.field == "next_date" else exc.field or "")
            if field is None:
                self._show_form_error(str(exc))
            else:
                field.set_error(str(exc))
            return False
        except MoneyManagerError as exc:
            self._show_form_error(str(exc))
            return False
        self.accept()
        return True

    def _show_form_error(self, message: str) -> None:
        self.form_error.setText(message)
        self.form_error.show()
