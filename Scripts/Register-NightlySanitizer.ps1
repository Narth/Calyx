param(
    [string]$Time = "03:15",
    [string]$TaskName = "Calyx Nightly Sanitizer",
    [string]$PythonPath = "C:\Calyx_Terminal\.venv\Scripts\python.exe",
    [string]$RepoPath = "C:\Calyx_Terminal"
)

$ErrorActionPreference = 'Stop'

Write-Host "Registering scheduled task '$TaskName' to run daily at $Time..." -ForegroundColor Cyan

# Build arguments to run sanitizer with absolute path
$scriptArg = "-u tools\sanitize_records.py"

# Ensure paths exist
if (-not (Test-Path $PythonPath)) { throw "Python not found at '$PythonPath'" }
if (-not (Test-Path $RepoPath)) { throw "Repo path not found: '$RepoPath'" }

# Create action: call python with sanitize script; use repo path in argument to avoid cwd dependency
$action = New-ScheduledTaskAction -Execute $PythonPath -Argument $scriptArg

# Daily trigger
$trigger = New-ScheduledTaskTrigger -Daily -At $Time

# Basic settings: run on battery, don't stop on battery switch
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# Create or replace the scheduled task for current user context
try {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false | Out-Null
    }
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Canonicalize & dedupe SVF records nightly" | Out-Null
    Write-Host "Scheduled task '$TaskName' registered successfully." -ForegroundColor Green
}
catch {
    Write-Error $_
    exit 1
}
