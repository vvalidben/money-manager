"""The app lock: Windows Hello on start, after idle time and on demand."""

from collections.abc import Iterator

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QDialog

from money_manager.core.config import AppConfig
from money_manager.core.errors import ValidationError
from money_manager.services import AppServices
from money_manager.ui.lock.hello import HelloResult, HelloStatus
from money_manager.ui.main_window import MainWindow
from money_manager.ui.pages import DASHBOARD_PAGE_KEY, SETTINGS_PAGE_KEY, SettingsPage
from tests.conftest import FakeVerifier
from tests.ui.support import wait_until


@pytest.fixture
def lock_on(app_services: AppServices) -> AppServices:
    app_services.settings.set_app_lock_enabled(True)
    return app_services


def _window(config: AppConfig, services: AppServices, **kwargs: bool) -> MainWindow:
    window = MainWindow(config, services, **kwargs)
    window.resize(1100, 760)
    window.show()
    return window


@pytest.fixture
def window(qapp: QApplication, app_config: AppConfig,
           lock_on: AppServices) -> Iterator[MainWindow]:
    widget = _window(app_config, lock_on)
    yield widget
    widget.close()
    widget.deleteLater()


class TestSettings:
    def test_defaults(self, app_services: AppServices) -> None:
        assert app_services.settings.app_lock_enabled() is False
        assert app_services.settings.lock_after_minutes() == 5

    def test_lock_time_choices(self, app_services: AppServices) -> None:
        assert app_services.settings.set_lock_after_minutes(15) == 15
        assert app_services.settings.lock_after_minutes() == 15
        for wrong in (7, True, -1):
            with pytest.raises(ValidationError):
                app_services.settings.set_lock_after_minutes(wrong)  # type: ignore[arg-type]


class TestLock:
    def test_off_means_never_locked(self, qapp: QApplication, app_config: AppConfig,
                                    app_services: AppServices) -> None:
        window = _window(app_config, app_services, start_locked=True)
        try:
            assert not window.app_lock.locked and window.app_lock.screen.isHidden()
            window.lock()
            assert not window.app_lock.locked
        finally:
            window.close()

    def test_starts_locked_and_opens_with_hello(self, qapp: QApplication, app_config: AppConfig,
                                                lock_on: AppServices,
                                                hello_verifier: FakeVerifier) -> None:
        window = _window(app_config, lock_on, start_locked=True)
        try:
            lock = window.app_lock
            assert lock.locked and lock.screen.isVisible()
            assert lock.screen.geometry() == window.centralWidget().rect()
            wait_until(lambda: not lock.locked)  # Hello is asked at once
            assert hello_verifier.messages == ["Unlock Money Manager"]
            assert lock.screen.isHidden()
        finally:
            window.close()

    def test_cancel_then_retry(self, window: MainWindow, hello_verifier: FakeVerifier) -> None:
        hello_verifier.answers = [HelloResult.CANCELED, HelloResult.FAILED]
        lock = window.app_lock
        lock.lock()
        lock.screen.unlock_button.click()
        wait_until(lambda: lock.screen.unlock_button.isEnabled())
        assert lock.locked and "cancelled" in lock.screen.message.text()
        lock.screen.unlock_button.click()
        wait_until(lambda: lock.screen.unlock_button.isEnabled())
        assert lock.locked and "could not confirm" in lock.screen.message.text()
        lock.screen.unlock_button.click()
        wait_until(lambda: not lock.locked)

    def test_shortcuts_are_paused_while_locked(self, window: MainWindow,
                                               hello_verifier: FakeVerifier) -> None:
        shortcuts = window.findChildren(QShortcut)
        assert shortcuts and all(s.isEnabled() for s in shortcuts)
        window.app_lock.lock()
        assert not any(s.isEnabled() for s in shortcuts)
        window.app_lock.unlock()
        wait_until(lambda: not window.app_lock.locked)
        assert all(s.isEnabled() for s in shortcuts)

    def test_keys_only_reach_the_lock_screen(self, window: MainWindow) -> None:
        window.show_page(DASHBOARD_PAGE_KEY)
        window.app_lock.lock()
        page = window.current_page
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier, "a")
        assert window.app_lock.eventFilter(page, event) is True
        assert window.app_lock.eventFilter(window.app_lock.screen.unlock_button, event) is False

    def test_ctrl_l_locks(self, window: MainWindow) -> None:
        wanted = QKeySequence("Ctrl+L").toString()
        next(s for s in window.findChildren(QShortcut) if s.key().toString() == wanted
             ).activated.emit()
        assert window.app_lock.locked

    def test_idle_time_locks_and_closes_dialogs(self, window: MainWindow) -> None:
        assert window.app_lock.idle_timer.isActive()
        assert window.app_lock.idle_timer.interval() == 5 * 60_000
        dialog = QDialog(window)
        dialog.show()
        window.app_lock.idle_timer.timeout.emit()
        assert window.app_lock.locked and not dialog.isVisible()

    def test_never_auto_lock(self, window: MainWindow, lock_on: AppServices) -> None:
        lock_on.settings.set_lock_after_minutes(0)
        window.app_lock.configure()
        assert not window.app_lock.idle_timer.isActive()

    def test_hello_gone_lets_you_in(self, window: MainWindow,
                                    hello_verifier: FakeVerifier) -> None:
        hello_verifier.default = HelloResult.UNAVAILABLE
        hello_verifier.status_value = HelloStatus.NOT_SET_UP
        lock = window.app_lock
        lock.lock()
        lock.screen.unlock_button.click()
        wait_until(lambda: lock.screen.unlock_button.isEnabled())
        assert "Sign-in options" in lock.screen.message.text()
        assert lock.screen.open_button.isVisibleTo(window)
        lock.screen.open_button.click()
        assert not lock.locked


