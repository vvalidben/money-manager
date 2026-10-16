"""Where the application's own files are, from source or as a packaged build.

A PyInstaller build unpacks the bundled files (assets, database migrations)
into ``sys._MEIPASS``; from source they sit next to the modules. Code must
never locate files relative to the current working directory.
"""

import sys
from pathlib import Path


def is_frozen() -> bool:
    """True when running as a packaged executable (PyInstaller)."""
    return bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS")


def package_dir() -> Path:
    """The ``money_manager`` package folder holding the bundled resources."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS")) / "money_manager"
    return Path(__file__).resolve().parents[1]


def resource_path(*parts: str) -> Path:
    """A bundled file or folder, e.g. ``resource_path("ui", "assets", "app_icon.png")``."""
    return package_dir().joinpath(*parts)


def executable_dir() -> Path | None:
    """The folder of ``MoneyManager.exe`` in a packaged build; None from source."""
    return Path(sys.executable).resolve().parent if is_frozen() else None
