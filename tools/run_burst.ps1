# Station Calyx — Burst runner
# Runs a short burst of snapshots and bridge pulses. Safe Mode only; file writes.

param(
    [int]$SnapshotIntervalSec = 150,   # 2.5 minutes
    [int]$SnapshotIterations  = 48,    # ~2 hours at 2.5-minute cadence
    [int]$PulseIntervalSec    = 300,   # 5 minutes
    [int]$PulseIterations     = 24     # ~2 hours at 5-minute cadence
)

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)

function Write-Snapshot {
    param($rootPath, $index)
    $ts = (Get-Date).ToUniversalTime().ToString('o')
    $count = (Get-Process python -ErrorAction SilentlyContinue | Measure-Object).Count
    $obj = [pscustomobject]@{
        timestamp = $ts
        count     = $count
        note      = "burst snapshot $index"
    }
    $obj | ConvertTo-Json -Compress | Add-Content -Path (Join-Path $rootPath 'logs/system_snapshots.jsonl')
    Write-Host "[snap] $ts count=$count idx=$index"
}

function Write-Pulse {
    param($rootPath)
    $id = ('burst-{0:yyyyMMddTHHmmss}' -f (Get-Date).ToUniversalTime())
    $script = Join-Path $rootPath 'tools/bridge_pulse_generator.py'
    & python $script --report-id $id | Out-String | Write-Host
}

for($i=0; $i -lt [Math]::Max($SnapshotIterations, $PulseIterations); $i++){
    if($i -lt $SnapshotIterations){ Write-Snapshot -rootPath $root -index $i }
    if($i -lt $PulseIterations){ Write-Pulse -rootPath $root }
    Start-Sleep -Seconds ([Math]::Min($SnapshotIntervalSec, $PulseIntervalSec))
}
