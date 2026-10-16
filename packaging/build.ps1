# Build the Windows release with the project's virtual environment.
#   powershell -ExecutionPolicy Bypass -File packaging\build.ps1
# See packaging\build.py for the steps.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "No virtual environment found. Run: py -3.12 -m venv .venv; .venv\Scripts\pip install -r requirements-dev.txt"
}
& $python (Join-Path $PSScriptRoot "build.py") @args
exit $LASTEXITCODE
