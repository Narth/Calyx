param(
    [switch]$CoreOnly = $true
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\STATE.md")) { $repoRoot = (Get-Location).Path }
Set-Location $repoRoot

$truthHelper = Join-Path $repoRoot "Scripts\runtime_truth_contract.ps1"
if (-not (Test-Path $truthHelper)) {
    Write-Error "runtime_truth_contract.ps1 not found: $truthHelper"
    exit 1
}
. $truthHelper

$statePath = Join-Path $repoRoot "STATE.md"
$updateScript = Join-Path $repoRoot "Scripts\update_state_checks.ps1"
$sunsetScript = Join-Path $repoRoot "Scripts\sunset_calyx.ps1"
$sunriseScript = Join-Path $repoRoot "Scripts\sunrise_calyx.ps1"
$navScript = Join-Path $repoRoot "Scripts\navigator.ps1"
$triageScript = Join-Path $repoRoot "Scripts\triage_orchestrator.ps1"
$healthPath = Join-Path $repoRoot "runtime\station_health.json"
$heartbeatPath = Join-Path $repoRoot "runtime\station_heartbeat.json"
$snapshotPath = Join-Path $repoRoot "runtime\service_runtime_snapshot.json"
$topologyPath = Join-Path $repoRoot "runtime\runtime_topology_snapshot.json"
$navLockPath = Join-Path $repoRoot "outgoing\navigator.lock"
$triageLockPath = Join-Path $repoRoot "outgoing\triage.lock"
$navLoopStopPath = Join-Path $repoRoot "runtime\navigator_triage.stop"

function Get-StateValue {
    param([string]$Key)
    foreach ($line in (Get-Content -LiteralPath $statePath -Encoding UTF8)) {
        if ($line.StartsWith("${Key}:")) {
            return ($line.Substring($Key.Length + 1)).Trim()
        }
    }
    return ""
}

function Add-ValidationResult {
    param(
        [System.Collections.Generic.List[object]]$Results,
        [string]$Name,
        [bool]$Passed,
        [string]$Detail
    )
    $Results.Add([ordered]@{
        name = $Name
        passed = $Passed
        detail = $Detail
    })
    if (-not $Passed) {
        throw "Validation failed: $Name :: $Detail"
    }
}

function Stop-PowerShellLoopByPattern {
    param([string]$Pattern)
    try {
        $targets = Get-Process powershell -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
                if ($cmd -and $cmd -match $Pattern) { $_ }
            } catch { }
        }
        foreach ($target in $targets) {
            Stop-Process -Id $target.Id -Force -ErrorAction SilentlyContinue
        }
    } catch { }
}

$results = [System.Collections.Generic.List[object]]::new()
$observedStaleDuringSunrise = $false

