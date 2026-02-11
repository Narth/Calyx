param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $scriptDir ".venv"
$requirementsPath = Join-Path $scriptDir "requirements-dev.txt"

if (!(Test-Path $requirementsPath)) {
    throw "requirements-dev.txt not found at $requirementsPath"
}

if (!(Test-Path $venvPath)) {
    py -3.11 -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create virtual environment at $venvPath"
    }
}

py -3.11 -m pip install --user -r $requirementsPath
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install dev requirements to user site"
}

$venvPython = Join-Path $venvPath "Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython -m pip install -r $requirementsPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install dev requirements into venv"
    }
}

py -3.11 -m pytest --version
if ($LASTEXITCODE -ne 0) {
    throw "pytest verification failed"
}
