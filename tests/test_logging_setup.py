import logging
from pathlib import Path

from money_manager.core.logging_setup import LOG_FILENAME, configure_logging, shutdown_logging


def _app_handlers() -> list[logging.Handler]:
    return [
        h for h in logging.getLogger().handlers if (h.get_name() or "").startswith("money_manager.")
    ]


def test_writes_to_log_file(tmp_path: Path) -> None:
    log_file = configure_logging(tmp_path, "INFO")

    logging.getLogger("money_manager.test").info("hello from test")
    shutdown_logging()

    assert log_file == tmp_path / LOG_FILENAME
    assert "hello from test" in log_file.read_text(encoding="utf-8")


def test_reconfiguring_does_not_duplicate_handlers(tmp_path: Path) -> None:
    configure_logging(tmp_path, "INFO")
    first_count = len(_app_handlers())

    configure_logging(tmp_path, "DEBUG")

    assert len(_app_handlers()) == first_count
    assert logging.getLogger().level == logging.DEBUG


def test_sqlalchemy_logging_is_silenced(tmp_path: Path) -> None:
    configure_logging(tmp_path, "DEBUG")

    assert not logging.getLogger("sqlalchemy.engine").isEnabledFor(logging.INFO)


def test_shutdown_removes_only_app_handlers(tmp_path: Path) -> None:
    foreign = logging.NullHandler()
    logging.getLogger().addHandler(foreign)
    try:
        configure_logging(tmp_path, "INFO")
        shutdown_logging()

        assert _app_handlers() == []
        assert foreign in logging.getLogger().handlers
    finally:
        logging.getLogger().removeHandler(foreign)
