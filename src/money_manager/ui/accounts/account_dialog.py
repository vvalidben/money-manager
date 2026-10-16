"""Create-account dialog (needed before the first transaction can be recorded)."""

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError, ValidationError
from money_manager.domain.entities import Account
from money_manager.domain.money import parse_amount_text
from money_manager.domain.validation import MAX_ACCOUNT_NAME_LENGTH
from money_manager.services import AppServices
from money_manager.ui.components import FormField
from money_manager.ui.theme import Spacing
from money_manager.ui.transactions.filter_bar import to_qdate

# Like transaction amounts, but an opening balance may be negative (overdrawn).
OPENING_BALANCE_PATTERN = r"-?[0-9   ]*([.,][0-9]{0,2})?"


class AccountDialog(QDialog):
    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._services = services
        self.saved: Account | None = None

        self.setWindowTitle("Create account")
        self.setModal(True)
        self.setMinimumWidth(420)

        intro = QLabel(
            "An account is where your money is kept, such as a bank account or cash. "
            "Enter its balance on the day you start tracking; earlier activity is "
            "already included in that balance."
        )
        intro.setObjectName("CardBody")
        intro.setWordWrap(True)

        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(MAX_ACCOUNT_NAME_LENGTH)
        self.name_edit.setPlaceholderText("e.g. Bank account")

        self.balance_edit = QLineEdit("0")
        self.balance_edit.setValidator(
            QRegularExpressionValidator(QRegularExpression(OPENING_BALANCE_PATTERN), self)
        )

        self.date_edit = QDateEdit(to_qdate(services.today()))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setMaximumDate(to_qdate(services.today()))

        self.fields: dict[str, FormField] = {
            "name": FormField("Name", self.name_edit),
            "opening_balance": FormField(
                f"Balance on the start date ({services.base_currency})", self.balance_edit
            ),
            "opening_date": FormField("Start date", self.date_edit),
        }
        self.form_error = QLabel()
        self.form_error.setObjectName("FormError")
        self.form_error.setWordWrap(True)
        self.form_error.hide()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save = buttons.button(QDialogButtonBox.StandardButton.Save)
        save.setText("Create account")
        save.setObjectName("PrimaryButton")
        buttons.accepted.connect(self.submit)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        layout.addWidget(intro)
        layout.addWidget(self.form_error)
        for field in self.fields.values():
            layout.addWidget(field)
        layout.addWidget(buttons)

    def submit(self) -> bool:
        for field in self.fields.values():
            field.set_error(None)
        self.form_error.hide()
        try:
            self.saved = self._services.accounts.create(
                self.name_edit.text(),
                opening_balance=parse_amount_text(self.balance_edit.text(), "opening_balance"),
                opening_date=self.date_edit.date().toPython(),
            )
        except ValidationError as exc:
            field = self.fields.get(exc.field or "")
            if field is not None:
                field.set_error(str(exc))
            else:
                self._show_form_error(str(exc))
            return False
        except MoneyManagerError as exc:
            self._show_form_error(str(exc))
            return False
        self.accept()
        return True

    def _show_form_error(self, message: str) -> None:
        self.form_error.setText(message)
        self.form_error.show()
