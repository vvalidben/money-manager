"""Import a bank statement (CSV): choose columns, preview, then import.

Columns and the date format are detected and can be changed; the preview is
rebuilt on every change. ``StatementImportService`` marks lines already
recorded and records the rest; the dialog only collects choices and shows
results.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError
from money_manager.domain.enums import CategoryKind
from money_manager.domain.money import Money
from money_manager.domain.statement import (
    DATE_FORMATS,
    StatementColumns,
    StatementTable,
    detect_date_format,
    guess_columns,
)
from money_manager.services import AppServices
from money_manager.services.statement_import_service import (
    ImportOutcome,
    PreviewLine,
    StatementPreview,
)
from money_manager.ui.components import FormField
from money_manager.ui.formatting import format_date, format_signed_money
from money_manager.ui.theme import Spacing
from money_manager.ui.transactions.transaction_dialog import side_by_side

PREVIEW_LIMIT = 500
FORMAT_LABELS = {"%d/%m/%Y": "31/12/2026", "%Y-%m-%d": "2026-12-31", "%d-%m-%Y": "31-12-2026",
                 "%d.%m.%Y": "31.12.2026", "%d/%m/%y": "31/12/26", "%Y/%m/%d": "2026/12/31",
                 "%m/%d/%Y": "12/31/2026 (month first)"}
ONE_COLUMN, TWO_COLUMNS = "one", "two"


class ImportStatementDialog(QDialog):
    def __init__(self, services: AppServices, path: Path, table: StatementTable,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._services = services
        self._path = path
        self._table = table
        self.preview: StatementPreview | None = None
        self.outcome: ImportOutcome | None = None
        self.setWindowTitle(f"Import {path.name}")
        self.setModal(True)
        self.resize(860, 640)

        intro = QLabel("Choose the account and check the columns. Lines already recorded in the "
                       "account are skipped, so importing the same statement twice adds nothing.")
        intro.setObjectName("CardBody")
        intro.setWordWrap(True)

        self.account_combo = QComboBox()
        for account in services.accounts.list():
            self.account_combo.addItem(account.name, account.id)

        header = list(table.header)
        self.date_combo = self._column_combo(header)
        self.description_combo = self._column_combo(header)
        self.amount_combo = self._column_combo(header)
        self.debit_combo, self.credit_combo = self._column_combo(header), self._column_combo(header)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("One column (minus = money out)", ONE_COLUMN)
        self.mode_combo.addItem("Separate debit and credit columns", TWO_COLUMNS)
        self.format_combo = QComboBox()
        for fmt in DATE_FORMATS:
            self.format_combo.addItem(FORMAT_LABELS[fmt], fmt)

        self.expense_combo = QComboBox()
        self.income_combo = QComboBox()
        expense_new, income_new = QToolButton(), QToolButton()
        expense_new.setText("New…")
        income_new.setText("New…")
        expense_new.clicked.connect(lambda: self._new_category(CategoryKind.EXPENSE))
        income_new.clicked.connect(lambda: self._new_category(CategoryKind.INCOME))
        self._category_names = {c.id: c.name for c in
                                services.categories.list(include_archived=True)}
        self._fill_categories()

        self.fields = {
            "account_id": FormField("Into account", self.account_combo),
            "date": FormField("Date column", self.date_combo),
            "format": FormField("Date format", self.format_combo),
            "description": FormField("Description column", self.description_combo),
            "mode": FormField("Amounts", self.mode_combo),
            "amount": FormField("Amount column", self.amount_combo),
            "debit": FormField("Debit column (money out)", self.debit_combo),
            "credit": FormField("Credit column (money in)", self.credit_combo),
            "expense": FormField("Spending goes to", side_by_side(self.expense_combo, expense_new),
                                 highlight=self.expense_combo),
            "income": FormField("Income goes to", side_by_side(self.income_combo, income_new),
                                highlight=self.income_combo),
        }
        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.MD)
        grid.setVerticalSpacing(Spacing.SM)
        for index, key in enumerate(("account_id", "date", "format", "description", "mode",
                                     "amount", "debit", "credit", "expense", "income")):
            grid.addWidget(self.fields[key], index // 3, index % 3, Qt.AlignmentFlag.AlignTop)
        for column in range(3):
            grid.setColumnStretch(column, 1)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Line", "Date", "Description", "Amount", "Category",
                                              "Status"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for column in (0, 1, 3, 4, 5):
            header_view.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.summary_label = QLabel()
        self.summary_label.setObjectName("MutedLabel")
        self.form_error = QLabel()
        self.form_error.setObjectName("FormError")
        self.form_error.setWordWrap(True)
        self.form_error.hide()

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                        | QDialogButtonBox.StandardButton.Cancel)
        self.import_button = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        self.import_button.setObjectName("PrimaryButton")
        self.import_button.setDefault(True)
        self.buttons.accepted.connect(self.submit)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        layout.addWidget(intro)
        layout.addWidget(self.form_error)
        layout.addLayout(grid)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.buttons)

        self._apply_guess()
        for combo in (self.account_combo, self.date_combo, self.description_combo,
                      self.amount_combo, self.debit_combo, self.credit_combo, self.mode_combo,
                      self.format_combo, self.expense_combo, self.income_combo):
            combo.currentIndexChanged.connect(self.refresh_preview)
        self.mode_combo.currentIndexChanged.connect(self._show_amount_fields)
        self._show_amount_fields()
        self.refresh_preview()

    # ------------------------------------------------------------ choices

    @staticmethod
    def _column_combo(header: list[str]) -> QComboBox:
        combo = QComboBox()
        for index, name in enumerate(header):
            combo.addItem(name or f"Column {index + 1}", index)
        return combo

    def _apply_guess(self) -> None:
        guess = guess_columns(self._table.header)
        count = len(self._table.header)
        if guess is None:  # a sensible start the user can change
            guess = StatementColumns(0, min(1, count - 1), amount=min(2, count - 1))
        self.date_combo.setCurrentIndex(guess.date)
        self.description_combo.setCurrentIndex(guess.description)
        if guess.split_amounts:
            self.mode_combo.setCurrentIndex(1)
            if guess.debit is not None:
                self.debit_combo.setCurrentIndex(guess.debit)
            if guess.credit is not None:
                self.credit_combo.setCurrentIndex(guess.credit)
        else:
            assert guess.amount is not None
            self.amount_combo.setCurrentIndex(guess.amount)
        detected = detect_date_format([row[guess.date] for row in self._table.rows
                                       if len(row) > guess.date])
        if detected is not None:
            self.format_combo.setCurrentIndex(self.format_combo.findData(detected))

    def _show_amount_fields(self) -> None:
        split = self.mode_combo.currentData() == TWO_COLUMNS
        self.fields["amount"].setVisible(not split)
        self.fields["debit"].setVisible(split)
        self.fields["credit"].setVisible(split)

    def columns(self) -> StatementColumns:
        if self.mode_combo.currentData() == TWO_COLUMNS:
            return StatementColumns(self.date_combo.currentData(),
                                    self.description_combo.currentData(),
                                    debit=self.debit_combo.currentData(),
                                    credit=self.credit_combo.currentData())
        return StatementColumns(self.date_combo.currentData(), self.description_combo.currentData(),
                                amount=self.amount_combo.currentData())

    def _fill_categories(self, select: tuple[CategoryKind, int] | None = None) -> None:
        for kind, combo in ((CategoryKind.EXPENSE, self.expense_combo),
                            (CategoryKind.INCOME, self.income_combo)):
            current = combo.currentData()
            combo.clear()
            for category in self._services.categories.list(kind):
                combo.addItem(category.name, category.id)
            wanted = select[1] if select is not None and select[0] is kind else current
            if wanted is not None and combo.findData(wanted) >= 0:
                combo.setCurrentIndex(combo.findData(wanted))

    def _new_category(self, kind: CategoryKind) -> None:
        name, accepted = QInputDialog.getText(self, f"New {kind.value} category",
                                              "Category name:")
        if not accepted or not name.strip():
            return
        try:
            category = self._services.categories.create(name, kind)
        except MoneyManagerError as exc:
            self._error(str(exc))
            return
        self._category_names[category.id] = category.name
        self._fill_categories((kind, category.id))

    # ------------------------------------------------------------ preview

    def refresh_preview(self) -> None:
        self.form_error.hide()
        account_id = self.account_combo.currentData()
        if account_id is None:
            self._error("Create an account first.")
            self.import_button.setEnabled(False)
            return
        try:
            self.preview = self._services.statements.preview(
                self._table, account_id, self.columns(), self.format_combo.currentData())
        except MoneyManagerError as exc:
            self._error(str(exc))
            return
        rows = [(str(p.line.row), format_date(p.line.occurred_on), p.line.description,
                 format_signed_money(Money(p.line.amount, self._services.base_currency)),
                 self._category_text(p), "Already recorded" if p.duplicate else "New")
                for p in self.preview.lines]
        rows += [(str(p.row), "", "", "", "", p.message) for p in self.preview.problems]
        rows.sort(key=lambda r: int(r[0]))
        self.table.setRowCount(min(len(rows), PREVIEW_LIMIT))
        for index, row in enumerate(rows[:PREVIEW_LIMIT]):
            for column, text in enumerate(row):
                item = QTableWidgetItem(text)
                if column == 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                          | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(index, column, item)
        new = len(self.preview.new_lines)
        self.summary_label.setText(
            f"{new} new · {self.preview.duplicate_count} already recorded · "
            f"{len(self.preview.problems)} cannot be read"
            + (f" · {self.preview.matched_count} sorted by your category rules"
               if self.preview.matched_count else "")
            + (f" · showing the first {PREVIEW_LIMIT} lines" if len(rows) > PREVIEW_LIMIT else ""))
        self.import_button.setText(f"Import {new} entr{'y' if new == 1 else 'ies'}")
        self.import_button.setEnabled(new > 0)

    def _category_text(self, line: PreviewLine) -> str:
        """The rule's category, or the import's default for the line's direction."""
        if line.duplicate:
            return ""
        if line.category_id is not None:
            return self._category_names.get(line.category_id, "?")
        default = self.income_combo if line.line.amount > 0 else self.expense_combo
        return f"{default.currentText()} (default)" if default.currentText() else "—"

    def _error(self, message: str) -> None:
        self.form_error.setText(message)
        self.form_error.show()

    # ------------------------------------------------------------ import

    def submit(self) -> bool:
        if self.preview is None or not self.preview.new_lines:
            return False
        expense, income = self.expense_combo.currentData(), self.income_combo.currentData()
        if expense is None or income is None:
            self._error("Choose a category for spending and for income (or create one with "
                        "New…). You can change categories of single entries later.")
            return False
        try:
            self.outcome = self._services.statements.import_lines(
                self.account_combo.currentData(), self.preview.new_lines,
                expense_category_id=expense, income_category_id=income, source=self._path.name)
        except MoneyManagerError as exc:
            self._error(str(exc))
            return False
        self.accept()
        return True
