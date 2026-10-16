"""Create / edit subscription dialog. Every rule is enforced by ``SubscriptionService``."""

from datetime import timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError, ValidationError
from money_manager.domain.enums import CategoryKind
from money_manager.domain.money import parse_amount_text
from money_manager.domain.subscriptions import Frequency, Subscription
from money_manager.domain.validation import (
    MAX_SUBSCRIPTION_NAME_LENGTH,
    SUBSCRIPTION_PAST_LIMIT_DAYS,
)
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.components import FormField
from money_manager.ui.goals.goal_dialog import amount_edit
from money_manager.ui.subscriptions.view_model import FREQUENCY_TEXT
from money_manager.ui.theme import Spacing
from money_manager.ui.transactions.filter_bar import to_qdate


class SubscriptionDialog(QDialog):
    def __init__(
        self,
        services: AppServices,
        *,
        subscription: Subscription | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._services = services
        self._original = subscription
        self.saved: Subscription | None = None
        today = services.today()

        self.setWindowTitle("Edit subscription" if subscription else "New subscription")
        self.setModal(True)
        self.setMinimumWidth(500)

        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(MAX_SUBSCRIPTION_NAME_LENGTH)
        self.name_edit.setPlaceholderText("e.g. Netflix")
        self.amount_edit = amount_edit()
        self.frequency_combo = QComboBox()
        for frequency, label in FREQUENCY_TEXT.items():
            self.frequency_combo.addItem(label, frequency.value)
        self.frequency_combo.setCurrentIndex(self.frequency_combo.findData(Frequency.MONTHLY.value))
        self.date_edit = QDateEdit(to_qdate(today))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setMinimumDate(to_qdate(today - timedelta(days=SUBSCRIPTION_PAST_LIMIT_DAYS)))

        self.category_combo = QComboBox()
        self.new_category_button = QToolButton()
        self.new_category_button.setText("New…")
        self.new_category_button.clicked.connect(self._prompt_new_category)
        category_row = QWidget()
        category_layout = QHBoxLayout(category_row)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.addWidget(self.category_combo, 1)
        category_layout.addWidget(self.new_category_button)

        self.account_combo = QComboBox()
        self.account_combo.addItem("Choose when paying", None)
        for account in services.accounts.list():
            self.account_combo.addItem(account.name, account.id)

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setFixedHeight(56)
        self.notes_edit.setPlaceholderText("Optional")
        self.active_check = QCheckBox("Active")
        self.active_check.setChecked(True)

        # Keys match the ``field`` names of the service's ValidationError.
        self.fields: dict[str, FormField] = {
            "name": FormField("Name", self.name_edit),
            "amount": FormField(f"Amount ({services.base_currency})", self.amount_edit),
            "frequency": FormField("Frequency", self.frequency_combo),
            "next_payment_date": FormField("Next payment", self.date_edit),
            "category_id": FormField("Category", category_row, highlight=self.category_combo),
            "account_id": FormField("Usually paid from", self.account_combo),
            "notes": FormField("Notes", self.notes_edit),
        }
        self.form_error = QLabel()
        self.form_error.setObjectName("FormError")
        self.form_error.setWordWrap(True)
        self.form_error.hide()

        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.MD)
        grid.setVerticalSpacing(Spacing.SM)
        grid.addWidget(self.fields["name"], 0, 0, 1, 2)
        grid.addWidget(self.fields["amount"], 1, 0)
        grid.addWidget(self.fields["frequency"], 1, 1)
        grid.addWidget(self.fields["next_payment_date"], 2, 0)
        grid.addWidget(self.fields["category_id"], 2, 1)
        grid.addWidget(self.fields["account_id"], 3, 0, 1, 2)
        grid.addWidget(self.fields["notes"], 4, 0, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        for field in self.fields.values():
            grid.setAlignment(field, Qt.AlignmentFlag.AlignTop)

        note = QLabel("A subscription is a reminder: payments are only recorded when you confirm "
                      "them, so your balance never changes on its own.")
        note.setObjectName("MutedLabel")
        note.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save = buttons.button(QDialogButtonBox.StandardButton.Save)
        save.setText("Save changes" if subscription else "Add subscription")
        save.setObjectName("PrimaryButton")
        buttons.accepted.connect(self.submit)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        layout.addWidget(self.form_error)
        layout.addLayout(grid)
        if subscription is None:
            layout.addWidget(self.active_check)
        layout.addWidget(note)
        layout.addWidget(buttons)

        self._reload_categories(subscription.category_id if subscription else None)
        if subscription is not None:
            self._populate(subscription)

    @property
    def frequency(self) -> Frequency:
        # Qt hands StrEnum item data back as a plain str.
        return Frequency(self.frequency_combo.currentData())

    def create_category(self, name: str) -> None:
        try:
            category = self._services.categories.create(name, CategoryKind.EXPENSE)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, "Could not create category", str(exc))
            return
        self._reload_categories(category.id)

    def submit(self) -> bool:
        for field in self.fields.values():
            field.set_error(None)
        self.form_error.hide()
        service = self._services.subscriptions
        try:
            values = {
                "amount": parse_amount_text(self.amount_edit.text()),
                "frequency": self.frequency,
                "next_payment_date": self.date_edit.date().toPython(),
                "category_id": self.category_combo.currentData(),
                "account_id": self.account_combo.currentData(),
                "notes": self.notes_edit.toPlainText(),
            }
            if values["category_id"] is None:
                raise ValidationError("Choose a category.", "category_id")
            if self._original is None:
                self.saved = service.create(self.name_edit.text(),
                                            is_active=self.active_check.isChecked(), **values)
            else:
                self.saved = service.update(self._original.id, name=self.name_edit.text(),
                                            **values)
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

    def _populate(self, subscription: Subscription) -> None:
        self.name_edit.setText(subscription.name)
        self.amount_edit.setText(f"{subscription.amount.amount}")
        self.frequency_combo.setCurrentIndex(
            self.frequency_combo.findData(subscription.frequency.value))
        self.date_edit.setMinimumDate(
            to_qdate(min(subscription.next_payment_date,
                         self._services.today() - timedelta(days=SUBSCRIPTION_PAST_LIMIT_DAYS))))
        self.date_edit.setDate(to_qdate(subscription.next_payment_date))
        self.account_combo.setCurrentIndex(max(self.account_combo.findData(subscription.account_id), 0))
        self.notes_edit.setPlainText(subscription.notes)

    def _reload_categories(self, select_id: int | None) -> None:
        self.category_combo.clear()
        for category in self._services.categories.list(CategoryKind.EXPENSE, include_archived=True):
            if not category.is_archived or category.id == select_id:
                self.category_combo.addItem(category.name, category.id)
        self.category_combo.setPlaceholderText("No expense categories yet — click New…")
        index = self.category_combo.findData(select_id) if select_id is not None else 0
        self.category_combo.setCurrentIndex(index if index >= 0 else 0)

    def _prompt_new_category(self) -> None:
        name, accepted = QInputDialog.getText(self, "New expense category", "Category name:")
        if accepted and name.strip():
            self.create_category(name)

    def _show_form_error(self, message: str) -> None:
        self.form_error.setText(message)
        self.form_error.show()
