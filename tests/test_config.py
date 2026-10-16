from pathlib import Path

import pytest

from money_manager.core import config as config_module
from money_manager.core.config import (
    CONFIG_FILE_ENV,
    DATA_DIR_ENV,
    DATABASE_FILENAME,
    LOG_LEVEL_ENV,
    AppConfig,
    load_config,
    prepare_directories,
)
from money_manager.core.errors import ConfigurationError


def test_default_data_dir_is_under_local_app_data(tmp_path: Path) -> None:
    config = load_config({"LOCALAPPDATA": str(tmp_path)})

    assert config.data_dir == tmp_path / "MoneyManager"


def test_data_dir_can_be_overridden(tmp_path: Path) -> None:
    config = load_config({DATA_DIR_ENV: str(tmp_path / "custom"), "LOCALAPPDATA": "ignored"})

    assert config.data_dir == tmp_path / "custom"


def test_defaults() -> None:
    config = load_config({"LOCALAPPDATA": "C:/unused"})

    assert config.log_level == "INFO"


def test_log_level_is_normalised() -> None:
    config = load_config({"LOCALAPPDATA": "C:/unused", LOG_LEVEL_ENV: " debug "})

    assert config.log_level == "DEBUG"


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match=LOG_LEVEL_ENV):
        load_config({"LOCALAPPDATA": "C:/unused", LOG_LEVEL_ENV: "LOUD"})


def test_derived_paths(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)

    assert config.database_path == tmp_path / DATABASE_FILENAME
    assert config.log_dir == tmp_path / "logs"
    assert config.database_url == f"sqlite:///{(tmp_path / DATABASE_FILENAME).as_posix()}"


def test_prepare_directories_creates_folders(app_config: AppConfig) -> None:
    prepare_directories(app_config)

    assert app_config.data_dir.is_dir()
    assert app_config.log_dir.is_dir()


def test_prepare_directories_reports_unusable_location(tmp_path: Path) -> None:
    blocker = tmp_path / "not_a_folder"
    blocker.write_text("")

    with pytest.raises(ConfigurationError, match="Cannot create the folder"):
        prepare_directories(AppConfig(data_dir=blocker))


def write_ini(path: Path, body: str) -> Path:
    path.write_text("[money_manager]\n" + body, encoding="utf-8")
    return path


def test_config_file_sets_data_dir_and_log_level(tmp_path: Path) -> None:
    ini = write_ini(tmp_path / "MoneyManager.ini", "data_dir = data\nlog_level = warning\n")

    config = load_config({CONFIG_FILE_ENV: str(ini), "LOCALAPPDATA": "C:/unused"})

    assert config.data_dir == tmp_path / "data"  # relative to the file: portable
    assert config.log_level == "WARNING" and config.config_file == ini


def test_environment_wins_over_the_file(tmp_path: Path) -> None:
    ini = write_ini(tmp_path / "MoneyManager.ini", "data_dir = data\nlog_level = ERROR\n")
    config = load_config({CONFIG_FILE_ENV: str(ini), DATA_DIR_ENV: str(tmp_path / "env"),
                          LOG_LEVEL_ENV: "DEBUG"})
    assert (config.data_dir, config.log_level) == (tmp_path / "env", "DEBUG")


def test_file_next_to_the_executable_is_used_when_packaged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_ini(tmp_path / "MoneyManager.ini", "data_dir = portable-data\n")
    monkeypatch.setattr(config_module, "executable_dir", lambda: tmp_path)
    assert load_config({"LOCALAPPDATA": "C:/unused"}).data_dir == tmp_path / "portable-data"


def test_empty_or_missing_section_uses_defaults(tmp_path: Path) -> None:
    ini = tmp_path / "MoneyManager.ini"
    ini.write_text("; nothing configured\n", encoding="utf-8")
    config = load_config({CONFIG_FILE_ENV: str(ini), "LOCALAPPDATA": str(tmp_path)})
    assert config.data_dir == tmp_path / "MoneyManager"


@pytest.mark.parametrize(("body", "message"), [
    ("colour = green\n", "Unknown setting"),
    ("log_level = LOUD\n", "Invalid log level"),
    ("this is not ini", "Cannot read the configuration file"),
])
def test_bad_config_files_are_reported(tmp_path: Path, body: str, message: str) -> None:
    ini = tmp_path / "MoneyManager.ini"
    ini.write_text(body if body.startswith("this") else "[money_manager]\n" + body,
                   encoding="utf-8")
    with pytest.raises(ConfigurationError, match=message):
        load_config({CONFIG_FILE_ENV: str(ini), "LOCALAPPDATA": "C:/unused"})


def test_missing_named_config_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_config({CONFIG_FILE_ENV: str(tmp_path / "nope.ini")})


def test_the_example_file_parses(tmp_path: Path) -> None:
    example = Path(__file__).resolve().parents[1] / "packaging" / "MoneyManager.example.ini"
    values = config_module.read_config_file(example)
    assert set(values) <= {"data_dir", "log_level"}

