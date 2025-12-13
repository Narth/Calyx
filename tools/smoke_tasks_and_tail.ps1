# Starts all scheduled tasks whose names start with 'Calyx' and tails the latest logs in outgoing\tasks\
$tasks = Get-ScheduledTask | Where-Object { $_.TaskName -like 'Calyx*' }
if ($tasks) {
    foreach ($t in $tasks) {
        try {
            Start-ScheduledTask -TaskName $t.TaskName -ErrorAction Stop
            Write-Output "Started: $($t.TaskName)"
        } catch {
            Write-Output "Failed to start: $($t.TaskName) - $($_.Exception.Message)"
        }
    }
} else {
    Write-Output "No Calyx scheduled tasks found."
}

Start-Sleep -Seconds 8

$files = Get-ChildItem -Path .\outgoing\tasks\ -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 6
if ($files) {
    foreach ($f in $files) {
        Write-Output ("--- {0}  {1} ---" -f $f.Name, $f.LastWriteTime)
        Get-Content -Path $f.FullName -Tail 200 -Encoding utf8
        Write-Output "`n"
    }
} else {
    Write-Output "No outgoing task logs found."
}
