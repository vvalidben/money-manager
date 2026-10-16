"""Add / edit transaction dialog.

The dialog only collects input. Every rule (positive amount, category kind,
dates, allocation funds, ...) is enforced by ``TransactionService``; its
``ValidationError.field`` decides which input shows the message.
"""

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
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
from money_manager.domain.entities import Account, Category, Transaction, TransactionDraft
from money_manager.domain.enums import TransactionType
from money_manager.domain.money import parse_amount_text
from money_manager.domain.validation import MAX_DESCRIPTION_LENGTH
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.components import FormField
from money_manager.ui.formatting import type_label
from money_manager.ui.theme import Spacing
from money_manager.ui.transactions.filter_bar import to_qdate

# Digits, grouping spaces and at most one decimal separator with two decimals.
AMOUNT_INPUT_PATTERN = r"[0-9   ]*([.,][0-9]{0,2})?"


class TransactionDialog(QDialog):
    def __init__(
        self,
        services: AppServices,
        *,
        transaction: Transaction | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._services = services
        self._original = transaction
        self.saved: Transaction | None = None

        self.setWindowTitle("Edit transaction" if transaction else "Add transaction")
        self.setModal(True)
        self.setMinimumWidth(520)

        self._accounts: list[Account] = services.accounts.list()
        self._categories: list[Category] = services.categories.list(include_archived=True)

        self.type_combo = QComboBox()
        for transaction_type in (
            TransactionType.EXPENSE,
            TransactionType.INCOME,
            TransactionType.ADJUSTMENT_IN,
            TransactionType.ADJUSTMENT_OUT,
        ):
            self.type_combo.addItem(type_label(transaction_type), transaction_type)

        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("0.00")
        self.amount_edit.setValidator(
            QRegularExpressionValidator(QRegularExpression(AMOUNT_INPUT_PATTERN), self)
        )
        self.currency_label = QLabel(services.base_currency)
        self.currency_label.setObjectName("MutedLabel")
        amount_row = _row(self.amount_edit, self.currency_label)

        self.category_combo = QComboBox()
        self.new_category_button = QToolButton()
        self.new_category_button.setText("New…")
        self.new_category_button.clicked.connect(self._prompt_new_category)
        category_row = _row(self.category_combo, self.new_category_button, stretch_first=True)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setMaximumDate(to_qdate(services.today()))

        self.account_combo = QComboBox()
        for account in self._accounts:
            self.account_combo.addItem(account.name, account.id)

        self.allocation_combo = QComboBox()

        self.description_edit = QLineEdit()
        self.description_edit.setMaxLength(MAX_DESCRIPTION_LENGTH)
        self.description_edit.setPlaceholderText("e.g. Groceries at Marjane")

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setFixedHeight(64)
        self.notes_edit.setPlaceholderText("Optional")

        # Keys match the ``field`` names used by the service's ValidationError.
        self.fields: dict[str, FormField] = {
            "type": FormField("Type", self.type_combo),
            "amount": FormField("Amount", amount_row, highlight=self.amount_edit),
            "category_id": FormField("Category", category_row, highlight=self.category_combo),
            "occurred_on": FormField("Date", self.date_edit),
            "account_id": FormField("Account", self.account_combo),
            "allocation_id": FormField("Paid from", self.allocation_combo),
            "description": FormField("Description", self.description_edit),
            "notes": FormField("Notes", self.notes_edit),
        }
        self.fields["account_id"].setVisible(len(self._accounts) > 1)

        self.form_error = QLabel()
        self.form_error.setObjectName("FormError")
        self.form_error.setWordWrap(True)
        self.form_error.hide()

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.save_button = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setText("Save changes" if transaction else "Add transaction")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.setDefault(True)
        self.buttons.accepted.connect(self.submit)
        self.buttons.rejected.connect(self.reject)

        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.MD)
        grid.setVerticalSpacing(Spacing.SM)
        grid.addWidget(self.fields["type"], 0, 0)
        grid.addWidget(self.fields["amount"], 0, 1)
        grid.addWidget(self.fields["category_id"], 1, 0)
        grid.addWidget(self.fields["occurred_on"], 1, 1)
        grid.addWidget(self.fields["account_id"], 2, 0)
        grid.addWidget(self.fields["allocation_id"], 2, 1)
        grid.addWidget(self.fields["description"], 3, 0, 1, 2)
        grid.addWidget(self.fields["notes"], 4, 0, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        # Keep side-by-side fields aligned when only one of them shows an error.
        for field in self.fields.values():
            grid.setAlignment(field, Qt.AlignmentFlag.AlignTop)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        layout.addWidget(self.form_error)
        layout.addLayout(grid)
        layout.addWidget(self.buttons)

        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self.account_combo.currentIndexChanged.connect(self._on_account_changed)
        for key, signal in (
            ("amount", self.amount_edit.textChanged),
            ("description", self.description_edit.textChanged),
            ("notes", self.notes_edit.textChanged),
            ("occurred_on", self.date_edit.dateChanged),
            ("category_id", self.category_combo.currentIndexChanged),
            ("allocation_id", self.allocation_combo.currentIndexChanged),
        ):
            signal.connect(lambda *_args, key=key: self.fields[key].set_error(None))

        self._populate(transaction)

    # ----------------------------------------------------------------- input

    @property
    def selected_type(self) -> TransactionType:
        # Qt hands StrEnum item data back as a plain str.
        return TransactionType(self.type_combo.currentData())

    def build_draft(self) -> TransactionDraft:
        """Collect the inputs; raises ``ValidationError`` if the amount is unreadable."""
        return TransactionDraft(
            account_id=self.account_combo.currentData(),
            type=self.selected_type,
            amount=parse_amount_text(self.amount_edit.text()),
            occurred_on=self.date_edit.date().toPython(),
            category_id=(
                self.category_combo.currentData()
                if self.selected_type.category_kind is not None
                else None
            ),
            description=self.description_edit.text(),
            notes=self.notes_edit.toPlainText(),
            allocation_id=(
                None if self.selected_type.is_adjustment else self.allocation_combo.currentData()
            ),
        )

    def submit(self) -> bool:
        """Save through the service; show errors inline and stay open on failure."""
        self._clear_errors()
        try:
            draft = self.build_draft()
            if self._original is None:
                self.saved = self._services.transactions.create(draft)
            else:
                self.saved = self._services.transactions.update(self._original.id, draft)
        except ValidationError as exc:
            self._show_error(exc)
            return False
        except MoneyManagerError as exc:
            self._show_form_error(str(exc))
            return False
        self.accept()
        return True

    def create_category(self, name: str) -> Category | None:
        """Create a category of the kind the current type needs and select it."""
        kind = self.selected_type.category_kind
        if kind is None:
            return None
        try:
            category = self._services.categories.create(name, kind)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, "Could not create category", str(exc))
            return None
        self._categories.append(category)
        self._reload_categories(select_id=category.id)
        return category

    # --------------------------------------------------------------- helpers

    def _populate(self, transaction: Transaction | None) -> None:
        if transaction is None:
            self.date_edit.setDate(to_qdate(self._services.today()))
            self._on_type_changed()
            self._on_account_changed()
            return
        self.type_combo.setCurrentIndex(self.type_combo.findData(transaction.type))
        self.account_combo.setCurrentIndex(max(self.account_combo.findData(transaction.account_id), 0))
        self._on_type_changed()
        self._on_account_changed()
        self.amount_edit.setText(f"{transaction.amount.amount}")
        self.date_edit.setDate(to_qdate(transaction.occurred_on))
        if transaction.category_id is not None:
            self.category_combo.setCurrentIndex(self.category_combo.findData(transaction.category_id))
        self.allocation_combo.setCurrentIndex(
            max(self.allocation_combo.findData(transaction.allocation_id), 0)
        )
        self.description_edit.setText(transaction.description)
        self.notes_edit.setPlainText(transaction.notes)

    def _on_type_changed(self) -> None:
        transaction_type = self.selected_type
        needs_category = transaction_type.category_kind is not None
        self.fields["category_id"].setVisible(needs_category)
        self.fields["allocation_id"].setVisible(not transaction_type.is_adjustment)
        self.fields["allocation_id"].label.setText(
            "Put into" if transaction_type.sign > 0 else "Paid from"
        )
        if needs_category:
            self._reload_categories()
        self._reload_allocations()

    def _on_account_changed(self) -> None:
        account = next((a for a in self._accounts if a.id == self.account_combo.currentData()), None)
        if account is not None:
            self.date_edit.setMinimumDate(to_qdate(account.opening_date))

    def _reload_categories(self, select_id: int | None = None) -> None:
        kind = self.selected_type.category_kind
        keep_id = select_id or self.category_combo.currentData()
        original_id = self._original.category_id if self._original else None
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        for category in sorted(self._categories, key=lambda c: c.name.casefold()):
            # Archived categories only appear when the transaction already uses them.
            if category.kind is kind and (not category.is_archived or category.id == original_id):
                self.category_combo.addItem(category.name, category.id)
        self.category_combo.setPlaceholderText(
            f"No {kind.value} categories yet — click New…" if kind else ""
        )
        self.category_combo.setCurrentIndex(self.category_combo.findData(keep_id) if keep_id else 0)
        if self.category_combo.currentIndex() < 0 and self.category_combo.count():
            self.category_combo.setCurrentIndex(0)
        self.category_combo.blockSignals(False)

    def _reload_allocations(self) -> None:
        selected = self.allocation_combo.currentData()
        original_id = self._original.allocation_id if self._original else None
        self.allocation_combo.blockSignals(True)
        self.allocation_combo.clear()
        self.allocation_combo.addItem("Available (not allocated)", None)
        for allocation in self._services.allocations.list(include_archived=True):
            if not allocation.is_archived or allocation.id == original_id:
                self.allocation_combo.addItem(allocation.name, allocation.id)
        self.allocation_combo.setCurrentIndex(max(self.allocation_combo.findData(selected), 0))
        self.allocation_combo.blockSignals(False)

    def _prompt_new_category(self) -> None:
        kind = self.selected_type.category_kind
        if kind is None:
            return
        name, accepted = QInputDialog.getText(
            self, f"New {kind.value} category", "Category name:"
        )
        if accepted and name.strip():
            self.create_category(name)

    def _clear_errors(self) -> None:
        for field in self.fields.values():
            field.set_error(None)
        self.form_error.hide()

    def _show_error(self, exc: ValidationError) -> None:
        field = self.fields.get(exc.field or "")
        # isHidden (explicitly hidden) rather than isVisible, which is also
        # False before the dialog is first shown.
        if field is not None and not field.isHidden():
            field.set_error(str(exc))
            field.widget.setFocus()
        else:
            self._show_form_error(str(exc))

    def _show_form_error(self, message: str) -> None:
        self.form_error.setText(message)
        self.form_error.show()


def _row(first: QWidget, second: QWidget, *, stretch_first: bool = True) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(Spacing.SM)
    layout.addWidget(first, 1 if stretch_first else 0)
    layout.addWidget(second)
    return container
