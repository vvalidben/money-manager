"""Settings page cards. Every rule is enforced by the services; cards only ask and show."""

import logging
import sys
from collections.abc import Sequence
from pathlib import Path

import PySide6
from PySide6.QtCore import QProcess, QStandardPaths, Qt, QUrl, Signal, qVersion
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from money_manager.core.config import AppConfig
from money_manager.core.resources import is_frozen
from money_manager.core.errors import MoneyManagerError
from money_manager.domain.enums import CategoryKind
from money_manager.domain.money import DEFAULT_CURRENCY
from money_manager.services import AppServices
from money_manager.services.category_rule_service import RuleEntry
from money_manager.services.data_service import SafetyCopy
from money_manager.ui import dialogs, motion
from money_manager.ui.components import Card, FlowRow, compact_combo
from money_manager.ui.formatting import format_date
from money_manager.ui.settings.reset_dialog import ResetDialog
from money_manager.ui.theme import Spacing, current_palette, resolve_palette

logger = logging.getLogger(__name__)

def open_folder(path: Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def documents_folder() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    return Path(location) if location else Path.home()


def _text(content: str, object_name: str = "CardBody") -> QLabel:
    label = QLabel(content)
    label.setObjectName(object_name)
    label.setWordWrap(True)
    # No maximum width: Qt sizes wrapped labels for the full width they are offered.
    return label


def _rows(rows: Sequence[tuple[str, str]]) -> QGridLayout:
    grid = QGridLayout()
    grid.setHorizontalSpacing(Spacing.LG)
    grid.setVerticalSpacing(Spacing.SM)
    grid.setContentsMargins(0, Spacing.SM, 0, 0)
    for row, (label, value) in enumerate(rows):
        name = QLabel(label)
        name.setObjectName("FieldLabel")
        shown = QLabel(value)
        shown.setObjectName("FieldValue")
        shown.setToolTip(value)  # long paths may be clipped
        shown.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # Long paths must not widen the page beyond the window.
        shown.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        grid.addWidget(name, row, 0)
        grid.addWidget(shown, row, 1)
    grid.setColumnStretch(1, 1)
    return grid


def _status_label() -> QLabel:
    label = QLabel()
    label.setObjectName("MutedLabel")
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    label.hide()
    return label


def _set_status(label: QLabel, message: str, *, error: bool = False) -> None:
    label.setText(message)
    label.setObjectName("FieldError" if error else "MutedLabel")
    label.style().unpolish(label)
    label.style().polish(label)
    label.setVisible(bool(message))


class StorageCard(Card):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__("Local data storage", parent)
        self._config = config
        self.body.addWidget(_text("Your financial data is stored only on this computer."))
        self.body.addLayout(_rows([
            ("Data folder", str(config.data_dir)),
            ("Database file", str(config.database_path)),
            ("Log files", str(config.log_dir)),
            ("Configuration file", str(config.config_file) if config.config_file else "None"),
        ]))
        self.body.addWidget(_text(
            "To keep the data somewhere else (for example a portable drive), set data_dir in "
            "MoneyManager.ini next to MoneyManager.exe, or start Money Manager with the "
            "environment variable MONEY_MANAGER_DATA_DIR set to that folder. "
            "The folder cannot be moved from inside the app, so that data is never lost halfway "
            "through a move; use Export backup and Import backup to copy data between folders.",
            "MutedLabel"))
        self.open_button = QPushButton("Open data folder")
        self.open_button.clicked.connect(lambda: open_folder(self._config.data_dir))
        row = QHBoxLayout()
        row.addWidget(self.open_button)
        row.addStretch(1)
        self.body.addLayout(row)


THEME_LABELS = (("dark", "Dark"), ("light", "Light"), ("system", "Same as Windows"))


def restart_application() -> None:
    """Start a new Money Manager and close this one (used to apply a new theme)."""
    arguments = sys.argv[1:] if is_frozen() else ["-m", "money_manager", *sys.argv[1:]]
    if QProcess.startDetached(sys.executable, arguments):
        QApplication.quit()


class AppearanceCard(Card):
    """Theme, and animations on or off (page entrances, counting figures, filling bars,
    notices)."""

    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__("Appearance", parent)
        self._settings = services.settings
        self.theme_combo = QComboBox()
        self.theme_combo.setAccessibleName("Theme")
        for key, label in THEME_LABELS:
            self.theme_combo.addItem(label, key)
        self.theme_combo.setMaximumWidth(260)
        self.theme_combo.currentIndexChanged.connect(self.save_theme)
        self.restart_note = _text("The new theme is used after a restart.", "MutedLabel")
        self.restart_note.setWordWrap(False)
        self.restart_button = QPushButton("Restart now")
        self.restart_button.clicked.connect(lambda: restart_application())
        theme_row = QHBoxLayout()
        theme_row.addWidget(self.theme_combo)
        theme_row.addWidget(self.restart_note)
        theme_row.addWidget(self.restart_button)
        theme_row.addStretch(1)
        self.body.addLayout(theme_row)
        self.animations_box = QCheckBox("Animations")
        self.animations_box.setAccessibleName("Animations")
        self.animations_box.toggled.connect(self.save)
        self.note = _text(
            "Tiles rise into place, figures count up, bars and rings fill, and a short "
            "notice confirms each change. Switch off for a still interface.", "MutedLabel")
        self.system_note = _text(
            "Windows' \"Show animations in Windows\" setting is off, so Money Manager "
            "stays still as well.", "MutedLabel")
        self.body.addWidget(self.animations_box)
        self.body.addWidget(self.note)
        self.body.addWidget(self.system_note)
        self.load()

    def load(self) -> None:
        self.animations_box.blockSignals(True)
        self.animations_box.setChecked(self._settings.animations_enabled())
        self.animations_box.blockSignals(False)
        self.system_note.setVisible(not motion.system_allows())
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentIndex(max(self.theme_combo.findData(self._settings.theme()), 0))
        self.theme_combo.blockSignals(False)
        self._show_restart()

    def _show_restart(self) -> None:
        """Offer a restart when the chosen theme is not the one on screen."""
        pending = resolve_palette(self.theme_combo.currentData()) != current_palette()
        self.restart_note.setVisible(pending)
        self.restart_button.setVisible(pending)

    def save_theme(self, _index: int) -> None:
        try:
            self._settings.set_theme(self.theme_combo.currentData())
        except MoneyManagerError as exc:
            dialogs.show_warning(self, "Could not save the setting", str(exc))
            self.load()
            return
        self._show_restart()

    def save(self, enabled: bool) -> None:
        try:
            self._settings.set_animations_enabled(enabled)
        except MoneyManagerError as exc:
            dialogs.show_warning(self, "Could not save the setting", str(exc))
            self.load()
            return
        motion.set_user_enabled(enabled)


class CurrencyCard(Card):
    changed = Signal()

    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__("Currency", parent)
        self._settings = services.settings
        self.combo = QComboBox()
        for info in self._settings.available_currencies():
            self.combo.addItem(info.label, info.code)
        self.combo.setMaximumWidth(320)
        self.combo.setAccessibleName("Currency")
        compact_combo(self.combo, 16)
        self.save_button = QPushButton("Use this currency")
        self.save_button.clicked.connect(self.save)
        row = QHBoxLayout()
        row.addWidget(self.combo)
        row.addWidget(self.save_button)
        row.addStretch(1)
        self.note = _text("", "MutedLabel")
        self.status_label = _status_label()
        self.body.addLayout(row)
        self.body.addWidget(self.note)
        self.body.addWidget(self.status_label)
        self.load()

    def load(self) -> None:
        current = self._settings.currency()
        self.combo.setCurrentIndex(self.combo.findData(current))
        changeable = self._settings.can_change_currency()
        self.combo.setEnabled(changeable)
        self.save_button.setEnabled(changeable)
        if changeable:
            self.note.setText(
                f"All amounts use one currency: currently {current} (the default is "
                f"{DEFAULT_CURRENCY}). It can be changed until the first account is created. "
                "Money Manager never converts between currencies and uses no exchange rates.")
        else:
            self.note.setText(
                f"Your accounts use {current}. The currency cannot be changed once accounts "
                "exist, because Money Manager never converts amounts between currencies.")

    def save(self) -> None:
        code = str(self.combo.currentData())
        try:
            saved = self._settings.set_currency(code)
        except MoneyManagerError as exc:
            _set_status(self.status_label, str(exc), error=True)
            self.load()
            return
        _set_status(self.status_label, f"Currency set to {saved}.")
        self.changed.emit()


class DataCard(Card):
    changed = Signal()  # the data was replaced by an import

    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__("Export and import", parent)
        self._services = services
        self.body.addWidget(_text(
            "A backup contains all of your data: accounts, transactions, allocations, goals, "
            "subscriptions, investments, settings and the AI insight history. It is a readable "
            "JSON file that restores everything exactly. API keys are never included."))
        self.body.addWidget(_text(
            "Backups and CSV exports contain your financial data unencrypted. Store them "
            "somewhere safe.", "PrivacyNotice"))
        self.export_button = QPushButton("Export backup…")
        self.export_button.setObjectName("PrimaryButton")
        self.export_button.clicked.connect(self.export_backup)
        self.csv_button = QPushButton("Export transactions (CSV)…")
        self.csv_button.clicked.connect(self.export_csv)
        self.import_button = QPushButton("Import backup…")
        self.import_button.clicked.connect(self.import_backup)
        self.body.addWidget(FlowRow([self.export_button, self.csv_button, self.import_button]))
        self.status_label = _status_label()
        self.body.addWidget(self.status_label)

    def export_backup(self) -> None:
        suggested = documents_folder() / f"money-manager-backup-{self._services.today():%Y-%m-%d}.json"
        path = dialogs.ask_save_path(self, "Export backup", suggested,
                                     "Money Manager backup (*.json)")
        if path is None:
            return
        try:
            summary = self._services.data.export_backup(path)
        except MoneyManagerError as exc:
            _set_status(self.status_label, str(exc), error=True)
            return
        _set_status(self.status_label, f"Backup saved and verified: {summary.total_rows} "
                                       f"records in {path}.")

    def export_csv(self) -> None:
        suggested = (documents_folder()
                     / f"money-manager-transactions-{self._services.today():%Y-%m-%d}.csv")
        path = dialogs.ask_save_path(self, "Export transactions", suggested, "CSV file (*.csv)")
        if path is None:
            return
        try:
            count = self._services.data.export_transactions_csv(path)
        except MoneyManagerError as exc:
            _set_status(self.status_label, str(exc), error=True)
            return
        _set_status(self.status_label, f"{count} transactions exported to {path}.")

    def import_backup(self) -> None:
        path = dialogs.ask_open_path(self, "Import backup", documents_folder(),
                                     "Money Manager backup (*.json)")
        if path is None:
            return
        data = self._services.data
        try:
            summary = data.read_backup(path)
        except MoneyManagerError as exc:
            _set_status(self.status_label, str(exc), error=True)
            return
        exported = summary.exported_at[:16].replace("T", " ") or "an unknown date"
        message = (
            f"Replace ALL current data with this backup from {exported}?\n\n"
            f"The backup has {summary.count('accounts')} accounts, "
            f"{summary.count('transactions')} transactions, {summary.count('goals')} goals and "
            f"{summary.total_rows} records in total (currency: {summary.currency or 'not set'})."
            "\n\nYour current data is first saved to a safety backup next to the database.")
        if not dialogs.confirm_destructive(self, "Import backup", message, "Replace my data"):
            return
        try:
            result = data.import_backup(path)
        except MoneyManagerError as exc:
            _set_status(self.status_label, str(exc), error=True)
            return
        details = [f"The backup from {exported} was imported."]
        if result.safety_backup is not None:
            details.append(f"Your previous data was saved to:\n{result.safety_backup}")
        if result.consistency is not None and not result.consistency.is_consistent:
            details.append("Warning: some allocation balances in the imported data do not add "
                           "up. Check the Money / Allocations page.")
        dialogs.show_info(self, "Import complete", "\n\n".join(details))
        self.changed.emit()


PRIVACY_POINTS = (
    "Your financial data is stored only on this computer, in the database file shown above. "
    "Money Manager has no user account, no cloud sync and no telemetry.",
    "Local AI (Ollama) processes the financial summary on this computer; nothing is sent over "
    "the internet.",
    "Online AI (Anthropic) sends selected financial information — totals, rates, category "
    "spending and trends, never transaction descriptions or account names — to "
    "api.anthropic.com. You see exactly what would be sent and must confirm every request.",
    "Automatic AI uses the local model when it is available. If it falls back to online AI, "
    "each request still needs your confirmation.",
    "API keys are sensitive: anyone who has your key can use your Anthropic account at your "
    "cost. Money Manager keeps it in the Windows Credential Manager, never in the database, "
    "backups or logs. If you think it was exposed, remove it here and revoke it in the "
    "Anthropic Console.",
    "Backups and CSV exports contain your data unencrypted. The AI insight history is stored "
    "locally and included in backups; clear it on the AI Advisor page.",
)


class PrivacyCard(Card):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Privacy", parent)
        self.points = PRIVACY_POINTS
        for point in PRIVACY_POINTS:
            self.body.addWidget(_text(f"•  {point}"))


class ResetCard(Card):
    changed = Signal()  # all data was deleted

    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__("Reset application data", parent)
        self._services = services
        self.body.addWidget(_text(
            "Deletes every account, transaction, allocation, goal, subscription, investment, "
            "setting and AI insight. A safety backup of the database is written first. This "
            "cannot be undone from inside the app."))
        self.reset_button = QPushButton("Reset all data…")
        self.reset_button.setObjectName("DangerButton")
        self.reset_button.clicked.connect(self.reset)
        row = QHBoxLayout()
        row.addWidget(self.reset_button)
        row.addStretch(1)
        self.body.addLayout(row)

    def reset(self) -> None:
        dialog = ResetDialog(self._services, parent=self)
        if dialog.exec() != ResetDialog.DialogCode.Accepted or dialog.result_info is None:
            return
        result = dialog.result_info
        details = ["All data was deleted."]
        if result.safety_backup is not None:
            details.append(f"A safety backup was saved to:\n{result.safety_backup}")
        if result.api_key_removed:
            details.append("The saved API key was removed.")
        dialogs.show_info(self, "Reset complete", "\n\n".join(details))
        self.changed.emit()


class AboutCard(Card):
    def __init__(self, services: AppServices, config: AppConfig,
                 parent: QWidget | None = None) -> None:
        super().__init__("About Money Manager", parent)
        info = services.settings.application_info()
        created = info.database_created_at[:10] or "unknown"
        self.rows = [
            ("Version", f"{info.name} {info.version}"),
            ("Data schema", info.schema_revision),
            ("Database created", created),
            ("Currency", services.base_currency),
            ("Python", info.python_version),
            ("Qt / PySide6", f"{qVersion()} / {PySide6.__version__}"),
            ("SQLite", info.sqlite_version),
        ]
        self.body.addLayout(_rows(self.rows))
        self.body.addWidget(_text(
            "Money Manager works fully offline. The only network connections it can make are "
            "to a local Ollama server and, when you confirm a request, to Anthropic's API.",
            "MutedLabel"))


class SafetyCopiesCard(Card):
    """The automatic safety copies, with a way to restore one."""

    changed = Signal()  # the data was replaced by a restore

    def __init__(self, services: AppServices, config: AppConfig,
                 parent: QWidget | None = None) -> None:
        super().__init__("Safety copies", parent)
        self._services = services
        self._config = config
        self.body.addWidget(_text(
            "Money Manager saves a copy of all your data before every reset, import or "
            "restore, before an update changes how data is stored, and once a day. "
            "Restoring a copy replaces your current data, which is itself saved first, so "
            "a restore can be undone the same way."))
        self.list = QListWidget()
        self.list.setAccessibleName("Safety copies")
        self.list.setMinimumHeight(132)
        self.list.setMaximumHeight(220)
        self.list.currentRowChanged.connect(self._update_buttons)
        self.list.itemDoubleClicked.connect(lambda _item: self.restore())
        self.body.addWidget(self.list)
        self.empty_label = _text("No safety copies yet.", "MutedLabel")
        self.body.addWidget(self.empty_label)
        self.daily_box = QCheckBox("Save a copy automatically each day (the last 30 are kept)")
        self.daily_box.setAccessibleName("Daily copies")
        self.daily_box.toggled.connect(self._save_daily)
        self.body.addWidget(self.daily_box)
        self.restore_button = QPushButton("Restore\u2026")
        self.restore_button.clicked.connect(self.restore)
        self.folder_button = QPushButton("Open data folder")
        self.folder_button.clicked.connect(lambda: open_folder(self._config.data_dir))
        row = QHBoxLayout()
        row.addWidget(self.restore_button)
        row.addWidget(self.folder_button)
        row.addStretch(1)
        self.body.addLayout(row)
        self.status_label = _status_label()
        self.body.addWidget(self.status_label)
        self.copies: list[SafetyCopy] = []
        self.load()

    def _save_daily(self, enabled: bool) -> None:
        try:
            self._services.settings.set_daily_copies_enabled(enabled)
        except MoneyManagerError as exc:
            _set_status(self.status_label, str(exc), error=True)

    def load(self) -> None:
        self.daily_box.blockSignals(True)
        self.daily_box.setChecked(self._services.settings.daily_copies_enabled())
        self.daily_box.blockSignals(False)
        try:
            self.copies = self._services.data.safety_copies()
        except (MoneyManagerError, OSError) as exc:
            self.copies = []
            _set_status(self.status_label, f"Could not list the safety copies: {exc}", error=True)
        self.list.clear()
        for copy in self.copies:
            item = QListWidgetItem(safety_copy_text(copy))
            item.setToolTip(str(copy.path))
            self.list.addItem(item)
        self.list.setVisible(bool(self.copies))
        self.empty_label.setVisible(not self.copies)
        if self.copies:
            self.list.setCurrentRow(0)
        self._update_buttons()

    def selected(self) -> SafetyCopy | None:
        row = self.list.currentRow()
        return self.copies[row] if 0 <= row < len(self.copies) else None

    def _update_buttons(self) -> None:
        copy = self.selected()
        self.restore_button.setEnabled(copy is not None and copy.readable)

    def restore(self) -> None:
        copy = self.selected()
        if copy is None or not copy.readable:
            return
        message = (
            f"Replace ALL current data with this safety copy?\n\n{safety_copy_text(copy)}"
            "\n\nYour current data is first saved as a new safety copy, so you can come "
            "back to it.")
        if not dialogs.confirm_destructive(self, "Restore safety copy", message,
                                           "Replace my data"):
            return
        try:
            result = self._services.data.restore_safety_copy(copy.path)
        except MoneyManagerError as exc:
            _set_status(self.status_label, str(exc), error=True)
            return
        details = [f"Your data from {_when(copy)} was restored."]
        if result.safety_backup is not None:
            details.append(f"The data you had before was saved to:\n{result.safety_backup}")
        if result.consistency is not None and not result.consistency.is_consistent:
            details.append("Warning: some allocation balances in the restored data do not add "
                           "up. Check the Money / Allocations page.")
        dialogs.show_info(self, "Restore complete", "\n\n".join(details))
        self.changed.emit()


def _when(copy: SafetyCopy) -> str:
    local = copy.created_at.astimezone()
    return f"{format_date(local.date())}, {local:%H:%M}"


def safety_copy_text(copy: SafetyCopy) -> str:
    """"Before a reset · 16 Oct 2026, 12:35 · 1 account, 42 transactions"."""
    if not copy.readable:
        contents = "cannot be read"
    else:
        accounts = f"{copy.accounts} account{'' if copy.accounts == 1 else 's'}"
        transactions = (f"{copy.transactions} transaction"
                        f"{'' if copy.transactions == 1 else 's'}")
        contents = f"{accounts}, {transactions}"
    return f"{copy.reason_text} \u00b7 {_when(copy)} \u00b7 {contents}"


class CategoryRulesCard(Card):
    """Keywords that put matching descriptions in a category (used by imports)."""

    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__("Category rules", parent)
        self._services = services
        self.body.addWidget(_text(
            "When a bank statement is imported, a line whose description contains a keyword "
            "goes to that keyword's category. Rules are learned when you change an entry's "
            "category; you can also add them here."))
        self.list = QListWidget()
        self.list.setAccessibleName("Category rules")
        self.list.setMinimumHeight(110)
        self.list.setMaximumHeight(220)
        self.list.currentRowChanged.connect(lambda _row: self._update_buttons())
        self.body.addWidget(self.list)
        self.empty_label = _text("No rules yet.", "MutedLabel")
        self.body.addWidget(self.empty_label)
        self.add_button = QPushButton("Add rule\u2026")
        self.add_button.clicked.connect(self.add_rule)
        self.remove_button = QPushButton("Remove")
        self.remove_button.setObjectName("DangerButton")
        self.remove_button.clicked.connect(self.remove_rule)
        row = QHBoxLayout()
        row.addWidget(self.add_button)
        row.addWidget(self.remove_button)
        row.addStretch(1)
        self.body.addLayout(row)
        self.status_label = _status_label()
        self.body.addWidget(self.status_label)
        self.entries: list[RuleEntry] = []
        self.load()

    def load(self) -> None:
        try:
            self.entries = self._services.category_rules.entries()
        except MoneyManagerError as exc:
            self.entries = []
            _set_status(self.status_label, str(exc), error=True)
        self.list.clear()
        for entry in self.entries:
            kind = "income" if entry.rule.kind is CategoryKind.INCOME else "spending"
            self.list.addItem(f"\u201c{entry.rule.keyword}\u201d \u2192 {entry.category_name}"
                              f"  ({kind})")
        self.list.setVisible(bool(self.entries))
        self.empty_label.setVisible(not self.entries)
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.remove_button.setEnabled(0 <= self.list.currentRow() < len(self.entries))

    def add_rule(self) -> None:
        categories = self._services.categories.list()
        if not categories:
            _set_status(self.status_label, "Create a category first.", error=True)
            return
        labels = [f"{c.name} ({'income' if c.kind is CategoryKind.INCOME else 'spending'})"
                  for c in categories]
        keyword, ok = QInputDialog.getText(self, "Add rule", "Keyword in the description:")
        if not ok or not keyword.strip():
            return
        label, ok = QInputDialog.getItem(self, "Add rule", "Category:", labels, 0, False)
        if not ok:
            return
        category = categories[labels.index(label)]
        try:
            self._services.category_rules.add(keyword, category.id)
        except MoneyManagerError as exc:
            _set_status(self.status_label, str(exc), error=True)
            return
        _set_status(self.status_label, "")
        self.load()

    def remove_rule(self) -> None:
        row = self.list.currentRow()
        if not 0 <= row < len(self.entries):
            return
        try:
            self._services.category_rules.remove(self.entries[row].rule.id)
        except MoneyManagerError as exc:
            _set_status(self.status_label, str(exc), error=True)
            return
        self.load()
