import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QWidget

from money_manager import app as app_module
from money_manager.core.config import DATA_DIR_ENV, AppConfig
from money_manager.core.logging_setup import LOG_FILENAME
from money_manager.ui.main_window import MainWindow


@pytest.fixture(autouse=True)
def _restore_excepthook(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)


def test_initialize_backend_creates_database_and_log(app_config: AppConfig) -> None:
    database = app_module.initialize_backend(app_config)
    database.dispose()

    assert app_config.database_path.is_file()
    assert (app_config.log_dir / LOG_FILENAME).is_file()


def test_run_starts_window_and_creates_database(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    seen_windows: list[QWidget] = []

    def inspect_and_quit() -> None:
        seen_windows.extend(w for w in qapp.topLevelWidgets() if isinstance(w, MainWindow))
        for widget in seen_windows:
            widget.close()
        qapp.quit()

    QTimer.singleShot(0, inspect_and_quit)
    exit_code = app_module.run([])

    assert exit_code == 0
    assert len(seen_windows) == 1
    assert (tmp_path / "money_manager.db").is_file()


def test_run_reports_startup_failure(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocker = tmp_path / "not_a_folder"
    blocker.write_text("")
    monkeypatch.setenv(DATA_DIR_ENV, str(blocker))
    shown: list[str] = []
    monkeypatch.setattr(
        app_module.dialogs, "show_error", lambda _parent, _title, message: shown.append(message)
    )

    exit_code = app_module.run([])

    assert exit_code == 1
    assert len(shown) == 1
    assert "Cannot create the folder" in shown[0]