try {
    if (Test-Path $updateScript) {
        & $updateScript | Out-Null
    }

    # AT-2 Expired advisory locks are ignored by consumers.
    New-Item -ItemType File -Path $navLoopStopPath -Force | Out-Null
    Start-Sleep -Seconds 3
    Stop-PowerShellLoopByPattern -Pattern "navigator_triage_loop\.ps1"
    Set-JsonArtifactStale -Path $navLockPath -ContractName "navigator" -Reason "validation_expired_advisory" | Out-Null
    Set-JsonArtifactStale -Path $triageLockPath -ContractName "triage" -Reason "validation_expired_advisory" | Out-Null
    & $updateScript | Out-Null
    Add-ValidationResult -Results $results -Name "advisory_lock_expiry" -Passed ((Get-StateValue "navigator_interval") -eq "unknown" -and (Get-StateValue "triage_status") -eq "unknown") -Detail "Expired navigator/triage locks were ignored by update_state_checks."
    & $navScript | Out-Null
    & $triageScript | Out-Null
    & $updateScript | Out-Null

    # AT-4 Graceful shutdown stale marking and AT-8 historical non-authority.
    & $sunsetScript -StopOpenClaw -WaitForPortsFree
    $heartbeatJson = Read-JsonArtifact -Path $heartbeatPath
    $snapshotJson = Read-JsonArtifact -Path $snapshotPath
    $topologyJson = Read-JsonArtifact -Path $topologyPath
    Add-ValidationResult -Results $results -Name "shutdown_stale_state" -Passed ((Get-StateValue "runtime_truth_label") -eq "STALE_STATE" -and (Get-StateValue "checks") -match "cbo_core=fail") -Detail "Sunset stale-marked STATE.md and removed active-state illusions."
    Add-ValidationResult -Results $results -Name "shutdown_stale_json" -Passed (($heartbeatJson.truth_state -eq "stale") -and ($snapshotJson.truth_state -eq "stale") -and ($topologyJson.truth_state -eq "stale")) -Detail "Heartbeat, service snapshot, and runtime topology snapshot are stale after shutdown."
    Add-ValidationResult -Results $results -Name "historical_non_authority" -Passed (($heartbeatJson.authoritative_for_liveness -eq $false) -and ($snapshotJson.authoritative_for_liveness -eq $false)) -Detail "Historical heartbeat/snapshot remain visible but non-authoritative."

    Start-Sleep -Seconds 16
    $healthJson = Read-JsonArtifact -Path $healthPath
    $healthTruth = Get-ArtifactFreshness -ContractName "station_health" -Artifact $healthJson -Path $healthPath
    Add-ValidationResult -Results $results -Name "health_ttl_expiry" -Passed ((-not $healthTruth.is_fresh) -and ($healthTruth.stale_label -eq "STALE_HEALTH")) -Detail "station_health.json expires after its TTL."

    # AT-3 Sunrise fresh-only-after-validation.
    $sunriseArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $sunriseScript)
    if ($CoreOnly) { $sunriseArgs += '-StartCoreOnly' }
    $sunriseProc = Start-Process powershell -ArgumentList $sunriseArgs -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru
    $deadline = (Get-Date).AddSeconds(60)
    while (-not $sunriseProc.HasExited -and (Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 1
        if ((Get-StateValue "runtime_truth_label") -eq "STALE_STATE") {
            $observedStaleDuringSunrise = $true
        }
        $sunriseProc.Refresh()
    }
    if (-not $sunriseProc.HasExited) {
        Wait-Process -Id $sunriseProc.Id -Timeout 60
        $sunriseProc.Refresh()
    }
    Add-ValidationResult -Results $results -Name "sunrise_exit_code" -Passed ($sunriseProc.ExitCode -eq 0) -Detail "Sunrise completed successfully."
    & $updateScript | Out-Null
    $heartbeatJson = Read-JsonArtifact -Path $heartbeatPath
    $snapshotJson = Read-JsonArtifact -Path $snapshotPath
    $topologyJson = Read-JsonArtifact -Path $topologyPath
    Add-ValidationResult -Results $results -Name "sunrise_stale_then_fresh" -Passed ($observedStaleDuringSunrise -and (Get-StateValue "runtime_truth_state") -eq "fresh") -Detail "Sunrise kept runtime truth stale before validation, then restored fresh state."
    Add-ValidationResult -Results $results -Name "fresh_json_surfaces" -Passed (($heartbeatJson.truth_state -eq "fresh") -and ($snapshotJson.truth_state -eq "fresh") -and ($topologyJson.truth_state -eq "fresh")) -Detail "Heartbeat, snapshot, and runtime topology returned to fresh after validated sunrise."

    $receiptPayload = [ordered]@{
        schema = "station.phase2_runtime_truth_validation.v1"
        ts_utc = Get-UtcNowString
        core_only = [bool]$CoreOnly
        results = $results
    }
    $receiptPath = Write-RuntimeTruthReceipt -RepoRoot $repoRoot -RelativeDir "runtime\receipts\audit" -Prefix "wo_phase2_runtime_truth_validation" -Payload $receiptPayload
    Write-Host "Validation receipt: $receiptPath"
} catch {
    $failurePayload = [ordered]@{
        schema = "station.phase2_runtime_truth_validation.v1"
        ts_utc = Get-UtcNowString
        core_only = [bool]$CoreOnly
        results = $results
        error = $_.Exception.Message
    }
    $receiptPath = Write-RuntimeTruthReceipt -RepoRoot $repoRoot -RelativeDir "runtime\receipts\audit" -Prefix "wo_phase2_runtime_truth_validation" -Payload $failurePayload
    Write-Host "Validation receipt: $receiptPath"
    throw
}
