"""Install and uninstall Money Manager for the current user (no administrator rights).

* The program goes to ``%LOCALAPPDATA%\\Programs\\MoneyManager``; the data is in
  its own folder (``%LOCALAPPDATA%\\MoneyManager`` by default) and is never
  touched by installing, updating or uninstalling.
* An update extracts the new version next to the old one, then swaps the
  folders, so a failure leaves the previous version working. Files the user
  added to the program folder (e.g. ``MoneyManager.ini``) are carried over.
* The install records which top-level items it created (``install-manifest.json``);
  the uninstaller removes only those, the shortcuts and the Apps entry.

The operating-system side (shortcuts, the Apps & features entry, "is it
running?") goes through ``System`` so the logic can be tested without them.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

APP_NAME = "Money Manager"
EXE_NAME = "MoneyManager.exe"
PROCESS_NAME = "MoneyManager"
PAYLOAD_ROOT = "MoneyManager/"  # folder inside the release zip
MANIFEST_NAME = "install-manifest.json"
UNINSTALLER_NAME = "uninstall.ps1"
SHORTCUT_NAME = f"{APP_NAME}.lnk"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\MoneyManager"
CREATE_NO_WINDOW = 0x08000000

Progress = Callable[[float, str], None]


class InstallError(Exception):
    """Something the user can act on (shown as is)."""


def default_target(environ: dict[str, str]) -> Path:
    base = environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "Programs" / "MoneyManager"


class System(Protocol):
    def is_running(self) -> bool: ...

    def create_shortcuts(self, exe: Path, *, desktop: bool) -> None: ...

    def register(self, target: Path, version: str, size_kb: int) -> None: ...

    def installed_version(self) -> str | None: ...


# ------------------------------------------------------------------ install

@dataclass(frozen=True, slots=True)
class InstallResult:
    target: Path
    version: str
    previous_version: str | None
    kept: tuple[str, ...]  # user files carried over from the previous folder


def install(payload: Path, target: Path, version: str, system: System, *,
            desktop_shortcut: bool = True, progress: Progress | None = None) -> InstallResult:
    report = progress or (lambda _fraction, _text: None)
    if system.is_running():
        raise InstallError("Money Manager is open. Close it, then choose Install again.")
    previous = system.installed_version()
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(target.name + ".new")
    old = target.with_name(target.name + ".old")
    for leftover in (staging, old):
        shutil.rmtree(leftover, ignore_errors=True)

    names = _extract(payload, staging, report)
    if not (staging / EXE_NAME).is_file():
        shutil.rmtree(staging, ignore_errors=True)
        raise InstallError("The installer is damaged (the program is missing). "
                           "Download it again.")

    report(0.85, "Replacing the previous version…")
    kept: list[str] = []
    if target.exists():
        try:
            target.rename(old)
        except OSError as exc:
            shutil.rmtree(staging, ignore_errors=True)
            raise InstallError("The program folder is in use. Close Money Manager (and any "
                               "window showing that folder), then try again.") from exc
    try:
        staging.rename(target)
    except OSError as exc:
        if old.exists():
            old.rename(target)  # put the previous version back
        raise InstallError(f"Could not install into {target}: {exc}") from exc
    if old.exists():
        ours = set(_manifest(old)) | {MANIFEST_NAME, UNINSTALLER_NAME} | names
        for item in sorted(old.iterdir()):
            if item.name not in ours:
                shutil.move(str(item), str(target / item.name))
                kept.append(item.name)
        shutil.rmtree(old, ignore_errors=True)

    (target / MANIFEST_NAME).write_text(
        json.dumps({"version": version, "files": sorted(names)}, indent=2), encoding="utf-8")
    (target / UNINSTALLER_NAME).write_text(UNINSTALL_SCRIPT, encoding="utf-8-sig")

    report(0.92, "Creating shortcuts…")
    system.create_shortcuts(target / EXE_NAME, desktop=desktop_shortcut)
    size_kb = sum(p.stat().st_size for p in target.rglob("*") if p.is_file()) // 1024
    system.register(target, version, size_kb)
    report(1.0, "Done")
    return InstallResult(target, version, previous, tuple(kept))


def _extract(payload: Path, staging: Path, report: Progress) -> set[str]:
    """Extract the program (the zip's ``MoneyManager/`` folder); its top-level names."""
    try:
        bundle = zipfile.ZipFile(payload)
    except (OSError, zipfile.BadZipFile) as exc:
        raise InstallError("The installer is damaged. Download it again.") from exc
    with bundle:
        members = [m for m in bundle.infolist()
                   if m.filename.startswith(PAYLOAD_ROOT) and not m.is_dir()]
        total = sum(m.file_size for m in members) or 1
        done = 0
        names: set[str] = set()
        staging.mkdir(parents=True)
        for member in members:
            relative = member.filename[len(PAYLOAD_ROOT):]
            destination = (staging / relative).resolve()
            if staging.resolve() not in destination.parents:
                raise InstallError("The installer is damaged (unexpected file paths).")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, destination.open("wb") as sink:
                shutil.copyfileobj(source, sink, 1024 * 1024)
            names.add(relative.split("/", 1)[0])
            done += member.file_size
            report(0.8 * done / total, "Copying files…")
    return names


def _manifest(folder: Path) -> list[str]:
    try:
        data = json.loads((folder / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # Installed by copying the folder: everything from a release is ours.
        return [EXE_NAME, "_internal", "README.md", "RELEASE_NOTES.md",
                "MoneyManager.example.ini"]
    files = data.get("files") if isinstance(data, dict) else None
    return [f for f in files if isinstance(f, str)] if isinstance(files, list) else []


# ------------------------------------------------------------- the real OS

def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_powershell(script: str) -> None:
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                   check=True, capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=60)


class WindowsSystem:
    def is_running(self) -> bool:
        result = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {EXE_NAME}", "/NH"],
                                capture_output=True, text=True, creationflags=CREATE_NO_WINDOW,
                                check=False)
        return EXE_NAME.lower() in result.stdout.lower()

    def create_shortcuts(self, exe: Path, *, desktop: bool) -> None:
        folders = ["Programs"] + (["Desktop"] if desktop else [])
        lines = ["$shell = New-Object -ComObject WScript.Shell"]
        for folder in folders:
            lines += [
                f"$link = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath("
                f"'{folder}')) {_ps_quote(SHORTCUT_NAME)}))",
                f"$link.TargetPath = {_ps_quote(str(exe))}",
                f"$link.WorkingDirectory = {_ps_quote(str(exe.parent))}",
                f"$link.IconLocation = {_ps_quote(str(exe) + ',0')}",
                "$link.Description = 'Money Manager — personal finance, kept local'",
                "$link.Save()",
            ]
        try:
            run_powershell("; ".join(lines))
        except (OSError, subprocess.SubprocessError) as exc:
            raise InstallError("Money Manager was installed, but its shortcuts could not be "
                               f"created ({type(exc).__name__}).") from exc

    def register(self, target: Path, version: str, size_kb: int) -> None:
        import winreg

        exe = target / EXE_NAME
        uninstall = (f'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden '
                     f'-File "{target / UNINSTALLER_NAME}"')
        values: dict[str, tuple[int, object]] = {
            "DisplayName": (winreg.REG_SZ, APP_NAME),
            "DisplayVersion": (winreg.REG_SZ, version),
            "Publisher": (winreg.REG_SZ, APP_NAME),
            "InstallLocation": (winreg.REG_SZ, str(target)),
            "DisplayIcon": (winreg.REG_SZ, f"{exe},0"),
            "UninstallString": (winreg.REG_SZ, uninstall),
            "InstallDate": (winreg.REG_SZ, date.today().strftime("%Y%m%d")),
            "EstimatedSize": (winreg.REG_DWORD, size_kb),
            "NoModify": (winreg.REG_DWORD, 1),
            "NoRepair": (winreg.REG_DWORD, 1),
        }
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
            for name, (kind, value) in values.items():
                winreg.SetValueEx(key, name, 0, kind, value)

    def installed_version(self) -> str | None:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
                value, _kind = winreg.QueryValueEx(key, "DisplayVersion")
        except OSError:
            return None
        return str(value)


# Run by Settings → Apps → Money Manager → Uninstall. It removes only what the
# installer created; the data folder is never touched.
UNINSTALL_SCRIPT = r"""# Money Manager uninstaller: removes the program, its shortcuts and its Apps entry.
# Your data (by default %LOCALAPPDATA%\MoneyManager) is NOT removed.
Add-Type -AssemblyName PresentationFramework
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$title = 'Uninstall Money Manager'
if (Get-Process -Name 'MoneyManager' -ErrorAction SilentlyContinue) {
    [System.Windows.MessageBox]::Show('Money Manager is open. Close it, then uninstall again.',
        $title, 'OK', 'Warning') | Out-Null
    exit 1
}
$answer = [System.Windows.MessageBox]::Show(
    "Remove Money Manager from this computer?`n`nYour data is kept (by default in $env:LOCALAPPDATA\MoneyManager).",
    $title, 'YesNo', 'Question')
if ($answer -ne 'Yes') { exit 0 }
$manifest = Join-Path $dir 'install-manifest.json'
if (Test-Path -LiteralPath $manifest) {
    foreach ($name in (Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json).files) {
        if ($name -and $name -notmatch '[\\/]' -and $name -ne '..') {
            Remove-Item -LiteralPath (Join-Path $dir $name) -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}
foreach ($folder in 'Programs', 'Desktop') {
    $link = Join-Path ([Environment]::GetFolderPath($folder)) 'Money Manager.lnk'
    Remove-Item -LiteralPath $link -Force -ErrorAction SilentlyContinue
}
Remove-Item -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\MoneyManager' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $manifest -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue
if (-not (Get-ChildItem -LiteralPath $dir -Force -ErrorAction SilentlyContinue)) {
    Remove-Item -LiteralPath $dir -Force -ErrorAction SilentlyContinue
}
[System.Windows.MessageBox]::Show('Money Manager was removed. Your data was kept.', $title,
    'OK', 'Information') | Out-Null
"""
