"""The installer's logic (packaging/installer/install_core.py) with a fake system."""

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "install_core", ROOT / "packaging" / "installer" / "install_core.py")
assert _spec is not None and _spec.loader is not None
core = importlib.util.module_from_spec(_spec)
sys.modules["install_core"] = core
_spec.loader.exec_module(core)


class FakeSystem:
    def __init__(self, running: bool = False, version: str | None = None) -> None:
        self.running = running
        self.version = version
        self.shortcuts: list[tuple[Path, bool]] = []
        self.registered: list[tuple[Path, str]] = []

    def is_running(self) -> bool:
        return self.running

    def create_shortcuts(self, exe: Path, *, desktop: bool) -> None:
        self.shortcuts.append((exe, desktop))

    def register(self, target: Path, version: str, size_kb: int) -> None:
        assert size_kb >= 0
        self.registered.append((target, version))

    def installed_version(self) -> str | None:
        return self.version


def payload(folder: Path, files: dict[str, str], name: str = "app.zip") -> Path:
    path = folder / name
    with zipfile.ZipFile(path, "w") as bundle:
        for relative, text in files.items():
            bundle.writestr(relative, text)
    return path


RELEASE = {"MoneyManager/MoneyManager.exe": "exe v2", "MoneyManager/_internal/lib.dll": "lib",
           "MoneyManager/README.md": "readme"}


def test_fresh_install(tmp_path: Path) -> None:
    system = FakeSystem()
    target = tmp_path / "Programs" / "MoneyManager"
    steps: list[float] = []
    result = core.install(payload(tmp_path, RELEASE), target, "1.4.0", system,
                          desktop_shortcut=True, progress=lambda f, _t: steps.append(f))
    assert (target / "MoneyManager.exe").read_text() == "exe v2"
    assert (target / "_internal" / "lib.dll").is_file()
    manifest = json.loads((target / "install-manifest.json").read_text(encoding="utf-8"))
    assert manifest == {"version": "1.4.0", "files": ["MoneyManager.exe", "README.md",
                                                      "_internal"]}
    assert "Your data" in (target / "uninstall.ps1").read_text(encoding="utf-8-sig")
    assert system.shortcuts == [(target / "MoneyManager.exe", True)]
    assert system.registered == [(target, "1.4.0")]
    assert steps[-1] == 1.0 and steps == sorted(steps)
    assert result.previous_version is None and result.kept == ()
    assert not (tmp_path / "Programs" / "MoneyManager.new").exists()


def test_update_keeps_the_users_files(tmp_path: Path) -> None:
    target = tmp_path / "MoneyManager"
    core.install(payload(tmp_path, {**RELEASE, "MoneyManager/old-only.txt": "x"}, "v1.zip"),
                 target, "1.3.0", FakeSystem())
    (target / "MoneyManager.ini").write_text("data_dir = data", encoding="utf-8")
    (target / "data").mkdir()
    (target / "data" / "money_manager.db").write_text("precious", encoding="utf-8")

    result = core.install(payload(tmp_path, RELEASE, "v2.zip"), target, "1.4.0",
                          FakeSystem(version="1.3.0"))

    assert result.previous_version == "1.3.0"
    assert set(result.kept) == {"MoneyManager.ini", "data"}
    assert (target / "data" / "money_manager.db").read_text(encoding="utf-8") == "precious"
    assert (target / "MoneyManager.ini").is_file()
    assert not (target / "old-only.txt").exists()  # a file of the old version, removed
    assert not (tmp_path / "MoneyManager.old").exists()


def test_a_copied_folder_without_manifest_is_updated(tmp_path: Path) -> None:
    target = tmp_path / "MoneyManager"
    (target / "_internal").mkdir(parents=True)
    (target / "MoneyManager.exe").write_text("old", encoding="utf-8")
    (target / "notes.txt").write_text("mine", encoding="utf-8")
    result = core.install(payload(tmp_path, RELEASE), target, "1.4.0", FakeSystem())
    assert (target / "MoneyManager.exe").read_text() == "exe v2"
    assert result.kept == ("notes.txt",)


def test_refuses_while_running(tmp_path: Path) -> None:
    with pytest.raises(core.InstallError, match="Close it"):
        core.install(payload(tmp_path, RELEASE), tmp_path / "MM", "1.4.0",
                     FakeSystem(running=True))
    assert not (tmp_path / "MM").exists()


def test_damaged_payloads(tmp_path: Path) -> None:
    broken = tmp_path / "broken.zip"
    broken.write_bytes(b"not a zip")
    with pytest.raises(core.InstallError, match="damaged"):
        core.install(broken, tmp_path / "MM", "1.4.0", FakeSystem())
    no_exe = payload(tmp_path, {"MoneyManager/README.md": "r"}, "no-exe.zip")
    with pytest.raises(core.InstallError, match="program is missing"):
        core.install(no_exe, tmp_path / "MM", "1.4.0", FakeSystem())
    escape = payload(tmp_path, {**RELEASE, "MoneyManager/../../evil.txt": "x"}, "evil.zip")
    with pytest.raises(core.InstallError, match="unexpected file paths"):
        core.install(escape, tmp_path / "MM", "1.4.0", FakeSystem())
    assert not (tmp_path / "evil.txt").exists()


def test_previous_version_survives_a_failed_install(tmp_path: Path) -> None:
    target = tmp_path / "MoneyManager"
    core.install(payload(tmp_path, RELEASE, "v1.zip"), target, "1.3.0", FakeSystem())
    with pytest.raises(core.InstallError):
        core.install(payload(tmp_path, {"MoneyManager/README.md": "r"}, "bad.zip"), target,
                     "1.4.0", FakeSystem())
    assert (target / "MoneyManager.exe").read_text() == "exe v2"


def test_default_target() -> None:
    assert core.default_target({"LOCALAPPDATA": r"C:\Users\x\AppData\Local"}) == Path(
        r"C:\Users\x\AppData\Local\Programs\MoneyManager")


def test_uninstaller_only_removes_listed_names() -> None:
    script = core.UNINSTALL_SCRIPT
    assert "install-manifest.json" in script and "-notmatch '[\\\\/]'" in script
    assert "LOCALAPPDATA\\MoneyManager" in script  # tells the user their data stays
    assert "Remove-Item -LiteralPath $dir -Recurse" not in script  # never the whole folder


def _build_module():
    spec = importlib.util.spec_from_file_location("mm_build", ROOT / "packaging" / "build.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_signing_is_optional_and_configurable(tmp_path: Path) -> None:
    build = _build_module()
    target = tmp_path / "MoneyManager.exe"
    assert build.signing_command({}, target) is None  # no certificate: not signed
    tool = str(tmp_path / "signtool.exe")
    command = build.signing_command({"MM_SIGN_CERT": "cert.pfx", "MM_SIGN_PASSWORD": "pw",
                                     "MM_SIGNTOOL": tool}, target)
    assert command[:2] == [tool, "sign"] and ["/f", "cert.pfx", "/p", "pw"] == command[8:12]
    assert "/tr" in command and command[-1] == str(target)
    store = build.signing_command({"MM_SIGN_THUMBPRINT": "AB12", "MM_SIGNTOOL": tool}, target)
    assert ["/sha1", "AB12"] == store[8:10]
    with pytest.raises(SystemExit):
        build.signing_command({"MM_SIGN_THUMBPRINT": "AB12",
                               "ProgramFiles(x86)": str(tmp_path / "none")}, target)
