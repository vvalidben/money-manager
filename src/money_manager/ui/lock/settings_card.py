"""Settings → App lock: Windows Hello on start and after a while without use.

Turning the lock on or off asks Windows Hello first, so it cannot be switched
on without working, nor switched off by someone who finds the app open.
"""

import logging

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from money_manager.core.errors import MoneyManagerError
from money_manager.services import AppServices
from money_manager.services.settings_service import LOCK_AFTER_CHOICES
from money_manager.ui.ai.background import BackgroundCall, run_in_background
from money_manager.ui.components.card import Card
from money_manager.ui.lock import hello
from money_manager.ui.lock.hello import HelloResult, HelloStatus

logger = logging.getLogger(__name__)


def lock_after_label(minutes: int) -> str:
    if minutes == 0:
        return "Only when I lock it"
    return "After 1 minute without use" if minutes == 1 else f"After {minutes} minutes without use"


class AppLockCard(Card):
    changed = Signal()  # the lock was switched or its time changed
    lock_requested = Signal()

    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__("App lock", parent)
        self._settings = services.settings
        self._call: BackgroundCall | None = None
        self.status: HelloStatus | None = None
        intro = QLabel("Ask for Windows Hello (PIN, fingerprint or face) when Money Manager "
                       "opens and after a while without use. This keeps other people who use "
                       "your computer out of the app; it does not encrypt the data file.")
        intro.setObjectName("CardBody")
        intro.setWordWrap(True)
        self.lock_box = QCheckBox("Lock Money Manager with Windows Hello")
        self.lock_box.setAccessibleName("Lock with Windows Hello")
        self.lock_box.toggled.connect(self._toggled)
        self.after_combo = QComboBox()
        self.after_combo.setAccessibleName("When to lock")
        for minutes in LOCK_AFTER_CHOICES:
            self.after_combo.addItem(lock_after_label(minutes), minutes)
        self.after_combo.currentIndexChanged.connect(self._after_changed)
        self.lock_now_button = QPushButton("Lock now")
        self.lock_now_button.setToolTip("Ctrl+L")
        self.lock_now_button.clicked.connect(self.lock_requested)
        row = QHBoxLayout()
        row.addWidget(self.after_combo)
        row.addWidget(self.lock_now_button)
        row.addStretch(1)
        self.status_label = QLabel()
        self.status_label.setObjectName("MutedLabel")
        self.status_label.setWordWrap(True)
        for widget in (intro, self.lock_box):
            self.body.addWidget(widget)
        self.body.addLayout(row)
        self.body.addWidget(self.status_label)
        self.load()

    def load(self) -> None:
        try:
            enabled = self._settings.app_lock_enabled()
            minutes = self._settings.lock_after_minutes()
        except MoneyManagerError as exc:
            self.status_label.setText(str(exc))
            return
        self.status = hello.default_verifier().status()
        self.lock_box.blockSignals(True)
        self.lock_box.setChecked(enabled)
        self.lock_box.blockSignals(False)
        self.after_combo.blockSignals(True)
        self.after_combo.setCurrentIndex(max(self.after_combo.findData(minutes), 0))
        self.after_combo.blockSignals(False)
        self._update(enabled)
        if self.status is not HelloStatus.AVAILABLE:
            self.status_label.setText(self.status.explanation)

    def _update(self, enabled: bool) -> None:
        busy = self._call is not None and self._call.running
        self.lock_box.setEnabled(not busy and (enabled or self.status is HelloStatus.AVAILABLE))
        self.after_combo.setEnabled(enabled and not busy)
        self.lock_now_button.setEnabled(enabled and not busy)

    def _toggled(self, wanted: bool) -> None:
        # Show the current state until Windows Hello has answered.
        self.lock_box.blockSignals(True)
        self.lock_box.setChecked(not wanted)
        self.lock_box.blockSignals(False)
        self.status_label.setText("Confirm with Windows Hello…")
        message = "Turn on the Money Manager lock" if wanted else "Turn off the Money Manager lock"
        verifier = hello.default_verifier()
        self._call = run_in_background(lambda: verifier.verify(message),
                                       lambda result: self._answered(wanted, result),
                                       self._failed, owner=self)
        self._update(not wanted)

    def _answered(self, wanted: bool, result: HelloResult) -> None:
        if result is not HelloResult.VERIFIED:
            self.status_label.setText(
                "Not changed: Windows Hello did not confirm it's you." if result is not
                HelloResult.UNAVAILABLE else (self.status or HelloStatus.UNSUPPORTED).explanation)
            self._update(not wanted)
            return
        try:
            self._settings.set_app_lock_enabled(wanted)
        except MoneyManagerError as exc:
            self.status_label.setText(str(exc))
            self._update(not wanted)
            return
        self.lock_box.blockSignals(True)
        self.lock_box.setChecked(wanted)
        self.lock_box.blockSignals(False)
        self.status_label.setText("The lock is on." if wanted else "The lock is off.")
        self._update(wanted)
        self.changed.emit()

    def _failed(self, error: BaseException) -> None:
        logger.warning("Windows Hello check failed: %s", type(error).__name__)
        self.status_label.setText("Not changed: Windows Hello did not answer.")
        self._update(self.lock_box.isChecked())

    def _after_changed(self, _index: int) -> None:
        try:
            self._settings.set_lock_after_minutes(self.after_combo.currentData())
        except MoneyManagerError as exc:
            self.status_label.setText(str(exc))
            return
        self.changed.emit()
