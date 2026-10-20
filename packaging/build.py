"""Build the Windows release: dist/MoneyManager/MoneyManager.exe and a zip.

    python packaging/build.py [--skip-self-test]

Steps: clean previous output → PyInstaller (packaging/MoneyManager.spec) →
add documentation → run the packaged self-test twice (first run and restart,
headless, in a temporary folder — never your real data) → zip with SHA-256.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGING = ROOT / "packaging"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
RELEASE = ROOT / "release"
APP_DIR = DIST / "MoneyManager"
EXE = APP_DIR / "MoneyManager.exe"
EXTRA_FILES = {
    ROOT / "README.md": "README.md",
    PACKAGING / "RELEASE_NOTES.md": "RELEASE_NOTES.md",
    PACKAGING / "MoneyManager.example.ini": "MoneyManager.example.ini",
}


def version() -> str:
    text = (ROOT / "src" / "money_manager" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__ = "([^"]+)"', text)
    assert match, "version not found"
    return match.group(1)


def step(message: str) -> None:
    print(f"\n== {message}", flush=True)


def clean() -> None:
    step("Cleaning previous build output")
    for folder in (BUILD, DIST):
        if folder.exists():
            shutil.rmtree(folder)
    # Stale bytecode must not be bundled next to the migration scripts.
    for cache in (ROOT / "src" / "money_manager").rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


# ------------------------------------------------------------------ signing
#
# Signing removes Windows' "unknown publisher" warning. It needs a code-signing
# certificate (bought from a certificate authority); without one the build is
# simply not signed. Configure it with environment variables — never in files:
#   MM_SIGN_CERT       path to a .pfx certificate file, with MM_SIGN_PASSWORD, or
#   MM_SIGN_THUMBPRINT the SHA-1 thumbprint of a certificate installed in Windows
#   MM_SIGNTOOL        signtool.exe (default: the newest one in the Windows SDK)
#   MM_SIGN_TIMESTAMP  RFC 3161 timestamp server (default: DigiCert's)

DEFAULT_TIMESTAMP = "http://timestamp.digicert.com"


def find_signtool(environ: dict[str, str]) -> Path | None:
    if environ.get("MM_SIGNTOOL"):
        return Path(environ["MM_SIGNTOOL"])
    kits = Path(environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Windows Kits" / "10" / "bin"
    tools = sorted(kits.glob("10.*/x64/signtool.exe")) if kits.is_dir() else []
    return tools[-1] if tools else None


def signing_command(environ: dict[str, str], target: Path) -> list[str] | None:
    """The signtool command for ``target``, or None when signing is not configured."""
    if environ.get("MM_SIGN_CERT"):
        identity = ["/f", environ["MM_SIGN_CERT"]]
        if environ.get("MM_SIGN_PASSWORD"):
            identity += ["/p", environ["MM_SIGN_PASSWORD"]]
    elif environ.get("MM_SIGN_THUMBPRINT"):
        identity = ["/sha1", environ["MM_SIGN_THUMBPRINT"]]
    else:
        return None
    tool = find_signtool(environ)
    if tool is None:
        raise SystemExit("Signing is configured but signtool.exe was not found "
                         "(install the Windows SDK or set MM_SIGNTOOL).")
    timestamp = environ.get("MM_SIGN_TIMESTAMP") or DEFAULT_TIMESTAMP
    return [str(tool), "sign", "/fd", "SHA256", "/tr", timestamp, "/td", "SHA256",
            *identity, "/d", "Money Manager", str(target)]


def sign(target: Path) -> bool:
    """Sign ``target`` when a certificate is configured; True when it was signed."""
    command = signing_command(dict(os.environ), target)
    if command is None:
        print(f"   not signed: {target.name} (no certificate configured)")
        return False
    # The command holds the certificate password: never print it.
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"Signing {target.name} failed (signtool exit {result.returncode}).")
    print(f"   signed: {target.name}")
    return True


def pyinstaller() -> None:
    step("Running PyInstaller")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                    "--distpath", str(DIST), "--workpath", str(BUILD),
                    str(PACKAGING / "MoneyManager.spec")], check=True, cwd=ROOT)
    if not EXE.is_file():
        raise SystemExit(f"PyInstaller did not produce {EXE}")


def add_documents() -> None:
    step("Adding documentation")
    for source, name in EXTRA_FILES.items():
        shutil.copy2(source, APP_DIR / name)
        print(f"   {name}")


def self_test() -> list[dict]:
    step("Self-test of the packaged executable (first run, then restart)")
    folder = Path(tempfile.mkdtemp(prefix="moneymanager-selftest-"))
    # Headless; the offscreen platform has no font database of its own, so point
    # it at the Windows fonts or the screenshots show boxes instead of text.
    environment = {**os.environ, "QT_QPA_PLATFORM": "offscreen",
                   "QT_QPA_FONTDIR": str(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts")}
    environment.pop("MONEY_MANAGER_CONFIG", None)
    reports = []
    for run in ("first run", "restart"):
        result = subprocess.run([str(EXE), "--self-test", str(folder)], env=environment,
                                timeout=300, check=False)
        report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
        reports.append(report)
        for check in report["checks"]:
            mark = "ok  " if check["ok"] else "FAIL"
            print(f"   {mark} {report['phase']}: {check['name']}"
                  + (f" — {check['detail'].splitlines()[0]}" if check["detail"] else ""))
        if result.returncode != 0 or not report["passed"] or report["phase"] != run:
            raise SystemExit(f"Self-test failed ({run}); see {folder / 'report.json'}")
        if not report["frozen"]:
            raise SystemExit("The self-test did not run from the packaged build")
    print(f"   screenshots: {folder / 'screens'}")
    return reports


def package(release_version: str) -> Path:
    step("Creating the release archive")
    RELEASE.mkdir(exist_ok=True)
    archive = RELEASE / f"MoneyManager-{release_version}-windows-x64.zip"
    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(APP_DIR.rglob("*")):
            if path.is_file():
                bundle.write(path, Path("MoneyManager") / path.relative_to(APP_DIR))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n",
                                                  encoding="utf-8")
    return archive


def installer(release_version: str, archive: Path) -> Path:
    """MoneyManager-<version>-Setup.exe, with the release zip as its payload."""
    step("Building the installer")
    work = BUILD / "installer"
    work.mkdir(parents=True, exist_ok=True)
    version_file = work / "version.txt"
    version_file.write_text(release_version, encoding="utf-8")
    payload = work / "MoneyManager.zip"
    shutil.copy2(archive, payload)
    environment = {**os.environ, "MM_PAYLOAD": str(payload), "MM_VERSION_FILE": str(version_file)}
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                    "--distpath", str(work / "dist"), "--workpath", str(work / "build"),
                    str(PACKAGING / "installer" / "Setup.spec")],
                   check=True, cwd=ROOT, env=environment)
    built = work / "dist" / f"MoneyManager-{release_version}-Setup.exe"
    if not built.is_file():
        raise SystemExit(f"PyInstaller did not produce {built}")
    setup = RELEASE / built.name
    shutil.copy2(built, setup)
    sign(setup)

    step("Checking the installer (quiet install into a temporary folder)")
    target = Path(tempfile.mkdtemp(prefix="moneymanager-setup-")) / "MoneyManager"
    result = subprocess.run([str(setup), "--quiet", "--no-shortcuts", "--target", str(target)],
                            timeout=600, check=False)
    manifest = target / "install-manifest.json"
    expected = (target / "MoneyManager.exe", manifest, target / "uninstall.ps1")
    if result.returncode != 0 or not all(path.is_file() for path in expected):
        raise SystemExit(f"The installer check failed (exit {result.returncode}); see {target}")
    print(f"   installed {sum(1 for p in target.rglob('*') if p.is_file())} files into {target}")
    shutil.rmtree(target.parent, ignore_errors=True)
    digest = hashlib.sha256(setup.read_bytes()).hexdigest()
    setup.with_name(setup.name + ".sha256").write_text(f"{digest}  {setup.name}\n",
                                                       encoding="utf-8")
    return setup


def folder_size(folder: Path) -> int:
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip-self-test", action="store_true",
                        help="do not run the packaged self-test (not recommended)")
    arguments = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("The Windows build must be created on Windows.")
    release_version = version()
    clean()
    pyinstaller()
    step("Signing")
    sign(EXE)
    add_documents()
    if not arguments.skip_self_test:
        self_test()
    archive = package(release_version)
    setup = installer(release_version, archive)
    step("Done")
    print(f"   version     {release_version}")
    print(f"   executable  {EXE}")
    print(f"   folder      {folder_size(APP_DIR) / 1e6:.0f} MB")
    print(f"   archive     {archive} ({archive.stat().st_size / 1e6:.0f} MB)")
    print(f"   installer   {setup} ({setup.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
