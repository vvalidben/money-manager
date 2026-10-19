"""Dialogs for allocations: create one, and move money between them and Available.

The dialogs only collect input; the allocation services enforce every rule
(names, positive amounts, enough money in the source).
"""

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError, ValidationError
from money_manager.domain.entities import Allocation, AllocationTransfer
from money_manager.domain.money import parse_amount_text
from money_manager.domain.validation import MAX_ALLOCATION_NAME_LENGTH, MAX_TRANSFER_NOTE_LENGTH
from money_manager.services import AppServices
from money_manager.ui.allocations.view_model import AVAILABLE
from money_manager.ui.components import FormField
from money_manager.ui.theme import Spacing
from money_manager.ui.transactions.transaction_dialog import AMOUNT_INPUT_PATTERN, side_by_side


class _FormDialog(QDialog):
    """Shared layout: intro, fields, inline errors, Save/Cancel."""

    def __init__(self, title: str, intro: str, save_text: str,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(420)
        self.fields: dict[str, FormField] = {}
        self._intro = QLabel(intro)
        self._intro.setObjectName("CardBody")
        self._intro.setWordWrap(True)
        self.form_error = QLabel()
        self.form_error.setObjectName("FormError")
        self.form_error.setWordWrap(True)
        self.form_error.hide()
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        save = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        save.setText(save_text)
        save.setObjectName("PrimaryButton")
        save.setDefault(True)
        self.buttons.accepted.connect(self.submit)
        self.buttons.rejected.connect(self.reject)

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        layout.addWidget(self._intro)
        layout.addWidget(self.form_error)
        for field in self.fields.values():
            layout.addWidget(field)
        layout.addWidget(self.buttons)

    def _amount_field(self, services: AppServices, label: str) -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText("0.00")
        edit.setValidator(QRegularExpressionValidator(QRegularExpression(AMOUNT_INPUT_PATTERN),
                                                      self))
        currency = QLabel(services.base_currency)
        currency.setObjectName("MutedLabel")
        self.fields["amount"] = FormField(label, side_by_side(edit, currency), highlight=edit)
        return edit

    def submit(self) -> bool:  # pragma: no cover - overridden
        raise NotImplementedError

    def _clear(self) -> None:
        for field in self.fields.values():
            field.set_error(None)
        self.form_error.hide()

    def _show(self, exc: MoneyManagerError) -> None:
        field = self.fields.get(exc.field or "") if isinstance(exc, ValidationError) else None
        if field is not None:
            field.set_error(str(exc))
        else:
            self.form_error.setText(str(exc))
            self.form_error.show()


class AllocationDialog(_FormDialog):
    """Create an allocation, optionally moving money into it from Available."""

    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(
            "New allocation",
            "An allocation sets money aside for a purpose, such as bills or a holiday. The "
            "money stays in your accounts; it is only no longer Available to spend.",
            "Create allocation", parent)
        self._services = services
        self.saved: Allocation | None = None
        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(MAX_ALLOCATION_NAME_LENGTH)
        self.name_edit.setPlaceholderText("e.g. Bills, Holiday, Emergency fund")
        self.fields["name"] = FormField("Name", self.name_edit)
        self.amount_edit = self._amount_field(services, "Set aside now (from Available)")
        self.amount_edit.setText("0")
        self._build()

    def submit(self) -> bool:
        self._clear()
        try:
            self.saved = self._services.allocations.create(
                self.name_edit.text(),
                initial_amount=parse_amount_text(self.amount_edit.text() or "0", "amount"))
        except MoneyManagerError as exc:
            if isinstance(exc, ValidationError) and exc.field == "initial_amount":
                exc.field = "amount"
            self._show(exc)
            return False
        self.accept()
        return True


class MoveMoneyDialog(_FormDialog):
    """Move money between allocations and Available (the total never changes)."""

    def __init__(self, services: AppServices, *, from_id: int | None = None,
                 to_id: int | None = None, parent: QWidget | None = None) -> None:
        super().__init__(
            "Move money",
            "Moves money between your allocations and Available. Your accounts and your "
            "total balance do not change.", "Move", parent)
        self._services = services
        self.saved: AllocationTransfer | None = None
        allocations = services.allocations.list()
        self.from_combo, self.to_combo = QComboBox(), QComboBox()
        for combo in (self.from_combo, self.to_combo):
            combo.addItem(AVAILABLE, None)
            for allocation in allocations:
                combo.addItem(allocation.name, allocation.id)
        # "Available" is the first item (no id); findData(None) does not find it.
        self.from_combo.setCurrentIndex(0 if from_id is None else self.from_combo.findData(from_id))
        self.to_combo.setCurrentIndex(0 if to_id is None else self.to_combo.findData(to_id))
        self.fields["from_allocation_id"] = FormField("From", self.from_combo)
        self.fields["to_allocation_id"] = FormField("To", self.to_combo)
        self.amount_edit = self._amount_field(services, "Amount")
        self.note_edit = QLineEdit()
        self.note_edit.setMaxLength(MAX_TRANSFER_NOTE_LENGTH)
        self.note_edit.setPlaceholderText("Optional")
        self.fields["note"] = FormField("Note", self.note_edit)
        self._build()

    def submit(self) -> bool:
        self._clear()
        try:
            self.saved = self._services.transfers.transfer(
                from_allocation_id=self.from_combo.currentData(),
                to_allocation_id=self.to_combo.currentData(),
                amount=parse_amount_text(self.amount_edit.text(), "amount"),
                note=self.note_edit.text())
        except MoneyManagerError as exc:
            self._show(exc)
            return False
        self.accept()
        return True
