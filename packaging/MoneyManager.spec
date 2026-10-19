# PyInstaller build specification for MoneyManager.exe (one-folder build).
#
# Build with:  python packaging/build.py      (or: pyinstaller packaging/MoneyManager.spec)
#
# Bundled resources keep the package layout, so money_manager.core.resources
# finds them under sys._MEIPASS/money_manager:
#   * ui/assets                    stylesheet images and the window icon
#   * persistence/migrations       Alembic reads these scripts from disk at start-up
# The optional online-AI SDK (anthropic) is included so online AI works in the build.

import re
from pathlib import Path

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 - defined by PyInstaller
SRC = ROOT / "src"
PACKAGE = SRC / "money_manager"
VERSION = re.search(r'__version__ = "([^"]+)"',
                    (PACKAGE / "__init__.py").read_text(encoding="utf-8")).group(1)
NUMBERS = tuple(int(part) for part in VERSION.split(".")) + (0,)

datas = [
    (str(PACKAGE / "ui" / "assets"), "money_manager/ui/assets"),
    (str(PACKAGE / "persistence" / "migrations"), "money_manager/persistence/migrations"),
]

excludes = [
    # development and test tools
    "pytest", "_pytest", "coverage", "PyInstaller", "tests",
    # GUI toolkits and Qt modules the application does not use
    "tkinter", "matplotlib.backends.backend_tkagg", "matplotlib.backends.backend_tkcairo",
    "matplotlib.backends.backend_webagg", "matplotlib.backends.backend_gtk3agg",
    "matplotlib.backends.backend_wxagg", "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.Qt3DCore",
    "PySide6.QtMultimedia", "PySide6.QtBluetooth", "PySide6.QtPositioning",
    "PySide6.QtSql", "PySide6.QtDesigner", "PySide6.QtHelp",
]

a = Analysis(  # noqa: F821
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(SRC)],
    datas=datas,
    hiddenimports=[
        "money_manager.persistence.migrations.env",
        "sqlalchemy.dialects.sqlite.pysqlite",
        "logging.config",  # used by Alembic's env handling
        "anthropic",
        # Windows Hello (imported lazily by ui.lock.hello)
        "winrt.runtime",
        "winrt.system",
        "winrt.windows.foundation",
        "winrt.windows.security.credentials.ui",
    ],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=NUMBERS, prodvers=NUMBERS),
    kids=[
        StringFileInfo([StringTable("040904B0", [
            StringStruct("CompanyName", "Money Manager"),
            StringStruct("FileDescription", "Money Manager — local-first personal finance"),
            StringStruct("FileVersion", VERSION),
            StringStruct("InternalName", "MoneyManager"),
            StringStruct("OriginalFilename", "MoneyManager.exe"),
            StringStruct("ProductName", "Money Manager"),
            StringStruct("ProductVersion", VERSION),
        ])]),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MoneyManager",
    icon=str(ROOT / "packaging" / "app.ico"),
    version=version_info,
    console=False,  # a windowed application: no console window
    upx=False,  # UPX-packed binaries trigger antivirus false positives
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    name="MoneyManager",
    upx=False,
)
