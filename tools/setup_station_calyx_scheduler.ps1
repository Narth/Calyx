# Station Calyx — Task Scheduler setup
# Creates three scheduled tasks:
#  - Daily burst at 00:00 local (run_burst.ps1)
#  - Hourly pulse (pulse_once.ps1)
#  - Snapshots every 15 minutes (snapshot_once.ps1)
#
# Requires Task Scheduler permissions.

$root    = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$burst   = Join-Path $root 'tools/run_burst.ps1'
$pulse   = Join-Path $root 'tools/pulse_once.ps1'
$snap    = Join-Path $root 'tools/snapshot_once.ps1'

function New-Task {
    param($name, $scheduleArgs)
    $taskCmd = "`"powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$($scheduleArgs.Script)`"`""
    $args = @(
        '/Create',
        '/TN', $name,
        '/TR', $taskCmd,
        '/F'
    ) + $scheduleArgs.Schedule
    Write-Host "Creating task $name ..."
    $proc = Start-Process -FilePath 'schtasks' -ArgumentList $args -NoNewWindow -PassThru -Wait
    if($proc.ExitCode -ne 0){ Write-Warning "Task $name creation exit code $($proc.ExitCode)" }
}

New-Task -name 'Calyx_Burst_Daily' -scheduleArgs @{
    Script   = $burst
    Schedule = @('/SC','DAILY','/ST','00:00')
}

New-Task -name 'Calyx_Pulse_Hourly' -scheduleArgs @{
    Script   = $pulse
    Schedule = @('/SC','HOURLY','/MO','1')
}

New-Task -name 'Calyx_Snapshot_15min' -scheduleArgs @{
    Script   = $snap
    Schedule = @('/SC','MINUTE','/MO','15')
}

Write-Host "Done. Verify with: schtasks /Query /TN Calyx_*"
