# PyInstaller specification for MoneyManager-<version>-Setup.exe (one file).
#
# Built by packaging/build.py after the application, which passes:
#   MM_PAYLOAD       the release zip (MoneyManager/ folder) embedded as the payload
#   MM_VERSION_FILE  a text file holding the version
# The installer is plain Python + tkinter; it does not include Qt.

import os
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

HERE = Path(SPECPATH).resolve()  # noqa: F821 - defined by PyInstaller
PACKAGING = HERE.parent
PAYLOAD = Path(os.environ["MM_PAYLOAD"])
VERSION_FILE = Path(os.environ["MM_VERSION_FILE"])
VERSION = VERSION_FILE.read_text(encoding="utf-8").strip()
NUMBERS = tuple(int(part) for part in re.findall(r"\d+", VERSION)[:3]) + (0,)

a = Analysis(  # noqa: F821
    [str(HERE / "setup_app.py")],
    pathex=[str(HERE)],
    datas=[
        (str(PAYLOAD), "."),
        (str(VERSION_FILE), "."),
        (str(PACKAGING / "app.ico"), "."),
    ],
    excludes=["PySide6", "shiboken6", "matplotlib", "numpy", "sqlalchemy", "alembic",
              "anthropic", "pytest", "money_manager"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=NUMBERS, prodvers=NUMBERS),
    kids=[
        StringFileInfo([StringTable("040904B0", [
            StringStruct("CompanyName", "Money Manager"),
            StringStruct("FileDescription", "Money Manager Setup"),
            StringStruct("FileVersion", VERSION),
            StringStruct("InternalName", "MoneyManagerSetup"),
            StringStruct("OriginalFilename", f"MoneyManager-{VERSION}-Setup.exe"),
            StringStruct("ProductName", "Money Manager"),
            StringStruct("ProductVersion", VERSION),
        ])]),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f"MoneyManager-{VERSION}-Setup",
    icon=str(PACKAGING / "app.ico"),
    version=version_info,
    console=False,
    upx=False,
)
