<#
.SYNOPSIS
  Install Calyx scheduled tasks and optional supporting registrations.

.DESCRIPTION
  Convenience wrapper to register the Station Calyx scheduled tasks using the
  `register_calyx_scheduled_tasks.ps1` helper. Runs a dry-run by default; use
  -Install to actually register. When -StartNow is given the script will attempt
  to start each scheduled task after registering it.

.NOTES
  This wrapper keeps the UX simpler for operators: one command to install Calyx
  services and optionally start them immediately. Tasks are registered under
  the current user account unless -UseSystem is provided and this script is run
  elevated.
#>

param(
    [switch]$Install,
    [switch]$Force,
    [switch]$StartNow,
    [switch]$UseSystem,
    [string]$PythonPath = "python"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$reg = Join-Path $scriptDir "register_calyx_scheduled_tasks.ps1"

if (-not (Test-Path $reg)) {
    Write-Host "Cannot find register_calyx_scheduled_tasks.ps1 at $reg" -ForegroundColor Red
    exit 2
}

$args = @()
if ($Install) { $args += '-Install' }
if ($Force)   { $args += '-Force' }
if ($UseSystem){ $args += '-UseSystem' }
$args += "-PythonPath `"$PythonPath`""

Write-Host "Invoking: $reg $($args -join ' ')"

# Run the register script in the same process
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $reg @args

if ($Install -and $StartNow) {
    # start the tasks we just installed
    $taskNames = @("Calyx Alerts Cleanup","Calyx Autonomy Monitor","Calyx Watchdog Repair","Calyx Triage Probe","Calyx Metrics Cron","Calyx Supervisor Adaptive")
    foreach ($t in $taskNames) {
        try {
            Write-Host "Attempting to start task: $t"
            Start-ScheduledTask -TaskName $t -ErrorAction Stop
            Write-Host "Started: $t"
        } catch {
            Write-Host ("Failed to start task {0}: {1}" -f $t, $_)
        }
    }
}

Write-Host "install_calyx_services: completed (dry-run if -Install not provided)"
