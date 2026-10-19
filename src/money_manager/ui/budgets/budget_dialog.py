"""Create a budget or change its monthly limit.

The dialog only collects input; ``BudgetService`` enforces every rule.
"""

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QInputDialog,
    QLabel,
    QLineEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError, ValidationError
from money_manager.domain.budgets import Budget
from money_manager.domain.enums import CategoryKind
from money_manager.domain.money import parse_amount_text
from money_manager.services import AppServices
from money_manager.ui.components import FormField
from money_manager.ui.theme import Spacing
from money_manager.ui.transactions.transaction_dialog import AMOUNT_INPUT_PATTERN, side_by_side


class BudgetDialog(QDialog):
    def __init__(self, services: AppServices, *, category_id: int | None = None,
                 current_limit: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._services = services
        self._editing = category_id is not None
        self.saved: Budget | None = None
        self.setWindowTitle("Change budget" if self._editing else "New budget")
        self.setModal(True)
        self.setMinimumWidth(420)

        self.category_combo = QComboBox()
        self.category_combo.setAccessibleName("Category")
        self.new_category_button = QToolButton()
        self.new_category_button.setText("New…")
        self.new_category_button.clicked.connect(self._prompt_new_category)
        self._fill_categories(category_id)
        if self._editing:
            self.category_combo.setEnabled(False)
            self.new_category_button.hide()

        self.amount_edit = QLineEdit(current_limit)
        self.amount_edit.setPlaceholderText("0.00")
        self.amount_edit.setValidator(
            QRegularExpressionValidator(QRegularExpression(AMOUNT_INPUT_PATTERN), self))
        currency = QLabel(services.base_currency)
        currency.setObjectName("MutedLabel")

        self.fields: dict[str, FormField] = {
            "category_id": FormField("Category", side_by_side(
                self.category_combo, self.new_category_button), highlight=self.category_combo),
            "amount": FormField("Monthly limit", side_by_side(self.amount_edit, currency),
                                highlight=self.amount_edit),
        }
        note = QLabel("Compared with this category's spending in the current calendar month.")
        note.setObjectName("MutedLabel")
        note.setWordWrap(True)
        self.form_error = QLabel()
        self.form_error.setObjectName("FormError")
        self.form_error.setWordWrap(True)
        self.form_error.hide()

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.save_button = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setText("Save budget")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.setDefault(True)
        self.buttons.accepted.connect(self.submit)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        layout.addWidget(self.form_error)
        layout.addWidget(self.fields["category_id"])
        layout.addWidget(self.fields["amount"])
        layout.addWidget(note)
        layout.addWidget(self.buttons)
        self.amount_edit.textChanged.connect(lambda *_a: self.fields["amount"].set_error(None))

    def _fill_categories(self, selected: int | None) -> None:
        budgeted = {s.budget.category_id for s in self._services.budgets.overview().statuses}
        self.category_combo.clear()
        for category in self._services.categories.list():
            if category.kind is not CategoryKind.EXPENSE:
                continue
            if category.id in budgeted and category.id != selected:
                continue  # one budget per category
            self.category_combo.addItem(category.name, category.id)
        if selected is not None:
            self.category_combo.setCurrentIndex(self.category_combo.findData(selected))

    def _prompt_new_category(self) -> None:
        name, accepted = QInputDialog.getText(self, "New expense category", "Category name:")
        if not accepted or not name.strip():
            return
        try:
            category = self._services.categories.create(name, CategoryKind.EXPENSE)
        except MoneyManagerError as exc:
            self.fields["category_id"].set_error(str(exc))
            return
        self._fill_categories(category.id)

    def submit(self) -> bool:
        for field in self.fields.values():
            field.set_error(None)
        self.form_error.hide()
        category_id = self.category_combo.currentData()
        if category_id is None:
            self.fields["category_id"].set_error(
                "Choose a category, or create one with New….")
            return False
        try:
            self.saved = self._services.budgets.set(category_id,
                                                    parse_amount_text(self.amount_edit.text()))
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
