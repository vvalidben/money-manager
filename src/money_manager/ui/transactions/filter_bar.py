"""Search box and filter controls that produce a ``TransactionFilter``."""

from collections.abc import Callable, Sequence
from datetime import date

from PySide6.QtCore import QDate, QTimer, Signal
from PySide6.QtWidgets import QComboBox, QDateEdit, QLineEdit, QPushButton, QSizePolicy, QWidget

from money_manager.domain.entities import Account, Category, TransactionFilter
from money_manager.domain.enums import TransactionType
from money_manager.domain.periods import DatePreset, preset_range
from money_manager.ui.components.flow import FlowLayout, compact_combo
from money_manager.ui.theme import Spacing
from money_manager.core.i18n import tr

SEARCH_DELAY_MS = 250

PERIOD_LABELS = {
    DatePreset.ALL_TIME: tr("All time"),
    DatePreset.THIS_MONTH: tr("This month"),
    DatePreset.LAST_MONTH: tr("Last month"),
    DatePreset.LAST_30_DAYS: tr("Last 30 days"),
    DatePreset.THIS_YEAR: tr("This year"),
    DatePreset.LAST_YEAR: tr("Last year"),
    DatePreset.CUSTOM: tr("Custom range…"),
}

# (label, types) — None means every type.
TYPE_OPTIONS: tuple[tuple[str, frozenset[TransactionType] | None], ...] = (
    (tr("All types"), None),
    (tr("Income"), frozenset({TransactionType.INCOME})),
    (tr("Expenses"), frozenset({TransactionType.EXPENSE})),
    (tr("Adjustments"), frozenset(t for t in TransactionType if t.is_adjustment)),
)


def to_qdate(value: date) -> QDate:
    return QDate(value.year, value.month, value.day)


class FilterBar(QWidget):
    """Emits ``changed`` whenever the resulting filter changes (search is debounced)."""

    changed = Signal()

    def __init__(self, today: Callable[[], date], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._today = today

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(tr("Search description, notes, category or amount"))
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMinimumWidth(240)
        self.search_edit.setAccessibleName(tr("Search transactions"))
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(SEARCH_DELAY_MS)
        self._search_timer.timeout.connect(self.changed)
        self.search_edit.textChanged.connect(lambda _text: self._search_timer.start())

        self.period_combo = QComboBox()
        for preset, label in PERIOD_LABELS.items():
            self.period_combo.addItem(label, preset)
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)

        start, end = today().replace(day=1), today()
        self.start_edit = self._date_edit(start)
        self.end_edit = self._date_edit(end)
        self.start_edit.dateChanged.connect(self._on_custom_range_changed)
        self.end_edit.dateChanged.connect(self._on_custom_range_changed)

        self.type_combo = QComboBox()
        for label, types in TYPE_OPTIONS:
            self.type_combo.addItem(label, types)
        self.type_combo.currentIndexChanged.connect(self.changed)

        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(170)
        self.category_combo.currentIndexChanged.connect(self.changed)

        self.account_combo = QComboBox()
        self.account_combo.currentIndexChanged.connect(self.changed)

        self.clear_button = QPushButton(tr("Clear filters"))
        self.clear_button.clicked.connect(self.clear)

        for combo, name in ((self.period_combo, tr("Period")), (self.type_combo, tr("Type")),
                            (self.category_combo, tr("Category")), (self.account_combo, tr("Account"))):
            combo.setAccessibleName(tr("Filter by {0}", name.lower()))
            compact_combo(combo, 10)
        self.start_edit.setAccessibleName(tr("From date"))
        self.end_edit.setAccessibleName(tr("To date"))

        # Wraps onto a second line in narrow windows instead of overlapping.
        layout = FlowLayout(self, Spacing.SM)
        policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        for widget in (
            self.search_edit,
            self.period_combo,
            self.start_edit,
            self.end_edit,
            self.type_combo,
            self.category_combo,
            self.account_combo,
            self.clear_button,
        ):
            layout.addWidget(widget)

        self.set_categories([])
        self.set_accounts([])
        self._update_custom_visibility()

    @property
    def period(self) -> DatePreset:
        # Qt hands StrEnum item data back as a plain str.
        return DatePreset(self.period_combo.currentData())

    def filters(self) -> TransactionFilter:
        preset = self.period
        if preset is DatePreset.CUSTOM:
            start, end = self.start_edit.date().toPython(), self.end_edit.date().toPython()
        else:
            start, end = preset_range(preset, self._today())
        return TransactionFilter(
            account_id=self.account_combo.currentData(),
            category_id=self.category_combo.currentData(),
            types=self.type_combo.currentData(),
            start=start,
            end=end,
            search=self.search_edit.text().strip(),
        )

    def is_filtered(self) -> bool:
        return self.filters() != TransactionFilter()

    def clear(self) -> None:
        widgets = (self.search_edit, self.period_combo, self.type_combo, self.category_combo,
                   self.account_combo)
        for widget in widgets:
            widget.blockSignals(True)
        self.search_edit.clear()
        self._search_timer.stop()
        self.period_combo.setCurrentIndex(0)
        self.type_combo.setCurrentIndex(0)
        self.category_combo.setCurrentIndex(0)
        self.account_combo.setCurrentIndex(0)
        for widget in widgets:
            widget.blockSignals(False)
        self._update_custom_visibility()
        self.changed.emit()

    def set_categories(self, categories: Sequence[Category]) -> None:
        """Offer every category, including archived ones, keeping the selection."""
        options = [
            (f"{c.name} ({c.kind.value}{', archived' if c.is_archived else ''})", c.id)
            for c in sorted(categories, key=lambda c: (c.kind.value, c.name.casefold()))
        ]
        self._replace_items(self.category_combo, tr("All categories"), options)

    def set_accounts(self, accounts: Sequence[Account]) -> None:
        self._replace_items(self.account_combo, tr("All accounts"), [(a.name, a.id) for a in accounts])
        # Only worth showing when there is a choice to make.
        self.account_combo.setVisible(len(accounts) > 1)

    def _replace_items(
        self, combo: QComboBox, all_label: str, options: Sequence[tuple[str, int]]
    ) -> None:
        selected = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(all_label, None)
        for label, value in options:
            combo.addItem(label, value)
        index = combo.findData(selected) if selected is not None else 0
        combo.setCurrentIndex(max(index, 0))
        combo.blockSignals(False)
        if selected is not None and index < 0:  # the selected item disappeared
            self.changed.emit()

    def _date_edit(self, value: date) -> QDateEdit:
        edit = QDateEdit(to_qdate(value))
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("dd/MM/yyyy")
        return edit

    def _on_period_changed(self) -> None:
        self._update_custom_visibility()
        self.changed.emit()

    def _on_custom_range_changed(self) -> None:
        # Keep the range valid: the end can never be before the start.
        self.end_edit.setMinimumDate(self.start_edit.date())
        if self.period is DatePreset.CUSTOM:
            self.changed.emit()

    def _update_custom_visibility(self) -> None:
        custom = self.period is DatePreset.CUSTOM
        self.start_edit.setVisible(custom)
        self.end_edit.setVisible(custom)
