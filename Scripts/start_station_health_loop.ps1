# Start the Station health loop (4s schedule) in the background.
# Writes runtime/station_health.json. Stop by creating runtime/station_health.stop.
# Usage: .\Scripts\start_station_health_loop.ps1
# See: docs/operations/STATION_HEALTH_BLOOMOS_AUDIT.md, HEARTBEAT.md

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
Set-Location $repoRoot

$loopScript = Join-Path $repoRoot "Scripts\station_health_loop.ps1"
if (-not (Test-Path $loopScript)) {
    Write-Error "station_health_loop.ps1 not found: $loopScript"
}

Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',$loopScript -WindowStyle Hidden
Write-Host "Station health loop started (background). Stop: New-Item -ItemType File -Path runtime\station_health.stop -Force" -ForegroundColor Cyan
