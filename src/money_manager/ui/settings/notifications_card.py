"""Settings → Notifications: reminders and the notification-area icon."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QLabel, QWidget

from money_manager.core.errors import MoneyManagerError
from money_manager.core.i18n import tr
from money_manager.services import AppServices
from money_manager.ui.components.card import Card


class NotificationsCard(Card):
    changed = Signal()

    def __init__(self, services: AppServices, parent: QWidget | None = None) -> None:
        super().__init__(tr("Notifications"), parent)
        self._settings = services.settings
        intro = QLabel(tr("Windows notifications for payments due today or tomorrow, budgets "
                          "near or over their limit, loans to repay within three days, and a "
                          "balance projected below zero in the next 30 days. Each reminder is "
                          "shown once, while Money Manager is running."))
        intro.setObjectName("CardBody")
        intro.setWordWrap(True)
        self.reminders_box = QCheckBox(tr("Show reminders"))
        self.reminders_box.toggled.connect(self._save_reminders)
        self.tray_box = QCheckBox(tr("Keep Money Manager running in the notification area when "
                                     "the window is closed"))
        self.tray_box.toggled.connect(self._save_tray)
        self.status_label = QLabel()
        self.status_label.setObjectName("MutedLabel")
        self.status_label.setWordWrap(True)
        for widget in (intro, self.reminders_box, self.tray_box, self.status_label):
            self.body.addWidget(widget)
        self.load()

    def load(self) -> None:
        for box, value in ((self.reminders_box, self._settings.reminders_enabled),
                           (self.tray_box, self._settings.keep_in_tray)):
            box.blockSignals(True)
            try:
                box.setChecked(value())
            except MoneyManagerError:
                box.setChecked(False)
            box.blockSignals(False)

    def _save_reminders(self, enabled: bool) -> None:
        self._save(self._settings.set_reminders_enabled, enabled)

    def _save_tray(self, enabled: bool) -> None:
        self._save(self._settings.set_keep_in_tray, enabled)

    def _save(self, setter, enabled: bool) -> None:  # noqa: ANN001
        try:
            setter(enabled)
        except MoneyManagerError as exc:
            self.status_label.setText(str(exc))
            self.load()
            return
        self.status_label.setText("")
        self.changed.emit()
