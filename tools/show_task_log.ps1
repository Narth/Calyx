<#
.SYNOPSIS
  Show the most recent launcher log for a Calyx scheduled task.

.DESCRIPTION
  Given a task name, this helper finds the newest log in outgoing/tasks that
  matches the alphanumeric characters of the task name and prints the file path
  and the last N lines. If no task name is provided, it lists the 20 most recent
  log files in outgoing/tasks.

.EXAMPLE
  # Show last 200 lines for 'Calyx Alerts Cleanup'
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\show_task_log.ps1 -TaskName "Calyx Alerts Cleanup"

#>
param(
    [string]$TaskName = "",
    [int]$Tail = 200
)

Set-StrictMode -Version Latest

try {
    $root = (Resolve-Path "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)\..\").Path
} catch {
    $root = Get-Location
}

$outDir = Join-Path $root 'outgoing\tasks'
if (-not (Test-Path $outDir)) {
    Write-Host "No outgoing/tasks directory found at: $outDir" -ForegroundColor Yellow
    exit 1
}

if ([string]::IsNullOrWhiteSpace($TaskName)) {
    Write-Host "Recent logs in $($outDir):" -ForegroundColor Cyan
    Get-ChildItem -Path $outDir -File | Sort-Object LastWriteTime -Descending | Select-Object -First 20 | ForEach-Object {
        Write-Host "- $($_.Name)  ($($_.LastWriteTime))"
    }
    exit 0
}

# Normalize task name to alphanumeric key (matches launcher safeName logic)
$key = ($TaskName -replace '\W','')
Write-Host "Searching logs for task: '$TaskName' (key: $key)" -ForegroundColor Cyan

$candidates = Get-ChildItem -Path $outDir -File | Where-Object { $_.Name -like "*$key*" } | Sort-Object LastWriteTime -Descending
if (-not $candidates -or $candidates.Count -eq 0) {
    Write-Host "No logs found matching key: $key" -ForegroundColor Yellow
    exit 2
}

$latest = $candidates | Select-Object -First 1
Write-Host "Found log: $($latest.FullName)  ($($latest.LastWriteTime))" -ForegroundColor Green
Write-Host "--- Last $Tail lines ---" -ForegroundColor Gray
Get-Content -Path $latest.FullName -Tail $Tail | ForEach-Object { Write-Host $_ }
exit 0
