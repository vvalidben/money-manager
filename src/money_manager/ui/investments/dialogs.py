"""Investment dialogs: create/edit, contribution/withdrawal and value.

They only collect input; ``InvestmentService`` enforces every rule and its
``ValidationError.field`` decides which input shows the message.
"""

from collections.abc import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
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
from money_manager.domain.investments import EntryKind, InvestmentKind, InvestmentPosition
from money_manager.domain.money import parse_amount_text
from money_manager.domain.validation import MAX_INVESTMENT_NAME_LENGTH, MAX_INVESTMENT_NOTE_LENGTH
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.components import FormField
from money_manager.ui.goals.goal_dialog import amount_edit
from money_manager.ui.investments.view_model import KIND_TEXT
from money_manager.ui.theme import Spacing
from money_manager.ui.transactions.filter_bar import to_qdate
from money_manager.core.i18n import tr


class _FormDialog(QDialog):
    """Shared layout: optional intro, form error banner, fields, OK/Cancel."""

    def __init__(self, title: str, ok_text: str, parent: QWidget | None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(460)
        self.fields: dict[str, FormField] = {}
        self.form_error = QLabel()
        self.form_error.setObjectName("FormError")
        self.form_error.setWordWrap(True)
        self.form_error.hide()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        self._layout.setSpacing(Spacing.MD)
        self._layout.addWidget(self.form_error)
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok.setText(ok_text)
        ok.setObjectName("PrimaryButton")
        self._buttons.accepted.connect(self.submit)
        self._buttons.rejected.connect(self.reject)

    def add_text(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("CardBody")
        label.setWordWrap(True)
        self._layout.addWidget(label)
        return label

    def add_field(self, key: str, field: FormField) -> None:
        self.fields[key] = field
        self._layout.addWidget(field)

    def finish(self) -> None:
        self._layout.addWidget(self._buttons)

    def submit(self) -> bool:
        raise NotImplementedError

    def run(self, action: Callable[[], object]) -> bool:
        for field in self.fields.values():
            field.set_error(None)
        self.form_error.hide()
        try:
            action()
        except ValidationError as exc:
            field = self.fields.get(exc.field or "")
            if field is not None and not field.isHidden():
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


def _date_edit(services: AppServices) -> QDateEdit:
    edit = QDateEdit(to_qdate(services.today()))
    edit.setCalendarPopup(True)
    edit.setDisplayFormat("dd/MM/yyyy")
    edit.setMaximumDate(to_qdate(services.today()))
    return edit


def _note_edit() -> QLineEdit:
    edit = QLineEdit()
    edit.setMaxLength(MAX_INVESTMENT_NOTE_LENGTH)
    edit.setPlaceholderText(tr("Optional"))
    return edit


class InvestmentDialog(_FormDialog):
    def __init__(self, services: AppServices, *, position: InvestmentPosition | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(tr("Edit investment") if position else tr("New investment"),
                         tr("Save changes") if position else tr("Add investment"), parent)
        self._services = services
        self._original = position
        self.saved: InvestmentPosition | None = None

        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(MAX_INVESTMENT_NAME_LENGTH)
        self.name_edit.setPlaceholderText(tr("e.g. MSCI World ETF"))
        self.kind_combo = QComboBox()
        for kind, label in KIND_TEXT.items():
            self.kind_combo.addItem(label, kind.value)
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setFixedHeight(60)
        self.notes_edit.setPlaceholderText(tr("Optional — broker, wallet, where the gold is kept …"))
        self.add_field("name", FormField(tr("Name"), self.name_edit))
        self.add_field("kind", FormField(tr("Type"), self.kind_combo))
        self.add_field("notes", FormField(tr("Notes"), self.notes_edit))
        self.add_text(tr("Values are entered by you — the app does not fetch market prices."))
        self.finish()

        if position is not None:
            self.name_edit.setText(position.investment.name)
            self.kind_combo.setCurrentIndex(self.kind_combo.findData(position.investment.kind.value))
            self.notes_edit.setPlainText(position.investment.notes)

    @property
    def kind(self) -> InvestmentKind:
        return InvestmentKind(self.kind_combo.currentData())  # Qt returns StrEnum data as str

    def submit(self) -> bool:
        service = self._services.investments

        def save() -> None:
            if self._original is None:
                self.saved = service.create(self.name_edit.text(), self.kind,
                                            self.notes_edit.toPlainText())
            else:
                self.saved = service.update(self._original.investment.id,
                                            name=self.name_edit.text(), kind=self.kind,
                                            notes=self.notes_edit.toPlainText())

        return self.run(save)


class EntryDialog(_FormDialog):
    """Add a contribution (optionally paid from an account) or a withdrawal."""

    def __init__(self, services: AppServices, position: InvestmentPosition, kind: EntryKind,
                 parent: QWidget | None = None) -> None:
        name = position.investment.name
        is_contribution = kind is EntryKind.CONTRIBUTION
        super().__init__(f"{'Add contribution to' if is_contribution else 'Withdraw from'} {name}",
                         tr("Add contribution") if is_contribution else tr("Record withdrawal"), parent)
        self._services = services
        self._position = position
        self.kind = kind

        self.amount_edit = amount_edit()
        self.date_edit = _date_edit(services)
        self.note_edit = _note_edit()
        self.add_field("amount", FormField(tr("Amount ({0})", services.base_currency), self.amount_edit))
        self.add_field("occurred_on", FormField(tr("Date"), self.date_edit))
        self.add_field("note", FormField(tr("Note"), self.note_edit))

        if is_contribution:
            self.from_account_check = QCheckBox(
                tr("Paid from one of my accounts (records an investment expense)"))
            self._layout.addWidget(self.from_account_check)
            self.account_combo = QComboBox()
            for account in services.accounts.list():
                self.account_combo.addItem(account.name, account.id)
            self.account_combo.setPlaceholderText(tr("No accounts yet"))
            self.category_combo = QComboBox()
            self.new_category_button = QToolButton()
            self.new_category_button.setText(tr("New…"))
            self.new_category_button.clicked.connect(self._prompt_new_category)
            category_row = QWidget()
            row_layout = QHBoxLayout(category_row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(self.category_combo, 1)
            row_layout.addWidget(self.new_category_button)
            self.allocation_combo = QComboBox()
            self.allocation_combo.addItem(tr("Available (not allocated)"), None)
            for allocation in services.allocations.list():
                self.allocation_combo.addItem(allocation.name, allocation.id)
            self.add_field("account_id", FormField(tr("From account"), self.account_combo))
            self.add_field("category_id", FormField(tr("Investment category"), category_row,
                                                    highlight=self.category_combo))
            self.add_field("allocation_id", FormField(tr("Paid from"), self.allocation_combo))
            self.hint = self.add_text("")
            self.from_account_check.toggled.connect(self._update_source)
            self.from_account_check.setChecked(bool(services.accounts.list()))
            self._reload_categories(None)
            self._update_source()
        else:
            self.add_text(tr("A withdrawal lowers the amount invested. It does not change your "
                          "balance: if the money came back to one of your accounts, record that "
                          "as a transaction too."))
        self.finish()

    def create_category(self, name: str) -> None:
        """Create an expense category, mark it as an investment category and select it."""
        try:
            category = self._services.categories.create(name, CategoryKind.EXPENSE)
            self._services.categories.set_investment(category.id, True)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, tr("Could not create category"), str(exc))
            return
        self._reload_categories(category.id)

    def submit(self) -> bool:
        service = self._services.investments
        investment_id = self._position.investment.id

        def save() -> None:
            amount = parse_amount_text(self.amount_edit.text())
            on = self.date_edit.date().toPython()
            note = self.note_edit.text()
            if self.kind is EntryKind.WITHDRAWAL:
                service.add_withdrawal(investment_id, amount, on, note=note)
            elif self.from_account_check.isChecked():
                account_id = self.account_combo.currentData()
                if account_id is None:
                    raise ValidationError(tr("Choose an account."), "account_id")
                service.add_contribution(
                    investment_id, amount, on, note=note, account_id=account_id,
                    category_id=self.category_combo.currentData(),
                    allocation_id=self.allocation_combo.currentData(),
                )
            else:
                service.add_contribution(investment_id, amount, on, note=note)

        return self.run(save)

    def _update_source(self) -> None:
        paid = self.from_account_check.isChecked()
        for key in ("account_id", "category_id", "allocation_id"):
            self.fields[key].setVisible(paid)
        self.hint.setText(
            tr("Records one expense in the investment category, so your balance goes down and the "
            "statistics count it as investing.")
            if paid else
            tr("External money (e.g. invested before you started tracking): your balance does not "
            "change.")
        )

    def _reload_categories(self, select_id: int | None) -> None:
        self.category_combo.clear()
        for category in self._services.categories.list(CategoryKind.EXPENSE):
            if category.is_investment:
                self.category_combo.addItem(category.name, category.id)
        self.category_combo.setPlaceholderText(tr("No investment categories — click New…"))
        index = self.category_combo.findData(select_id) if select_id is not None else 0
        self.category_combo.setCurrentIndex(index if index >= 0 else 0)

    def _prompt_new_category(self) -> None:
        name, accepted = QInputDialog.getText(self, tr("New investment category"), tr("Category name:"))
        if accepted and name.strip():
            self.create_category(name)


class ValueDialog(_FormDialog):
    def __init__(self, services: AppServices, position: InvestmentPosition,
                 parent: QWidget | None = None) -> None:
        super().__init__(tr("Update value · {0}", position.investment.name), tr("Save value"), parent)
        self._services = services
        self._position = position
        self.add_text(tr("Enter what the investment is worth, e.g. from your broker's app. "
                      "A value entered for the same day replaces the earlier one."))
        self.value_edit = amount_edit()
        if position.current_value is not None:
            self.value_edit.setText(f"{position.current_value.amount}")
        self.date_edit = _date_edit(services)
        self.note_edit = _note_edit()
        self.add_field("value", FormField(tr("Current value ({0})", services.base_currency),
                                          self.value_edit))
        self.add_field("valued_on", FormField(tr("Value on"), self.date_edit))
        self.add_field("note", FormField(tr("Note"), self.note_edit))
        self.finish()

    def submit(self) -> bool:
        def save() -> None:
            self._services.investments.set_value(
                self._position.investment.id,
                parse_amount_text(self.value_edit.text(), "value"),
                self.date_edit.date().toPython(),
                note=self.note_edit.text(),
            )

        return self.run(save)
