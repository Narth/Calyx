param(
    [string]$OutDir = "logs\calyx_guardian",
    [string]$CorrelationId,
    [string]$ParentCorrelationId,
    [int]$TimeoutSeconds = 1200
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($CorrelationId)) {
    throw "CorrelationId is required"
}

$taskName = "CalyxGuardianPhase0Elevated"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$manifest = Join-Path $scriptDir "render\guardian_manifest.py"
$receiptPath = Join-Path $OutDir "elevation_receipt.json"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -TaskName $taskName
$startUtc = (Get-Date).ToUniversalTime().ToString("o")

Start-ScheduledTask -TaskName $taskName

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$lastRunTime = $info.LastRunTime
$completed = $false

while ($stopwatch.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
    Start-Sleep -Seconds 5
    $info = Get-ScheduledTaskInfo -TaskName $taskName
    $task = Get-ScheduledTask -TaskName $taskName
    if ($info.LastRunTime -gt $lastRunTime -and $task.State -ne "Running") {
        $completed = $true
        break
    }
}

$endUtc = (Get-Date).ToUniversalTime().ToString("o")
$lastResult = $info.LastTaskResult

$elevationStatusPath = Join-Path $OutDir "elevation_status.json"
$elevationStatus = $null
if (Test-Path $elevationStatusPath) {
    try {
        $elevationStatus = Get-Content -Path $elevationStatusPath -Raw | ConvertFrom-Json
    } catch {
        $elevationStatus = $null
    }
}

$receipt = [ordered]@{
    task_name = $taskName
    correlation_id = $CorrelationId
    parent_correlation_id = $ParentCorrelationId
    start_utc = $startUtc
    end_utc = $endUtc
    completed = $completed
    last_run_result = $lastResult
    elevation_achieved = if ($null -ne $elevationStatus) { [bool]$elevationStatus.is_admin } else { $false }
}
$receipt | ConvertTo-Json -Depth 4 | Set-Content -Path $receiptPath -Encoding utf8

$manifestArgs = @(
    "-3.11",
    $manifest,
    "--outdir",
    $OutDir,
    "--correlation-id",
    $CorrelationId
)
if ($ParentCorrelationId) {
    $manifestArgs += @("--parent-correlation-id", $ParentCorrelationId)
}
py $manifestArgs

if (-not $completed) {
    throw "Elevated Phase 0 task did not complete within timeout"
}

Write-Host "Elevated Phase 0 complete. Receipt: $receiptPath"
