"""Logging configuration.

Logs go to a rotating file in the data folder and, when a console exists, to
stderr. Log messages must never contain transaction amounts or other financial
details; log events and identifiers instead. As a safety net every line,
tracebacks included, passes through ``redact_secrets`` so API keys that end
up in a third-party exception message are never written to disk.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from money_manager.core.errors import ConfigurationError
from money_manager.core.redaction import redact_secrets

LOG_FILENAME = "money_manager.log"
LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
MAX_LOG_BYTES = 1_000_000
LOG_BACKUP_COUNT = 5

_HANDLER_PREFIX = "money_manager."


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact_secrets(super().format(record))


def configure_logging(log_dir: Path, level: str) -> Path:
    """Install the application's log handlers on the root logger.

    Safe to call more than once: previously installed handlers are replaced.
    Returns the path of the log file.
    """
    log_file = log_dir / LOG_FILENAME
    shutdown_logging()

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=MAX_LOG_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
        )
    except OSError as exc:
        raise ConfigurationError(f"Cannot open the log file '{log_file}': {exc}") from exc
    file_handler.set_name(_HANDLER_PREFIX + "file")
    handlers: list[logging.Handler] = [file_handler]

    # Windowed builds (pythonw, PyInstaller --windowed) have no console.
    if sys.stderr is not None:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.set_name(_HANDLER_PREFIX + "console")
        handlers.append(console_handler)

    formatter = RedactingFormatter(LOG_FORMAT)
    root = logging.getLogger()
    root.setLevel(level)
    for handler in handlers:
        handler.setFormatter(formatter)
        root.addHandler(handler)

    # SQLAlchemy logs SQL parameters at INFO, which would leak financial values.
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    # HTTP client libraries can log request details at DEBUG.
    # Alembic reports every routine schema check at INFO; migrations log their own summary.
    for name in ("anthropic", "httpx", "httpx2", "httpcore", "urllib3", "alembic"):
        logging.getLogger(name).setLevel(logging.WARNING)
    return log_file


def shutdown_logging() -> None:
    """Remove and close the handlers installed by ``configure_logging``."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        name = handler.get_name()
        if name and name.startswith(_HANDLER_PREFIX):
            root.removeHandler(handler)
            handler.close()
