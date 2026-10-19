"""Correct an account's balance to match the bank (recorded as an adjustment).

The recorded balance is never overwritten: ``BalanceService.reconcile`` records
the difference as a balance adjustment, which can be seen and deleted later.
"""

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError, ValidationError
from money_manager.domain.entities import Account, Transaction
from money_manager.domain.money import Money, parse_amount_text
from money_manager.services import AppServices
from money_manager.ui.accounts.account_dialog import OPENING_BALANCE_PATTERN
from money_manager.ui.components import FormField
from money_manager.ui.formatting import format_money
from money_manager.ui.theme import Spacing
from money_manager.ui.transactions.transaction_dialog import side_by_side


class CorrectBalanceDialog(QDialog):
    def __init__(self, services: AppServices, account: Account, recorded: Money,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._services = services
        self._account = account
        self.submitted = False
        self.adjustment: Transaction | None = None  # None when nothing needed correcting
        self.setWindowTitle(f"Correct the balance of {account.name}")
        self.setModal(True)
        self.setMinimumWidth(420)

        intro = QLabel(
            f"Money Manager shows {format_money(recorded)} today. Enter the balance your "
            "bank (or wallet) shows; the difference is recorded as a balance adjustment, "
            "so nothing is overwritten and you can see the correction in Transactions.")
        intro.setObjectName("CardBody")
        intro.setWordWrap(True)
        self.balance_edit = QLineEdit(str(recorded.amount))
        self.balance_edit.setValidator(
            QRegularExpressionValidator(QRegularExpression(OPENING_BALANCE_PATTERN), self))
        currency = QLabel(services.base_currency)
        currency.setObjectName("MutedLabel")
        self.field = FormField("Actual balance today", side_by_side(self.balance_edit, currency),
                               highlight=self.balance_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        save = buttons.button(QDialogButtonBox.StandardButton.Save)
        save.setText("Correct balance")
        save.setObjectName("PrimaryButton")
        save.setDefault(True)
        buttons.accepted.connect(self.submit)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        layout.addWidget(intro)
        layout.addWidget(self.field)
        layout.addWidget(buttons)

    def submit(self) -> bool:
        self.field.set_error(None)
        try:
            self.adjustment = self._services.balances.reconcile(
                self._account.id, parse_amount_text(self.balance_edit.text(), "actual_balance"))
        except (ValidationError, MoneyManagerError) as exc:
            self.field.set_error(str(exc))
            return False
        self.submitted = True
        self.accept()
        return True