class TestCard:
    def _card(self, window: MainWindow):  # noqa: ANN202
        page = window.page(SETTINGS_PAGE_KEY)
        assert isinstance(page, SettingsPage)
        return page.lock_card

    def test_turning_on_needs_hello(self, qapp: QApplication, app_config: AppConfig,
                                    app_services: AppServices,
                                    hello_verifier: FakeVerifier) -> None:
        window = _window(app_config, app_services)
        try:
            card = self._card(window)
            assert not card.lock_box.isChecked() and not card.lock_now_button.isEnabled()
            hello_verifier.answers = [HelloResult.CANCELED]
            card.lock_box.click()
            wait_until(lambda: card.lock_box.isEnabled())
            assert not app_services.settings.app_lock_enabled()
            assert not card.lock_box.isChecked()

            card.lock_box.click()
            wait_until(lambda: card.lock_box.isChecked())
            assert app_services.settings.app_lock_enabled()
            assert window.app_lock.idle_timer.isActive()  # the window picked it up
            card.lock_now_button.click()
            assert window.app_lock.locked
        finally:
            window.close()

    def test_without_hello_it_cannot_be_turned_on(self, qapp: QApplication,
                                                  app_config: AppConfig,
                                                  app_services: AppServices,
                                                  hello_verifier: FakeVerifier) -> None:
        hello_verifier.status_value = HelloStatus.NOT_SET_UP
        window = _window(app_config, app_services)
        try:
            card = self._card(window)
            assert not card.lock_box.isEnabled()
            assert "Sign-in options" in card.status_label.text()
        finally:
            window.close()

    def test_lock_time_is_saved(self, window: MainWindow, lock_on: AppServices) -> None:
        card = self._card(window)
        card.after_combo.setCurrentIndex(card.after_combo.findData(30))
        assert lock_on.settings.lock_after_minutes() == 30
        assert window.app_lock.idle_timer.interval() == 30 * 60_000
