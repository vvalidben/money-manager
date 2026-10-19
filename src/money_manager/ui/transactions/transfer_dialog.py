"""Transfer money between two of the user's accounts.

The dialog only collects input; ``AccountTransferService`` enforces every rule
(two different accounts, positive amount, dates after both accounts opened).
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
from money_manager.domain.entities import Account, AccountTransfer
from money_manager.domain.money import parse_amount_text
from money_manager.domain.validation import MAX_DESCRIPTION_LENGTH
from money_manager.services import AppServices
from money_manager.ui.components import FormField
from money_manager.ui.theme import Spacing
from money_manager.ui.transactions.filter_bar import to_qdate
from money_manager.ui.transactions.transaction_dialog import AMOUNT_INPUT_PATTERN, side_by_side


class TransferDialog(QDialog):
    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._services = services
        self.saved: AccountTransfer | None = None
        self.setWindowTitle("Transfer between accounts")
        self.setModal(True)
        self.setMinimumWidth(480)

        self._accounts: list[Account] = services.accounts.list()
        self.from_combo = QComboBox()
        self.to_combo = QComboBox()
        for account in self._accounts:
            self.from_combo.addItem(account.name, account.id)
            self.to_combo.addItem(account.name, account.id)
        if len(self._accounts) > 1:
            self.to_combo.setCurrentIndex(1)

        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("0.00")
        self.amount_edit.setValidator(
            QRegularExpressionValidator(QRegularExpression(AMOUNT_INPUT_PATTERN), self))
        currency = QLabel(services.base_currency)
        currency.setObjectName("MutedLabel")

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setMaximumDate(to_qdate(services.today()))
        self.date_edit.setDate(to_qdate(services.today()))

        self.description_edit = QLineEdit()
        self.description_edit.setMaxLength(MAX_DESCRIPTION_LENGTH)
        self.description_edit.setPlaceholderText("Optional, e.g. Cash for the market")

        self.fields: dict[str, FormField] = {
            "from_account_id": FormField("From", self.from_combo),
            "to_account_id": FormField("To", self.to_combo),
            "amount": FormField("Amount", side_by_side(self.amount_edit, currency),
                                highlight=self.amount_edit),
            "occurred_on": FormField("Date", self.date_edit),
            "description": FormField("Description", self.description_edit),
        }
        note = QLabel("Moves money between your own accounts. Your total stays the same, and a "
                      "transfer never counts as income or spending.")
        note.setObjectName("MutedLabel")
        note.setWordWrap(True)

        self.form_error = QLabel()
        self.form_error.setObjectName("FormError")
        self.form_error.setWordWrap(True)
        self.form_error.hide()

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.save_button = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setText("Transfer")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.setDefault(True)
        self.buttons.accepted.connect(self.submit)
        self.buttons.rejected.connect(self.reject)

        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.MD)
        grid.setVerticalSpacing(Spacing.SM)
        grid.addWidget(self.fields["from_account_id"], 0, 0)
        grid.addWidget(self.fields["to_account_id"], 0, 1)
        grid.addWidget(self.fields["amount"], 1, 0)
        grid.addWidget(self.fields["occurred_on"], 1, 1)
        grid.addWidget(self.fields["description"], 2, 0, 1, 2)
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

        for key, signal in (("amount", self.amount_edit.textChanged),
                            ("description", self.description_edit.textChanged),
                            ("occurred_on", self.date_edit.dateChanged),
                            ("from_account_id", self.from_combo.currentIndexChanged),
                            ("to_account_id", self.to_combo.currentIndexChanged)):
            signal.connect(lambda *_args, key=key: self.fields[key].set_error(None))

    def submit(self) -> bool:
        """Save through the service; show errors inline and stay open on failure."""
        for field in self.fields.values():
            field.set_error(None)
        self.form_error.hide()
        try:
            self.saved = self._services.account_transfers.create(
                self.from_combo.currentData(), self.to_combo.currentData(),
                parse_amount_text(self.amount_edit.text()),
                self.date_edit.date().toPython(), self.description_edit.text())
        except ValidationError as exc:
            field = self.fields.get(exc.field or "")
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
