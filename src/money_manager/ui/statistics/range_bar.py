"""Time-range selector: 7 days … 1 year presets plus a custom range."""

from collections.abc import Callable
from datetime import date, timedelta

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QDateEdit, QHBoxLayout, QLabel, QPushButton, QWidget

from money_manager.domain.periods import StatsRange
from money_manager.ui.theme import Spacing
from money_manager.ui.transactions.filter_bar import to_qdate
from money_manager.core.i18n import tr

RANGE_LABELS = {
    StatsRange.DAYS_7: tr("7 days"),
    StatsRange.DAYS_30: tr("30 days"),
    StatsRange.MONTHS_3: tr("3 months"),
    StatsRange.MONTHS_6: tr("6 months"),
    StatsRange.YEAR_1: tr("1 year"),
    StatsRange.CUSTOM: tr("Custom"),
}
DEFAULT_RANGE = StatsRange.DAYS_30


class RangeBar(QWidget):
    """Segmented preset buttons; "Custom" reveals start/end date pickers."""

    changed = Signal()

    def __init__(self, today: Callable[[], date], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.buttons: dict[StatsRange, QPushButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for preset, label in RANGE_LABELS.items():
            button = QPushButton(label)
            button.setObjectName("SegmentButton")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, p=preset: self._on_preset(p))
            self._group.addButton(button)
            self.buttons[preset] = button
            layout.addWidget(button)
        self.buttons[DEFAULT_RANGE].setChecked(True)

        layout.addSpacing(Spacing.MD)
        end = today()
        self.start_edit = self._date_edit(end - timedelta(days=29), end)
        self.end_edit = self._date_edit(end, end)
        self.to_label = QLabel("to")
        self.to_label.setObjectName("MutedLabel")
        for widget in (self.start_edit, self.to_label, self.end_edit):
            layout.addWidget(widget)
            layout.addSpacing(Spacing.XS)
        self.start_edit.dateChanged.connect(self._on_dates_changed)
        self.end_edit.dateChanged.connect(self._on_dates_changed)
        layout.addStretch(1)
        self._preset = DEFAULT_RANGE
        self._update_custom_visibility()

    @property
    def preset(self) -> StatsRange:
        return self._preset

    def custom_dates(self) -> tuple[date, date]:
        return self.start_edit.date().toPython(), self.end_edit.date().toPython()

    def select(self, preset: StatsRange) -> None:
        self.buttons[preset].setChecked(True)
        self._on_preset(preset)

    def _on_preset(self, preset: StatsRange) -> None:
        self._preset = preset
        self._update_custom_visibility()
        self.changed.emit()

    def _on_dates_changed(self) -> None:
        self.end_edit.setMinimumDate(self.start_edit.date())
        if self._preset is StatsRange.CUSTOM:
            self.changed.emit()

    def _update_custom_visibility(self) -> None:
        custom = self._preset is StatsRange.CUSTOM
        for widget in (self.start_edit, self.to_label, self.end_edit):
            widget.setVisible(custom)

    @staticmethod
    def _date_edit(value: date, maximum: date) -> QDateEdit:
        edit = QDateEdit(to_qdate(value))
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("dd/MM/yyyy")
        edit.setMaximumDate(to_qdate(maximum))
        return edit
