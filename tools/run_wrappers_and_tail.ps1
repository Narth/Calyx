$wrappers = @(
    '.\\tools\\CalyxWatchdogRepair_wrapper.bat',
    '.\\tools\\CalyxTriageProbe_wrapper.bat',
    '.\\tools\\CalyxAutonomyMonitor_wrapper.bat',
    '.\\tools\\CalyxAlertsCleanup_wrapper.bat',
    '.\\tools\\CalyxMetricsCron_wrapper.bat',
    '.\\tools\\CalyxSupervisorAdaptive_wrapper.bat'
)

foreach ($w in $wrappers) {
    if (Test-Path $w) {
        Write-Output "Running wrapper: $w"
        & $w
        Start-Sleep -Milliseconds 700
    } else {
        Write-Output "Missing wrapper: $w"
    }
}

Start-Sleep -Seconds 1
$files = Get-ChildItem -Path .\outgoing\tasks\ -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 8
if ($files) {
    foreach ($f in $files) {
        Write-Output "--- $($f.Name)  $($f.LastWriteTime) ---"
        Get-Content -Path $f.FullName -Tail 200 -Encoding utf8
        Write-Output "`n"
    }
} else {
    Write-Output "No outgoing task logs found."
}
