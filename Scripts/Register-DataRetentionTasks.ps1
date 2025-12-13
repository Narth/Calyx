# Register Data Retention Scheduled Tasks for Station Calyx
# This script registers weekly archival and monthly cleanup tasks

param(
    [string]$PythonPath = "C:\Calyx_Terminal\.venv\Scripts\python.exe",
    [string]$WorkingDir = "C:\Calyx_Terminal"
)

Write-Host "[CBO] Registering data retention scheduled tasks..." -ForegroundColor Cyan

# Verify Python path exists
if (-not (Test-Path $PythonPath)) {
    Write-Host "[CBO] ERROR: Python path not found: $PythonPath" -ForegroundColor Red
    Write-Host "[CBO] Please update PythonPath parameter" -ForegroundColor Yellow
    exit 1
}

# Verify working directory exists
if (-not (Test-Path $WorkingDir)) {
    Write-Host "[CBO] ERROR: Working directory not found: $WorkingDir" -ForegroundColor Red
    exit 1
}

# Task 1: Weekly Agent Run Archival (Sunday @ 02:00)
Write-Host "[CBO] Registering Weekly Agent Run Archival task..." -ForegroundColor Green
$action1 = New-ScheduledTaskAction -Execute $PythonPath -Argument "-u tools\archive_agent_runs.py --days 7" -WorkingDirectory $WorkingDir
$trigger1 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "02:00"
$settings1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal1 = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

try {
    Register-ScheduledTask -TaskName "Calyx Weekly Agent Run Archival" -Action $action1 -Trigger $trigger1 -Settings $settings1 -Principal $principal1 -Description "Archive agent_run directories older than 7 days" -Force | Out-Null
    Write-Host "[CBO] ✓ Weekly Agent Run Archival registered successfully" -ForegroundColor Green
} catch {
    Write-Host "[CBO] ✗ Failed to register Weekly Agent Run Archival: $_" -ForegroundColor Red
}

# Task 2: Weekly Chronicles Archival (Sunday @ 02:30)
Write-Host "[CBO] Registering Weekly Chronicles Archival task..." -ForegroundColor Green
$action2 = New-ScheduledTaskAction -Execute $PythonPath -Argument "-u tools\archive_chronicles.py --days 7" -WorkingDirectory $WorkingDir
$trigger2 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "02:30"
$settings2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal2 = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

try {
    Register-ScheduledTask -TaskName "Calyx Weekly Chronicles Archival" -Action $action2 -Trigger $trigger2 -Settings $settings2 -Principal $principal2 -Description "Archive chronicles older than 7 days" -Force | Out-Null
    Write-Host "[CBO] ✓ Weekly Chronicles Archival registered successfully" -ForegroundColor Green
} catch {
    Write-Host "[CBO] ✗ Failed to register Weekly Chronicles Archival: $_" -ForegroundColor Red
}

# Task 3: Weekly SVF Log Archival (Sunday @ 03:00)
Write-Host "[CBO] Registering Weekly SVF Log Archival task..." -ForegroundColor Green
$action3 = New-ScheduledTaskAction -Execute $PythonPath -Argument "-m tools.log_housekeeper run --keep-days 14" -WorkingDirectory $WorkingDir
$trigger3 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "03:00"
$settings3 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal3 = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

try {
    Register-ScheduledTask -TaskName "Calyx Weekly SVF Log Archival" -Action $action3 -Trigger $trigger3 -Settings $settings3 -Principal $principal3 -Description "Archive SVF logs and reports older than 14 days" -Force | Out-Null
    Write-Host "[CBO] ✓ Weekly SVF Log Archival registered successfully" -ForegroundColor Green
} catch {
    Write-Host "[CBO] ✗ Failed to register Weekly SVF Log Archival: $_" -ForegroundColor Red
}

# Task 4: Monthly Archive Verification (1st of month @ 04:00)
Write-Host "[CBO] Registering Monthly Archive Verification task..." -ForegroundColor Green
$action4 = New-ScheduledTaskAction -Execute $PythonPath -Argument "-u tools\verify_archives.py" -WorkingDirectory $WorkingDir
$trigger4 = New-ScheduledTaskTrigger -Monthly -DaysOfMonth 1 -At "04:00"
$settings4 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal4 = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

try {
    Register-ScheduledTask -TaskName "Calyx Monthly Archive Verification" -Action $action4 -Trigger $trigger4 -Settings $settings4 -Principal $principal4 -Description "Verify archive integrity and report space savings" -Force | Out-Null
    Write-Host "[CBO] ✓ Monthly Archive Verification registered successfully" -ForegroundColor Green
} catch {
    Write-Host "[CBO] ⚠ Could not register Monthly Archive Verification (verify_archives.py may not exist yet)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[CBO] Data retention scheduled tasks registration complete!" -ForegroundColor Cyan
Write-Host "[CBO] To view registered tasks:" -ForegroundColor Yellow
Write-Host "    Get-ScheduledTask -TaskName 'Calyx*'" -ForegroundColor White
Write-Host ""
Write-Host "[CBO] To unregister tasks:" -ForegroundColor Yellow
Write-Host "    Unregister-ScheduledTask -TaskName 'Calyx Weekly Agent Run Archival'" -ForegroundColor White
Write-Host "    Unregister-ScheduledTask -TaskName 'Calyx Weekly Chronicles Archival'" -ForegroundColor White
Write-Host "    Unregister-ScheduledTask -TaskName 'Calyx Weekly SVF Log Archival'" -ForegroundColor White
Write-Host "    Unregister-ScheduledTask -TaskName 'Calyx Monthly Archive Verification'" -ForegroundColor White
