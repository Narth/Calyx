# Navigator + Triage loop — ship's wheel and medical unit. Runs every IntervalSec (default 120 = 2 min).
# Writes outgoing/navigator.lock and outgoing/triage.lock. BloomOS and CBO read these for cadence and health.
# Stop: create runtime\navigator_triage.stop
# Usage: .\Scripts\navigator_triage_loop.ps1 [-IntervalSec 120]
# See: docs/operations/NAVIGATOR_TRIAGE_MINIMAL_SUNRISE.md, docs/AGENT_REPOSITORY.md

param(
    [int]$IntervalSec = 120,
    [string]$StopFile = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) { $repoRoot = (Get-Location).Path }
Set-Location $repoRoot

if (-not $StopFile) { $StopFile = Join-Path $repoRoot "runtime\navigator_triage.stop" }
$navScript = Join-Path $repoRoot "Scripts\navigator.ps1"
$triageScript = Join-Path $repoRoot "Scripts\triage_orchestrator.ps1"

if (-not (Test-Path $navScript)) {
    Write-Error "navigator.ps1 not found: $navScript"
}
if (-not (Test-Path $triageScript)) {
    Write-Error "triage_orchestrator.ps1 not found: $triageScript"
}

Write-Host "Navigator+Triage loop started (interval ${IntervalSec}s). Stop: New-Item -ItemType File -Path runtime\navigator_triage.stop -Force" -ForegroundColor Cyan

while ($true) {
    if (Test-Path -LiteralPath $StopFile -PathType Leaf) {
        Write-Host "Stop file detected. Exiting." -ForegroundColor Gray
        Remove-Item -LiteralPath $StopFile -Force -ErrorAction SilentlyContinue
        break
    }

    & $navScript | Out-Null
    & $triageScript | Out-Null

    $sleepSec = [Math]::Max(60, $IntervalSec - 5)
    Start-Sleep -Seconds $sleepSec
}
