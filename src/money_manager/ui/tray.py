"""The notification-area (tray) icon: reminders as Windows notifications, and a
place for Money Manager to keep running when its window is closed."""

import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from money_manager.core.i18n import tr
from money_manager.domain.reminders import Reminder

logger = logging.getLogger(__name__)

NOTIFICATION_MS = 10_000


class TrayController(QObject):
    open_requested = Signal(str)  # page key ("" keeps the current page)
    lock_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._last_page = ""
        self.icon: QSystemTrayIcon | None = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        app = QApplication.instance()
        window_icon = app.windowIcon() if isinstance(app, QApplication) else QIcon()
        self.icon = QSystemTrayIcon(window_icon, self)
        self.icon.setToolTip("Money Manager")
        self.menu = QMenu(parent)
        for text, signal in ((tr("Open Money Manager"), self.open_requested),
                             (tr("Lock now"), self.lock_requested),
                             (tr("Quit Money Manager"), self.quit_requested)):
            action = QAction(text, self.menu)
            if signal is self.open_requested:
                action.triggered.connect(lambda: self.open_requested.emit(""))
            else:
                action.triggered.connect(signal)
            self.menu.addAction(action)
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._activated)
        self.icon.messageClicked.connect(lambda: self.open_requested.emit(self._last_page))

    @property
    def available(self) -> bool:
        return self.icon is not None

    def set_visible(self, visible: bool) -> None:
        if self.icon is not None:
            self.icon.setVisible(visible)

    def notify(self, reminder: Reminder) -> None:
        if self.icon is None:
            return
        self._last_page = reminder.page
        self.icon.showMessage(reminder.title, reminder.body,
                              QSystemTrayIcon.MessageIcon.Information, NOTIFICATION_MS)

    def message(self, title: str, body: str) -> None:
        if self.icon is not None:
            self._last_page = ""
            self.icon.showMessage(title, body, QSystemTrayIcon.MessageIcon.Information,
                                  NOTIFICATION_MS)

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.open_requested.emit("")
