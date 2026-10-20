"""Confirm one due payment of a subscription as paid (creates one real expense)."""

from datetime import date

from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError, ValidationError
from money_manager.domain.entities import Transaction
from money_manager.domain.money import parse_amount_text
from money_manager.domain.subscriptions import Subscription, advance
from money_manager.services import AppServices
from money_manager.ui.components import FormField
from money_manager.ui.formatting import format_date
from money_manager.ui.goals.goal_dialog import amount_edit
from money_manager.ui.theme import Spacing
from money_manager.ui.transactions.filter_bar import to_qdate
from money_manager.core.i18n import tr


class RecordPaymentDialog(QDialog):
    def __init__(
        self,
        services: AppServices,
        subscription: Subscription,
        due_date: date,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._services = services
        self._subscription = subscription
        self.due_date = due_date
        self.saved: Transaction | None = None
        today = services.today()

        self.setWindowTitle(tr("Record payment · {0}", subscription.name))
        self.setModal(True)
        self.setMinimumWidth(440)

        following = advance(due_date, subscription.frequency, subscription.anchor_day)
        info = QLabel(
            tr("Confirms the payment due {0} by recording one expense. The next payment "
               "will then be due {1}.", format_date(due_date), format_date(following))
        )
        info.setObjectName("CardBody")
        info.setWordWrap(True)

        self.amount_edit = amount_edit()
        self.amount_edit.setText(f"{subscription.amount.amount}")
        self.date_edit = QDateEdit(to_qdate(min(due_date, today)))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setMaximumDate(to_qdate(today))
        self.account_combo = QComboBox()
        for account in services.accounts.list():
            self.account_combo.addItem(account.name, account.id)
        if subscription.account_id is not None:
            self.account_combo.setCurrentIndex(
                max(self.account_combo.findData(subscription.account_id), 0))
        self.account_combo.setPlaceholderText(tr("Create an account first"))

        # ``occurred_on`` is the transaction's own field name for the date.
        self.fields: dict[str, FormField] = {
            "amount": FormField(tr("Amount paid ({0})", services.base_currency), self.amount_edit),
            "occurred_on": FormField(tr("Paid on"), self.date_edit),
            "account_id": FormField(tr("Paid from"), self.account_combo),
        }
        self.form_error = QLabel()
        self.form_error.setObjectName("FormError")
        self.form_error.setWordWrap(True)
        self.form_error.hide()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok.setText(tr("Record payment"))
        ok.setObjectName("PrimaryButton")
        buttons.accepted.connect(self.submit)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        layout.addWidget(info)
        layout.addWidget(self.form_error)
        for field in self.fields.values():
            layout.addWidget(field)
        layout.addWidget(buttons)

    def submit(self) -> bool:
        for field in self.fields.values():
            field.set_error(None)
        self.form_error.hide()
        try:
            self.saved = self._services.subscriptions.record_payment(
                self._subscription.id,
                self.due_date,
                account_id=self.account_combo.currentData(),
                amount=parse_amount_text(self.amount_edit.text()),
                paid_on=self.date_edit.date().toPython(),
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
