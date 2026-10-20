"""Settings → Updates: an opt-in check for a newer version, and a link to it."""

import logging

from PySide6.QtCore import Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QWidget

from money_manager import __version__
from money_manager.core.errors import MoneyManagerError
from money_manager.services import AppServices
from money_manager.services.update_service import UpdateInfo
from money_manager.ui.ai.background import BackgroundCall, run_in_background
from money_manager.ui.components.card import Card
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)


class UpdatesCard(Card):
    update_found = Signal(str)  # the newer version

    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(tr("Updates"), parent)
        self._updates = services.updates
        self._call: BackgroundCall | None = None
        self.info: UpdateInfo | None = None
        intro = QLabel(tr("This is version {0}. Money Manager can ask GitHub once a day whether a "
                          "newer version exists. Only that question is sent — nothing about you or "
                          "your data (GitHub sees your IP address, as with any web request). "
                          "Nothing is downloaded by itself.", __version__))
        intro.setObjectName("CardBody")
        intro.setWordWrap(True)
        self.auto_box = QCheckBox(tr("Check for a newer version once a day"))
        self.auto_box.toggled.connect(self._toggled)
        self.check_button = QPushButton(tr("Check now"))
        self.check_button.clicked.connect(self.check_now)
        self.download_button = QPushButton(tr("Download\u2026"))
        self.download_button.setObjectName("PrimaryButton")
        self.download_button.clicked.connect(self.open_download)
        self.download_button.hide()
        row = QHBoxLayout()
        row.addWidget(self.check_button)
        row.addWidget(self.download_button)
        row.addStretch(1)
        self.status_label = QLabel()
        self.status_label.setObjectName("MutedLabel")
        self.status_label.setWordWrap(True)
        self.body.addWidget(intro)
        self.body.addWidget(self.auto_box)
        self.body.addLayout(row)
        self.body.addWidget(self.status_label)
        self.load()

    def load(self) -> None:
        self.auto_box.blockSignals(True)
        try:
            self.auto_box.setChecked(self._updates.enabled())
        except MoneyManagerError:
            self.auto_box.setChecked(False)
        self.auto_box.blockSignals(False)

    def _toggled(self, enabled: bool) -> None:
        try:
            self._updates.set_enabled(enabled)
        except MoneyManagerError as exc:
            self.status_label.setText(str(exc))
            self.load()

    def check_now(self) -> None:
        if self._call is not None and self._call.running:
            return
        self.check_button.setEnabled(False)
        self.status_label.setText(tr("Checking\u2026"))
        self._call = run_in_background(self._updates.check, self.show_result, self._failed,
                                       owner=self)

    def show_result(self, info: UpdateInfo) -> None:
        self.check_button.setEnabled(True)
        self.info = info
        if info.is_newer:
            self.status_label.setText(tr("Version {0} is available (you have {1}).", info.latest, info.current))
            self.download_button.show()
            self.update_found.emit(info.latest)
        else:
            self.status_label.setText(tr("You have the latest version ({0}).", info.current))
            self.download_button.hide()

    def _failed(self, error: BaseException) -> None:
        self.check_button.setEnabled(True)
        message = str(error) if isinstance(error, MoneyManagerError) else (
            tr("The check failed."))
        logger.info("Update check failed: %s", type(error).__name__)
        self.status_label.setText(message)

    def open_download(self) -> None:
        if self.info is not None:
            QDesktopServices.openUrl(QUrl(self.info.url))
