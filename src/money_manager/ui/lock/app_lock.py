"""The app lock: a screen over the whole window, opened with Windows Hello.

When the lock is on (Settings → App lock), Money Manager starts locked and
locks itself again after the chosen time without use, or on Ctrl+L. While
locked, the screen covers every page, open dialogs are closed and keyboard
shortcuts are ignored.

The lock keeps people who use your computer out of the app; it does not
encrypt the data file. If Windows Hello stops being available (e.g. the PIN
was removed — which itself needs your Windows password), the screen explains
it and lets you in rather than locking you out of your own data.
"""

import logging

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from money_manager.core.errors import MoneyManagerError
from money_manager.services.settings_service import SettingsService
from money_manager.ui.ai.background import BackgroundCall, run_in_background
from money_manager.ui.lock import hello
from money_manager.ui.lock.hello import HelloResult, HelloStatus, Verifier
from money_manager.ui.theme import Spacing
from money_manager.core.i18n import tr

logger = logging.getLogger(__name__)

UNLOCK_MESSAGE = tr("Unlock Money Manager")
AUTO_PROMPT_DELAY_MS = 350
_ACTIVITY = frozenset({QEvent.Type.MouseButtonPress, QEvent.Type.MouseMove,
                       QEvent.Type.KeyPress, QEvent.Type.Wheel})
_KEYS = frozenset({QEvent.Type.KeyPress, QEvent.Type.KeyRelease, QEvent.Type.Shortcut,
                   QEvent.Type.ShortcutOverride})


class LockScreen(QWidget):
    unlock_requested = Signal()
    open_requested = Signal()  # Windows Hello is unavailable: let the user in

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("ContentArea")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.title = QLabel(tr("Money Manager is locked"))
        self.title.setObjectName("EmptyHeading")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message = QLabel(tr("Confirm it's you with Windows Hello — your PIN, fingerprint "
                              "or face."))
        self.message.setObjectName("MutedLabel")
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setMaximumWidth(460)
        self.unlock_button = QPushButton(tr("Unlock with Windows Hello"))
        self.unlock_button.setObjectName("PrimaryButton")
        self.unlock_button.clicked.connect(self.unlock_requested)
        self.open_button = QPushButton(tr("Open without the lock"))
        self.open_button.clicked.connect(self.open_requested)
        self.open_button.hide()
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.MD)
        layout.addStretch(1)
        for widget in (self.title, self.message, self.unlock_button, self.open_button):
            layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        self.hide()

    def show_message(self, text: str) -> None:
        self.message.setText(text)

    def set_busy(self, busy: bool) -> None:
        self.unlock_button.setEnabled(not busy)
        self.unlock_button.setText(tr("Waiting for Windows Hello…") if busy
                                   else tr("Unlock with Windows Hello"))


class AppLock(QObject):
    locked_changed = Signal(bool)

    def __init__(self, host: QWidget, settings: SettingsService,
                 verifier: Verifier | None = None) -> None:
        super().__init__(host)
        self._host = host
        self._settings = settings
        self._verifier = verifier
        self.screen = LockScreen(host)
        self.screen.unlock_requested.connect(self.unlock)
        self.screen.open_requested.connect(self._open_without_lock)
        self._call: BackgroundCall | None = None
        self.locked = False
        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self._idle)
        self._filtering = False
        self.configure()

    @property
    def verifier(self) -> Verifier:
        if self._verifier is None:
            self._verifier = hello.default_verifier()
        return self._verifier

    def enabled(self) -> bool:
        try:
            return self._settings.app_lock_enabled()
        except MoneyManagerError:
            return False

    def configure(self) -> None:
        """Re-read the settings (after a change in Settings)."""
        self.idle_timer.stop()
        enabled = self.enabled()
        self._watch_activity(enabled or self.locked)
        if not enabled:
            return
        try:
            minutes = self._settings.lock_after_minutes()
        except MoneyManagerError:
            return
        if minutes:
            self.idle_timer.setInterval(minutes * 60_000)
            self.idle_timer.start()

    def _watch_activity(self, on: bool) -> None:
        """The application-wide filter runs only while the lock is in use."""
        app = QApplication.instance()
        if app is None or on == self._filtering:
            return
        if on:
            app.installEventFilter(self)
        else:
            app.removeEventFilter(self)
        self._filtering = on

    def lock(self, *, prompt: bool = False) -> bool:
        """Cover the window (when the lock is on); ``prompt`` asks Hello right away."""
        if self.locked or not self.enabled():
            return self.locked
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QDialog) and widget.isVisible():
                widget.reject()  # nothing stays readable above the lock screen
        self.locked = True
        self.idle_timer.stop()
        self._watch_activity(True)
        self.place()
        self.screen.open_button.hide()
        self.screen.show_message(tr("Confirm it's you with Windows Hello — your PIN, fingerprint "
                                 "or face."))
        self.screen.set_busy(False)
        self.screen.show()
        self.screen.raise_()
        self.screen.unlock_button.setFocus()
        logger.info("Money Manager locked")
        self.locked_changed.emit(True)
        if prompt:
            QTimer.singleShot(AUTO_PROMPT_DELAY_MS, self.unlock)
        return True

    def place(self) -> None:
        self.screen.setGeometry(self._host.rect())
        if self.locked:
            self.screen.raise_()

    def unlock(self) -> None:
        if not self.locked or (self._call is not None and self._call.running):
            return
        self.screen.set_busy(True)
        verifier = self.verifier
        self._call = run_in_background(lambda: verifier.verify(UNLOCK_MESSAGE),
                                       self._verified, self._failed, owner=self.screen)

    def _verified(self, result: HelloResult) -> None:
        self.screen.set_busy(False)
        if result is HelloResult.VERIFIED:
            self._release()
        elif result is HelloResult.CANCELED:
            self.screen.show_message(tr("Unlock was cancelled. Choose Unlock to try again."))
        elif result is HelloResult.FAILED:
            self.screen.show_message(tr("Windows Hello could not confirm it's you. Try again."))
        else:
            self._unavailable()

    def _failed(self, error: BaseException) -> None:
        logger.warning("Windows Hello check failed: %s", type(error).__name__)
        self.screen.set_busy(False)
        self._unavailable()

    def _unavailable(self) -> None:
        status = self.verifier.status()
        detail = (status.explanation if status is not HelloStatus.AVAILABLE
                  else tr("Windows Hello did not answer."))
        self.screen.show_message(
            tr("{0} You can open Money Manager without the lock and turn it off or set "
               "Windows Hello up again.", detail))
        self.screen.open_button.setVisible(status is not HelloStatus.AVAILABLE)

    def _open_without_lock(self) -> None:
        logger.warning("Opened without the lock: Windows Hello unavailable")
        self._release()

    def _release(self) -> None:
        self.locked = False
        self.screen.hide()
        logger.info("Money Manager unlocked")
        self.locked_changed.emit(False)
        self.configure()

    def _idle(self) -> None:
        self.lock()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        kind = event.type()
        if self.locked:
            # Keys only reach the lock screen; shortcuts below it are ignored.
            if kind in _KEYS and not self._on_screen(watched):
                return True
        elif kind in _ACTIVITY and self.idle_timer.isActive():
            self.idle_timer.start()  # restart the countdown
        return False

    def _on_screen(self, watched: QObject) -> bool:
        return isinstance(watched, QWidget) and (watched is self.screen
                                                 or self.screen.isAncestorOf(watched))
