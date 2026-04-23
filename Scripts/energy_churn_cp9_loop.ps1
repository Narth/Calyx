# Energy Churn + CP9 Auto-Tuner loop — trend analysis and tuning recommendations.
# Runs every IntervalSec (default 300 = 5 min). Energy churn needs history; CP9 reads nav/triage/churn.
# Stop: create runtime\energy_churn_cp9.stop
# Usage: .\Scripts\energy_churn_cp9_loop.ps1 [-IntervalSec 300]
# See: docs/planning/ENERGY_CHURN_ANALYSIS_PLAN.md, docs/AGENT_REPOSITORY.md

param(
    [int]$IntervalSec = 300,
    [string]$StopFile = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) { $repoRoot = (Get-Location).Path }
Set-Location $repoRoot

if (-not $StopFile) { $StopFile = Join-Path $repoRoot "runtime\energy_churn_cp9.stop" }
$churnScript = Join-Path $repoRoot "Scripts\energy_churn_analyzer.ps1"
$cp9Script = Join-Path $repoRoot "tools\cp9_auto_tuner.py"
$venvPython = Join-Path $repoRoot ".venv_cbohub311\Scripts\python.exe"

if (-not (Test-Path $churnScript)) {
    Write-Error "energy_churn_analyzer.ps1 not found: $churnScript"
}
if (-not (Test-Path $cp9Script)) {
    Write-Error "cp9_auto_tuner.py not found: $cp9Script"
}
if (-not (Test-Path $venvPython)) {
    Write-Error "Venv Python not found: $venvPython"
}

Write-Host "Energy Churn + CP9 loop started (interval ${IntervalSec}s). Stop: New-Item -ItemType File -Path runtime\energy_churn_cp9.stop -Force" -ForegroundColor Cyan

while ($true) {
    if (Test-Path -LiteralPath $StopFile -PathType Leaf) {
        Write-Host "Stop file detected. Exiting." -ForegroundColor Gray
        Remove-Item -LiteralPath $StopFile -Force -ErrorAction SilentlyContinue
        break
    }

    & $churnScript 2>&1 | Out-Null
    & $venvPython $cp9Script 2>&1 | Out-Null

    $sleepSec = [Math]::Max(60, $IntervalSec - 10)
    Start-Sleep -Seconds $sleepSec
}
