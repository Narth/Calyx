# Start Calyx scheduled tasks and list recent launcher logs
$names = @(
    'Calyx Alerts Cleanup',
    'Calyx Autonomy Monitor',
    'Calyx Watchdog Repair',
    'Calyx Triage Probe',
    'Calyx Metrics Cron',
    'Calyx Supervisor Adaptive'
)
foreach ($n in $names) {
    try {
        Start-ScheduledTask -TaskName $n -ErrorAction Stop
        Write-Host "Started: $n"
    } catch {
        Write-Host "Start attempt for $n failed: $_"
    }
}
Start-Sleep -Seconds 8
Get-ChildItem -Path .\outgoing\tasks\ -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 20 Name,LastWriteTime,Length | Format-Table -AutoSize
