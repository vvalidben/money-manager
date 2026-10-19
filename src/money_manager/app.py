"""Application bootstrap: configuration → logging → database → window."""

import logging
import sys
from collections.abc import Sequence
from typing import TYPE_CHECKING

from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from money_manager import APP_NAME, __version__
from money_manager.core.config import AppConfig, load_config, prepare_directories
from money_manager.core.errors import MoneyManagerError
from money_manager.core.exception_hook import install_exception_hook
from money_manager.core.logging_setup import configure_logging, shutdown_logging
from money_manager.core.resources import resource_path
from money_manager.core.cli import self_test_folder
from money_manager.persistence.database import Database
from money_manager.services import AppServices
from money_manager.services.data_service import ensure_daily_copy
from money_manager.services.settings_service import SettingsService
from money_manager.ui import dialogs, motion
from money_manager.ui.theme import apply_theme, resolve_palette, use_palette

# The windows, pages and charts are imported only once the colour palette is
# chosen (see ``run``): the charts copy colour tokens when they are imported.
if TYPE_CHECKING:
    from money_manager.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def initialize_backend(config: AppConfig) -> Database:
    """Prepare folders, logging and the database. Raises ``MoneyManagerError``."""
    prepare_directories(config)
    configure_logging(config.log_dir, config.log_level)
    logger.info("Starting %s %s", APP_NAME, __version__)
    logger.info("Data folder: %s", config.data_dir)

    database = Database(config.database_url)
    database.initialize()
    return database


class WindowManager:
    """Owns the main window and rebuilds it (with fresh services) on request.

    Changing the currency, importing a backup or resetting changes what the
    services were built with, so a new ``AppServices`` and window replace the
    old ones. The new window is shown before the old one closes, so the
    application never runs out of windows (which would quit it).
    """

    def __init__(self, config: AppConfig, database: Database) -> None:
        self._config = config
        self._database = database
        self.window: "MainWindow | None" = None

    def open(self, page_key: str | None = None) -> "MainWindow":
        from money_manager.ui.main_window import MainWindow

        services = AppServices.create(self._database)
        # Locked on start; a rebuilt window (currency change, import …) is in use already.
        start_locked = self.window is None and services.settings.app_lock_enabled()
        window = MainWindow(self._config, services, start_locked=start_locked)
        window.reload_requested.connect(self.open)
        if page_key is not None:
            window.show_page(page_key)
        previous, self.window = self.window, window
        if previous is not None:
            window.setGeometry(previous.geometry())
        window.show()
        if previous is not None:
            previous.close()
            previous.deleteLater()
            logger.info("Rebuilt the main window (currency %s)", services.base_currency)
        return window


def _set_windows_app_id() -> None:
    """Group the windows under Money Manager's own taskbar icon (not python.exe's)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MoneyManager.Desktop")
    except (AttributeError, OSError):
        logger.debug("Could not set the Windows application id", exc_info=True)


def run(argv: Sequence[str] | None = None) -> int:
    """Start the GUI and block until it closes. Returns the process exit code."""
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication(
        list(argv) if argv is not None else sys.argv
    )
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setWindowIcon(QIcon(str(resource_path("ui", "assets", "app_icon.png"))))
    _set_windows_app_id()
    apply_theme(app)
    install_exception_hook(notify=dialogs.show_unexpected_error)

    folder = self_test_folder(sys.argv if argv is None else argv)
    if folder is not None:
        from money_manager.selftest import run_self_test

        try:
            return run_self_test(folder, app)
        finally:
            shutdown_logging()

    try:
        config = load_config()
        database = initialize_backend(config)
    except MoneyManagerError as exc:
        logger.critical("Startup failed: %s", exc, exc_info=True)
        dialogs.show_error(None, f"{APP_NAME} could not start", str(exc))
        shutdown_logging()
        return 1

    settings = SettingsService(database)
    palette = resolve_palette(settings.theme())
    if palette != "dark":
        use_palette(palette)
        apply_theme(app)
    motion.set_user_enabled(settings.animations_enabled())
    if settings.daily_copies_enabled():
        try:
            ensure_daily_copy(database)
        except MoneyManagerError as exc:  # a missed copy must never stop the app
            logger.warning("Could not write the daily copy: %s", exc)
    windows = WindowManager(config, database)
    if motion.enabled():
        from money_manager.ui.components.splash import LaunchScreen

        # A short launch screen, then the window appears as the screen fades.
        splash = LaunchScreen()
        splash.intro_finished.connect(windows.open)
        splash.intro_finished.connect(splash.fade_out)
        splash.start()
    else:
        windows.open()
    try:
        return app.exec()
    finally:
        # Let short background calculations finish; an AI request still running is
        # abandoned (its result is never shown).
        QThreadPool.globalInstance().waitForDone(2000)
        database.dispose()
        logger.info("Shutting down")
        shutdown_logging()
