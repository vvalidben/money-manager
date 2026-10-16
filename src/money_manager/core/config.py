"""Application configuration.

Resolved once at startup, in this order (first wins):

1. environment variables ``MONEY_MANAGER_DATA_DIR`` / ``MONEY_MANAGER_LOG_LEVEL``;
2. an optional ``MoneyManager.ini`` — the file named by ``MONEY_MANAGER_CONFIG``,
   or, in the packaged build, the one next to ``MoneyManager.exe`` (portable use);
3. defaults: data in ``%LOCALAPPDATA%\\MoneyManager``, log level INFO.

Configuration holds no secrets: API keys are never read from here. AI and
currency settings live in the database; the API key in the Windows
Credential Manager.
"""

import configparser
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from money_manager.core.errors import ConfigurationError
from money_manager.core.resources import executable_dir

DATA_DIR_ENV = "MONEY_MANAGER_DATA_DIR"
LOG_LEVEL_ENV = "MONEY_MANAGER_LOG_LEVEL"
CONFIG_FILE_ENV = "MONEY_MANAGER_CONFIG"

APP_DIR_NAME = "MoneyManager"
CONFIG_FILENAME = "MoneyManager.ini"
CONFIG_SECTION = "money_manager"
DATABASE_FILENAME = "money_manager.db"
LOG_DIR_NAME = "logs"
DEFAULT_LOG_LEVEL = "INFO"

_VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
_KNOWN_KEYS = frozenset({"data_dir", "log_level"})


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Immutable runtime configuration."""

    data_dir: Path
    log_level: str = DEFAULT_LOG_LEVEL
    config_file: Path | None = None  # the MoneyManager.ini that was read, if any

    @property
    def database_path(self) -> Path:
        return self.data_dir / DATABASE_FILENAME

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / LOG_DIR_NAME


def default_data_dir(environ: Mapping[str, str]) -> Path:
    """Per-user data folder, e.g. ``%LOCALAPPDATA%\\MoneyManager``."""
    local_app_data = environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return base / APP_DIR_NAME


def find_config_file(environ: Mapping[str, str]) -> Path | None:
    """The configuration file to read, or None when there is none."""
    named = environ.get(CONFIG_FILE_ENV, "").strip()
    if named:
        path = Path(named).expanduser()
        if not path.is_file():
            raise ConfigurationError(
                f"The configuration file named by {CONFIG_FILE_ENV} does not exist: {path}")
        return path
    folder = executable_dir()
    if folder is not None and (folder / CONFIG_FILENAME).is_file():
        return folder / CONFIG_FILENAME
    return None


def read_config_file(path: Path) -> dict[str, str]:
    """Settings from the ``[money_manager]`` section; relative paths are resolved
    against the file's own folder, so a portable copy works wherever it is moved."""
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with path.open(encoding="utf-8-sig") as handle:
            parser.read_file(handle)
    except (OSError, UnicodeDecodeError, configparser.Error) as exc:
        raise ConfigurationError(f"Cannot read the configuration file '{path}': {exc}") from exc
    if not parser.has_section(CONFIG_SECTION):
        return {}
    values = {key: value.strip() for key, value in parser.items(CONFIG_SECTION)}
    unknown = sorted(set(values) - _KNOWN_KEYS)
    if unknown:
        raise ConfigurationError(
            f"Unknown setting(s) {', '.join(unknown)} in '{path}'; expected "
            f"{', '.join(sorted(_KNOWN_KEYS))}.")
    if values.get("data_dir"):
        data_dir = Path(os.path.expandvars(values["data_dir"])).expanduser()
        values["data_dir"] = str(data_dir if data_dir.is_absolute() else path.parent / data_dir)
    return values


def load_config(environ: Mapping[str, str] | None = None) -> AppConfig:
    """Build the configuration from environment variables, the optional file and defaults."""
    env = os.environ if environ is None else environ
    config_file = find_config_file(env)
    file_values = read_config_file(config_file) if config_file is not None else {}

    data_dir_text = env.get(DATA_DIR_ENV, "").strip() or file_values.get("data_dir", "")
    data_dir = Path(data_dir_text).expanduser() if data_dir_text else default_data_dir(env)

    log_level = (env.get(LOG_LEVEL_ENV, "").strip() or file_values.get("log_level", "")
                 or DEFAULT_LOG_LEVEL).upper()
    if log_level not in _VALID_LOG_LEVELS:
        raise ConfigurationError(
            f"Invalid log level {log_level!r} (set by {LOG_LEVEL_ENV} or log_level); "
            f"expected one of {', '.join(sorted(_VALID_LOG_LEVELS))}."
        )

    return AppConfig(data_dir=data_dir, log_level=log_level, config_file=config_file)


def prepare_directories(config: AppConfig) -> None:
    """Create the data and log folders if they do not exist yet."""
    for directory in (config.data_dir, config.log_dir):
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ConfigurationError(
                f"Cannot create the folder '{directory}': {exc.strerror or exc}"
            ) from exc
