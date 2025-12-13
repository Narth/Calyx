param(
    [switch]$EnableScheduler,
    [switch]$NetworkOn,
    [switch]$NavigatorControlOnWindows,
    [int]$Interval = 30,
    [int]$SupervisorInterval = 60,
    [int]$MetricsInterval = 900,
    [int]$HousekeepingKeepDays = 14,
    [switch]$DryRun,
    [switch]$Status
)

$ErrorActionPreference = 'Stop'
Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location -Path (Resolve-Path '..')

# Try to activate venv if present (no-op if missing)
$venv311 = Join-Path (Get-Location) '.venv311/Scripts/Activate.ps1'
$venv = Join-Path (Get-Location) '.venv/Scripts/Activate.ps1'
# Prefer the Python 3.11 venv for LLM-ready tooling; fall back to legacy venv if missing.
if (Test-Path $venv311) {
    . $venv311
} elseif (Test-Path $venv) {
    . $venv
}

$python = 'python'
if (Test-Path '.venv311/Scripts/python.exe') {
    $python = (Resolve-Path '.venv311/Scripts/python.exe').Path
} elseif (Test-Path '.venv/Scripts/python.exe') {
    $python = (Resolve-Path '.venv/Scripts/python.exe').Path
}

$argv = @('-u', 'tools/cbo_overseer.py', '--interval', $Interval, '--supervisor-interval', $SupervisorInterval, '--metrics-interval', $MetricsInterval, '--housekeeping-keep-days', $HousekeepingKeepDays)
if ($EnableScheduler) { $argv += '--enable-scheduler' }
if ($NetworkOn) { $argv += '--network-on' }
if ($NavigatorControlOnWindows) { $argv += '--navigator-control-on-windows' }
if ($DryRun) { $argv += '--dry-run' }
if ($Status) { $argv += '--status' }

& $python @argv
