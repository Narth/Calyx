# Inspect registered scheduled tasks that start with 'Calyx' and print their action command and arguments
$tasks = Get-ScheduledTask | Where-Object { $_.TaskName -like 'Calyx*' }
if (-not $tasks) { Write-Output 'No Calyx scheduled tasks found.'; exit 0 }
foreach ($t in $tasks) {
    Write-Output "Task: $($t.TaskName)"
    $s = Get-ScheduledTask -TaskName $t.TaskName
    foreach ($a in $s.Actions) {
        Write-Output ("  Execute: {0}" -f $a.Execute)
        Write-Output ("  Arguments: {0}" -f $a.Arguments)
        Write-Output ""
    }
}
