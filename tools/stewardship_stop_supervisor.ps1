param(
    [string]$Root = $null
)

$ErrorActionPreference = 'Continue'

if ([string]::IsNullOrWhiteSpace($Root)) {
    $Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
} else {
    try { $Root = (Resolve-Path $Root).Path } catch { }
}

$Targets = @(
    'tools\svc_supervisor_adaptive.py',
    'tools\uptime_tracker.py',
    'tools\enhanced_metrics_collector.py',
    'tools\telemetry_sentinel.py',
    'tools\bridge_pulse_scheduler.py'
)

function Get-Procs {
    try {
        return Get-CimInstance Win32_Process
    } catch {
        try {
            return Get-WmiObject Win32_Process
        } catch {
            return @()
        }
    }
}

function Find-Procs([string]$Needle) {
    $procs = Get-Procs
    if (-not $procs) { return @() }

    return $procs |
        Where-Object {
            $_.CommandLine -and ($_.CommandLine -like ('*' + $Needle + '*'))
        } |
        Select-Object ProcessId, Name, CommandLine
}

$all = @()
foreach ($t in $Targets) {
    $all += Find-Procs $t
}

$all = $all | Sort-Object ProcessId -Unique

if (-not $all -or $all.Count -eq 0) {
    Write-Output 'No stewardship supervisor/loop processes found.'
    exit 0
}

Write-Output ('Stopping ' + $all.Count + ' process(es)...')
foreach ($p in $all) {
    Write-Output ('- pid=' + $p.ProcessId + ' name=' + $p.Name)
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Milliseconds 300
Write-Output 'Stop attempt complete. Locks may remain until overwritten.'
exit 0
