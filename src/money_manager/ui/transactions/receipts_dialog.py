"""Receipts of one transaction: attach photos or PDFs, open them, remove them."""

import logging
import tempfile
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError
from money_manager.domain.entities import Transaction
from money_manager.domain.receipts import MAX_RECEIPT_BYTES, Receipt
from money_manager.services import AppServices
from money_manager.ui import dialogs
from money_manager.ui.formatting import format_date, format_money
from money_manager.ui.theme import Spacing
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

FILE_TYPES = "(*.jpg *.jpeg *.png *.webp *.gif *.bmp *.pdf)"


def size_text(size: int) -> str:
    return f"{size / 1024:.0f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"


def open_folder() -> Path:
    """Where a receipt is written to be opened by the system viewer."""
    return Path(tempfile.gettempdir()) / "MoneyManager receipts"


class ReceiptsDialog(QDialog):
    def __init__(self, services: AppServices, transaction: Transaction,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._services = services
        self._transaction = transaction
        self.changed = False
        self.receipts: list[Receipt] = []
        self.setWindowTitle(tr("Receipts"))
        self.setModal(True)
        self.setMinimumWidth(520)
        title = transaction.description or tr("This entry")
        heading = QLabel(f"{title} · {format_money(transaction.amount)} · "
                         f"{format_date(transaction.occurred_on)}")
        heading.setObjectName("CardHeading")
        heading.setWordWrap(True)
        note = QLabel(tr("Photos (JPG, PNG…) or PDFs up to {0} MB. They are kept with your data, "
                         "included in backups, and deleted with the entry.", MAX_RECEIPT_BYTES // (1024 * 1024)))
        note.setObjectName("MutedLabel")
        note.setWordWrap(True)
        self.list = QListWidget()
        self.list.setAccessibleName(tr("Receipts"))
        self.list.currentRowChanged.connect(lambda _row: self._update_buttons())
        self.list.itemDoubleClicked.connect(lambda _item: self.open_selected())
        self.empty_label = QLabel(tr("No receipts yet."))
        self.empty_label.setObjectName("MutedLabel")
        self.status_label = QLabel()
        self.status_label.setObjectName("FormError")
        self.status_label.setWordWrap(True)
        self.status_label.hide()
        self.add_button = QPushButton(tr("Attach…"))
        self.add_button.setObjectName("PrimaryButton")
        self.add_button.clicked.connect(self.attach)
        self.open_button = QPushButton(tr("Open"))
        self.open_button.clicked.connect(self.open_selected)
        self.remove_button = QPushButton(tr("Remove"))
        self.remove_button.setObjectName("DangerButton")
        self.remove_button.clicked.connect(self.remove_selected)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        row = QHBoxLayout()
        for button in (self.add_button, self.open_button, self.remove_button):
            row.addWidget(button)
        row.addStretch(1)
        row.addWidget(close)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        for widget in (heading, note, self.list, self.empty_label, self.status_label):
            layout.addWidget(widget)
        layout.addLayout(row)
        self.load()

    def load(self) -> None:
        try:
            self.receipts = self._services.receipts.list(self._transaction.id)
        except MoneyManagerError as exc:
            self._error(str(exc))
            self.receipts = []
        self.list.clear()
        for receipt in self.receipts:
            self.list.addItem(f"{receipt.file_name}  ·  {size_text(receipt.size)}")
        if self.receipts:
            self.list.setCurrentRow(0)
        self.list.setVisible(bool(self.receipts))
        self.empty_label.setVisible(not self.receipts)
        self._update_buttons()

    def _update_buttons(self) -> None:
        chosen = 0 <= self.list.currentRow() < len(self.receipts)
        self.open_button.setEnabled(chosen)
        self.remove_button.setEnabled(chosen)

    def _error(self, message: str) -> None:
        self.status_label.setText(message)
        self.status_label.setVisible(bool(message))

    def attach(self) -> None:
        path = dialogs.ask_open_path(self, tr("Attach a receipt"), Path.home(),
                                     f"{tr('Receipts')} {FILE_TYPES}")
        if path is None:
            return
        try:
            self._services.receipts.add(self._transaction.id, path)
        except MoneyManagerError as exc:
            self._error(str(exc))
            return
        self._error("")
        self.changed = True
        self.load()

    def open_selected(self) -> None:
        row = self.list.currentRow()
        if not 0 <= row < len(self.receipts):
            return
        try:
            path = self._services.receipts.export(self.receipts[row].id, open_folder())
        except MoneyManagerError as exc:
            self._error(str(exc))
            return
        self.open_file(path)

    def open_file(self, path: Path) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def remove_selected(self) -> None:
        row = self.list.currentRow()
        if not 0 <= row < len(self.receipts):
            return
        receipt = self.receipts[row]
        if not dialogs.confirm_destructive(self, tr("Remove receipt"),
                                           tr("Remove {0}?", receipt.file_name), tr("Remove")):
            return
        try:
            self._services.receipts.delete(receipt.id)
        except MoneyManagerError as exc:
            self._error(str(exc))
            return
        self.changed = True
        self.load()
