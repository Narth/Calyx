# CP6 Sociologist + CP7 Chronicler loop - Phase 3: harmony and drift.
# Runs every IntervalSec (default 600 = 10 min). Lightweight; reads locks and health.
# Stop: create runtime\cp6_cp7.stop
# Usage: .\Scripts\cp6_cp7_loop.ps1 [-IntervalSec 600]
# See: docs/AGENT_REPOSITORY.md, docs/CP6.md

param(
    [int]$IntervalSec = 600,
    [string]$StopFile = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) { $repoRoot = (Get-Location).Path }
Set-Location $repoRoot

if (-not $StopFile) { $StopFile = Join-Path $repoRoot "runtime\cp6_cp7.stop" }
$cp6Script = Join-Path $repoRoot "tools\cp6_sociologist.py"
$cp7Script = Join-Path $repoRoot "tools\cp7_chronicler.py"
$venvPython = Join-Path $repoRoot ".venv_cbohub311\Scripts\python.exe"

if (-not (Test-Path $cp6Script)) { Write-Error "cp6_sociologist.py not found: $cp6Script" }
if (-not (Test-Path $cp7Script)) { Write-Error "cp7_chronicler.py not found: $cp7Script" }
if (-not (Test-Path $venvPython)) { Write-Error "Venv Python not found: $venvPython" }

Write-Host "CP6+CP7 loop started (interval ${IntervalSec}s). Stop: New-Item -ItemType File -Path runtime\cp6_cp7.stop -Force" -ForegroundColor Cyan

while ($true) {
    if (Test-Path -LiteralPath $StopFile -PathType Leaf) {
        Write-Host "Stop file detected. Exiting." -ForegroundColor Gray
        Remove-Item -LiteralPath $StopFile -Force -ErrorAction SilentlyContinue
        break
    }

    & $venvPython $cp6Script 2>&1 | Out-Null
    & $venvPython $cp7Script 2>&1 | Out-Null

    $sleepSec = [Math]::Max(60, $IntervalSec - 10)
    Start-Sleep -Seconds $sleepSec
}
