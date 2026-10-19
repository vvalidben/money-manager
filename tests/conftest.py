import os

# Must be set before any QApplication exists so tests run without a display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Still pages by default: tests read final values at once. Motion tests turn it on.
os.environ.setdefault("MONEY_MANAGER_MOTION", "off")

from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from PySide6.QtCore import QThreadPool  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from money_manager.ai.secrets import MemorySecretStore  # noqa: E402
from money_manager.core.config import AppConfig  # noqa: E402
from money_manager.core.logging_setup import shutdown_logging  # noqa: E402
from money_manager.persistence.database import Database  # noqa: E402
from money_manager.services import AppServices  # noqa: E402
from money_manager.ui.theme import apply_theme  # noqa: E402
from tests.services.support import fixed_today  # noqa: E402


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    app = QApplication([])
    # The real theme (fonts, stylesheet), so layout tests measure what users see.
    apply_theme(app)
    return app


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(data_dir=tmp_path / "data")


@pytest.fixture
def database(app_config: AppConfig) -> Iterator[Database]:
    """An initialised database in a temporary folder."""
    app_config.data_dir.mkdir(parents=True)
    db = Database(app_config.database_url)
    db.initialize()
    yield db
    QThreadPool.globalInstance().waitForDone(10_000)  # background page calculations
    db.dispose()


@pytest.fixture
def app_services(database: Database) -> AppServices:
    """Every service, wired to the test database with a fixed 'today'.

    Secrets stay in memory and the real environment is not read, so tests never
    touch the Windows Credential Manager or a developer's ANTHROPIC_API_KEY.
    """
    return AppServices.create(database, today=fixed_today, secret_store=MemorySecretStore(),
                              environ={})


@pytest.fixture(autouse=True)
def _release_log_files() -> Iterator[None]:
    """Close log handlers so Windows can delete temporary folders."""
    yield
    shutdown_logging()
