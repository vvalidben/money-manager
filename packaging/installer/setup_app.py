"""Money Manager Setup: the window around ``install_core`` (tkinter, no Qt needed).

Command line (used by the build to check the installer, never needed by users):
    MoneyManager-Setup.exe --quiet --target DIR --no-shortcuts
installs into DIR without a window, shortcuts or an Apps & features entry.
"""

from __future__ import annotations

import argparse
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import install_core
from install_core import APP_NAME, EXE_NAME, InstallError, WindowsSystem, default_target

VERSION_FILE = "version.txt"
PAYLOAD_FILE = "MoneyManager.zip"


def bundled(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def bundled_version() -> str:
    try:
        return bundled(VERSION_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        return "?"


class QuietSystem:
    """``--quiet``: no shortcuts, no Apps entry (for the build's installer check)."""

    def is_running(self) -> bool:
        return False

    def create_shortcuts(self, exe: Path, *, desktop: bool) -> None:
        return None

    def register(self, target: Path, version: str, size_kb: int) -> None:
        return None

    def installed_version(self) -> str | None:
        return None


class SetupWindow:
    def __init__(self, root: tk.Tk, version: str, target: Path) -> None:
        self.root = root
        self.version = version
        self.target = target
        self.system = WindowsSystem()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        root.title(f"{APP_NAME} Setup")
        root.resizable(False, False)
        icon = bundled("app.ico")
        if icon.is_file():
            root.iconbitmap(str(icon))
        frame = ttk.Frame(root, padding=24)
        frame.grid(sticky="nsew")
        previous = self.system.installed_version()
        heading = (f"Update {APP_NAME} {previous} to {version}" if previous
                   and previous != version else f"Install {APP_NAME} {version}")
        ttk.Label(frame, text=heading, font=("Segoe UI Semibold", 15)).grid(sticky="w")
        ttk.Label(frame, wraplength=440, justify="left", text=(
            f"{APP_NAME} will be installed for you only, without administrator rights, in:\n"
            f"{target}\n\nYour data is kept in its own folder. Installing, updating or "
            "uninstalling never changes it.")).grid(sticky="w", pady=(10, 12))
        self.desktop = tk.BooleanVar(value=True)
        self.launch = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Create a desktop shortcut",
                        variable=self.desktop).grid(sticky="w")
        ttk.Checkbutton(frame, text=f"Open {APP_NAME} when done",
                        variable=self.launch).grid(sticky="w", pady=(2, 12))
        self.bar = ttk.Progressbar(frame, length=440, maximum=1.0)
        self.bar.grid(sticky="ew")
        self.status = ttk.Label(frame, text="", wraplength=440)
        self.status.grid(sticky="w", pady=(6, 12))
        buttons = ttk.Frame(frame)
        buttons.grid(sticky="e")
        self.cancel_button = ttk.Button(buttons, text="Cancel", command=root.destroy)
        self.cancel_button.grid(row=0, column=0, padx=(0, 8))
        self.install_button = ttk.Button(buttons, text="Install", command=self.start)
        self.install_button.grid(row=0, column=1)
        self.install_button.focus_set()
        root.bind("<Return>", lambda _e: self.install_button.invoke())

    def start(self) -> None:
        if self.system.is_running():
            messagebox.showwarning(f"{APP_NAME} Setup",
                                   f"{APP_NAME} is open. Close it, then choose Install again.")
            return
        self.install_button.state(["disabled"])
        self.cancel_button.state(["disabled"])
        threading.Thread(target=self._work, daemon=True).start()
        self.root.after(50, self._poll)

    def _work(self) -> None:
        try:
            result = install_core.install(
                bundled(PAYLOAD_FILE), self.target, self.version, self.system,
                desktop_shortcut=self.desktop.get(),
                progress=lambda fraction, text: self.events.put(("progress", (fraction, text))))
        except InstallError as exc:
            self.events.put(("error", str(exc)))
        except Exception as exc:  # noqa: BLE001 - shown to the user, never silently lost
            self.events.put(("error", f"Unexpected problem: {exc}"))
        else:
            self.events.put(("done", result))

    def _poll(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress":
                    fraction, text = value  # type: ignore[misc]
                    self.bar["value"] = fraction
                    self.status["text"] = text
                elif kind == "error":
                    self.status["text"] = str(value)
                    self.install_button.state(["!disabled"])
                    self.cancel_button.state(["!disabled"])
                    messagebox.showerror(f"{APP_NAME} Setup", str(value))
                    return
                else:
                    self._finished()
                    return
        except queue.Empty:
            pass
        self.root.after(50, self._poll)

    def _finished(self) -> None:
        self.bar["value"] = 1.0
        self.status["text"] = (f"{APP_NAME} {self.version} is installed. Find it in the Start "
                               "menu. To remove it: Settings → Apps → Installed apps.")
        self.install_button.grid_remove()
        self.cancel_button.state(["!disabled"])
        self.cancel_button["text"] = "Close"
        if self.launch.get():
            subprocess.Popen([str(self.target / EXE_NAME)], cwd=str(self.target),
                             close_fds=True)
            self.root.after(800, self.root.destroy)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} Setup")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--target", type=Path)
    parser.add_argument("--no-shortcuts", action="store_true")
    arguments = parser.parse_args(argv)
    version = bundled_version()
    target = arguments.target or default_target(dict(os.environ))
    if arguments.quiet:
        system = QuietSystem() if arguments.no_shortcuts else WindowsSystem()
        try:
            install_core.install(bundled(PAYLOAD_FILE), target, version, system,
                                 desktop_shortcut=False)
        except InstallError as exc:
            print(exc, file=sys.stderr)
            return 1
        return 0
    root = tk.Tk()
    SetupWindow(root, version, target)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
