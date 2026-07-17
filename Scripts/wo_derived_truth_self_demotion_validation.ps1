param()

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

$updateScript = Join-Path $repoRoot "Scripts\update_state_checks.ps1"
$checkScript = Join-Path $repoRoot "Scripts\check_calyx_core_services.ps1"
$statePath = Join-Path $repoRoot "STATE.md"
$heartbeatPath = Join-Path $repoRoot "runtime\station_heartbeat.json"
$snapshotPath = Join-Path $repoRoot "runtime\service_runtime_snapshot.json"
$topologyPath = Join-Path $repoRoot "runtime\runtime_topology_snapshot.json"
$securityReceiptDir = Join-Path $repoRoot "runtime\receipts\security"

function Get-UtcNowOffset {
    return [DateTimeOffset]::UtcNow
}

function Convert-ToUtcOffset {
    param([Parameter(Mandatory = $true)][string]$Value)
    return [DateTimeOffset]::Parse($Value).ToUniversalTime()
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

function Get-CurrentSnapshot {
    $state = Read-StateRuntimeBlock -StatePath $statePath
    $heartbeat = Read-JsonArtifact -Path $heartbeatPath
    $snapshot = Read-JsonArtifact -Path $snapshotPath
    $topology = Read-JsonArtifact -Path $topologyPath
    $checks = (& $checkScript | Select-Object -First 1).Trim()
    return [ordered]@{
        observed_ts_utc = (Get-UtcNowOffset).ToString("o")
        state = $state
        heartbeat = $heartbeat
        snapshot = $snapshot
        topology = $topology
        checks = $checks
    }
}

function Get-NewTransitionReceipts {
    param([Parameter(Mandatory = $true)][DateTimeOffset]$SinceUtc)
    if (-not (Test-Path -LiteralPath $securityReceiptDir -PathType Container)) { return @() }
    $receipts = @()
    foreach ($path in (Get-ChildItem -LiteralPath $securityReceiptDir -Filter "runtime_truth_transition__*.json" -File | Sort-Object LastWriteTimeUtc)) {
        $receipt = Read-JsonArtifact -Path $path.FullName
        if (-not $receipt) { continue }
        $tsRaw = if ($receipt.ts_utc) { [string]$receipt.ts_utc } else { "" }
        if (-not $tsRaw) { continue }
        $ts = Convert-ToUtcOffset -Value $tsRaw
        if ($ts -lt $SinceUtc) { continue }
        $receipts += [pscustomobject]@{
            path = $path.FullName
            receipt = $receipt
            ts_utc = $ts
        }
    }
    return $receipts
}

function Wait-ForDerivedStale {
    param(
        [Parameter(Mandatory = $true)][DateTimeOffset]$DeadlineUtc
    )
    while ((Get-UtcNowOffset) -lt $DeadlineUtc) {
        $snap = Get-CurrentSnapshot
        $stateStale = $snap.state -and ($snap.state.runtime_truth_state -eq "stale") -and ($snap.state.runtime_truth_label -eq "STALE_STATE")
        $heartbeatStale = $snap.heartbeat -and ($snap.heartbeat.truth_state -eq "stale") -and ($snap.heartbeat.stale_label -eq "STALE_HEARTBEAT")
        $snapshotStale = $snap.snapshot -and ($snap.snapshot.truth_state -eq "stale") -and ($snap.snapshot.stale_label -eq "STALE_SNAPSHOT")
        $topologyStale = $snap.topology -and ($snap.topology.truth_state -eq "stale") -and ($snap.topology.stale_label -eq "STALE_TOPOLOGY")
        if ($stateStale -and $heartbeatStale -and $snapshotStale -and $topologyStale) {
            return $snap
        }
        Start-Sleep -Seconds 2
    }
    return $null
}

$results = [System.Collections.Generic.List[object]]::new()
$scriptStartUtc = Get-UtcNowOffset
$staleObservedUtc = $null

try {
    & $updateScript | Out-Null
    $freshSnap = Get-CurrentSnapshot

    $sameHeartbeat = ($freshSnap.state.heartbeat_ts -eq $freshSnap.heartbeat.heartbeat_emitted_ts) -and ($freshSnap.heartbeat.heartbeat_emitted_ts -eq $freshSnap.snapshot.heartbeat_emitted_ts)
    $sameExpiry = ($freshSnap.state.runtime_truth_expires_ts -eq $freshSnap.heartbeat.expires_ts_utc) -and ($freshSnap.heartbeat.expires_ts_utc -eq $freshSnap.snapshot.expires_ts_utc)
    $freshAligned = ($freshSnap.state.runtime_truth_state -eq "fresh") -and ($freshSnap.heartbeat.truth_state -eq "fresh") -and ($freshSnap.snapshot.truth_state -eq "fresh")
    $checksAligned = ($freshSnap.checks -eq "dev_harness=ok,cbo_core=ok,avatar_web=ok,telemetry_gateway=ok") -and (($freshSnap.heartbeat.services.PSObject.Properties.Value | Where-Object { $_.status -ne "ok" }).Count -eq 0)
    Add-ValidationResult -Results $results -Name "immediate_post_refresh_alignment" -Passed ($sameHeartbeat -and $sameExpiry -and $freshAligned -and $checksAligned) -Detail "Governed refresh produced aligned fresh surfaces and no contradiction with live probes."

    $expiryUtc = Convert-ToUtcOffset -Value ([string]$freshSnap.heartbeat.expires_ts_utc)
    $deadlineUtc = $expiryUtc.AddSeconds(45)
    $staleSnap = Wait-ForDerivedStale -DeadlineUtc $deadlineUtc
    $staleObservedUtc = Get-UtcNowOffset
    Add-ValidationResult -Results $results -Name "controlled_pause_self_demotion" -Passed ($null -ne $staleSnap) -Detail "Derived surfaces self-demoted after TTL expiry without manual refresh."

    $staleChecksRemain = ($staleSnap.checks -eq "dev_harness=ok,cbo_core=ok,avatar_web=ok,telemetry_gateway=ok")
    $staleCanonical = ($staleSnap.state.runtime_truth_canonical -match "^live_probes")
    Add-ValidationResult -Results $results -Name "stale_label_consistency" -Passed (($staleSnap.heartbeat.authoritative_for_liveness -eq $false) -and ($staleSnap.snapshot.authoritative_for_liveness -eq $false) -and $staleCanonical -and $staleChecksRemain) -Detail "Stale surfaces stayed internally consistent and probe-canonical."

    Start-Sleep -Seconds 8
    $stillStaleSnap = Get-CurrentSnapshot
    $stillStale = ($stillStaleSnap.state.runtime_truth_state -eq "stale") -and ($stillStaleSnap.heartbeat.truth_state -eq "stale") -and ($stillStaleSnap.snapshot.truth_state -eq "stale") -and ($stillStaleSnap.topology.truth_state -eq "stale")
    Add-ValidationResult -Results $results -Name "stale_monotonicity" -Passed $stillStale -Detail "Stale surfaces did not return to fresh passively."

    $probeWhileStale = ($stillStaleSnap.checks -eq "dev_harness=ok,cbo_core=ok,avatar_web=ok,telemetry_gateway=ok")
    Add-ValidationResult -Results $results -Name "probe_canonicality_unchanged" -Passed $probeWhileStale -Detail "Live probes remained canonical and unchanged while derived surfaces were stale."

    & $updateScript | Out-Null
    $restoredSnap = Get-CurrentSnapshot
    $newHeartbeat = $restoredSnap.heartbeat.heartbeat_emitted_ts -ne $freshSnap.heartbeat.heartbeat_emitted_ts
    $restoredFresh = ($restoredSnap.state.runtime_truth_state -eq "fresh") -and ($restoredSnap.heartbeat.truth_state -eq "fresh") -and ($restoredSnap.snapshot.truth_state -eq "fresh") -and ($restoredSnap.topology.truth_state -eq "fresh")
    Add-ValidationResult -Results $results -Name "fresh_requires_governed_refresh" -Passed ($newHeartbeat -and $restoredFresh) -Detail "Fresh state returned only after a governed refresh with a new heartbeat timestamp."

    $transitionReceipts = @(Get-NewTransitionReceipts -SinceUtc $scriptStartUtc)
    $demotionReceipts = @($transitionReceipts | Where-Object { $_.receipt.transition -eq "fresh_to_stale" -and $_.receipt.reason -eq "ttl_expired" })
    $restoreReceipts = @($transitionReceipts | Where-Object { $_.ts_utc -ge $staleObservedUtc -and $_.receipt.transition -eq "stale_to_fresh" -and $_.receipt.reason -eq "governed_refresh" })

    $demotionFieldsValid = $false
    if ($demotionReceipts.Count -eq 1) {
        $surfaceTransitions = @($demotionReceipts[0].receipt.surface_transitions)
        $requiredSurfaces = @("STATE.md", "station_heartbeat.json", "service_runtime_snapshot.json", "runtime_topology_snapshot.json")
        $surfacesSeen = @($surfaceTransitions | ForEach-Object { $_.surface })
        $demotionFieldsValid = ($requiredSurfaces | Where-Object { $_ -notin $surfacesSeen }).Count -eq 0
        foreach ($transition in $surfaceTransitions) {
            if (-not $transition.surface -or -not $transition.prior_state -or -not $transition.new_state -or -not $transition.emitted_ts_utc -or -not $transition.expiry_ts_utc -or -not $transition.observed_demotion_ts_utc -or $transition.reason -ne "ttl_expired") {
                $demotionFieldsValid = $false
                break
            }
        }
    }
    Add-ValidationResult -Results $results -Name "transition_receipt_discipline" -Passed ($demotionFieldsValid -and $restoreReceipts.Count -ge 1) -Detail "Automatic demotion and governed restore emitted bounded transition receipts with the required fields."

    $receiptPayload = [ordered]@{
        schema = "station.derived_truth_self_demotion_validation.v1"
        ts_utc = Get-UtcNowString
        results = $results
        transition_receipts = @{
            demotion_paths = @($demotionReceipts | ForEach-Object { $_.path })
            restore_paths = @($restoreReceipts | ForEach-Object { $_.path })
        }
    }
    $receiptPath = Write-RuntimeTruthReceipt -RepoRoot $repoRoot -RelativeDir "runtime\receipts\audit" -Prefix "wo_derived_truth_self_demotion_validation" -Payload $receiptPayload
    Write-Host "Validation receipt: $receiptPath"
} catch {
    $failurePayload = [ordered]@{
        schema = "station.derived_truth_self_demotion_validation.v1"
        ts_utc = Get-UtcNowString
        results = $results
        error = $_.Exception.Message
    }
    $receiptPath = Write-RuntimeTruthReceipt -RepoRoot $repoRoot -RelativeDir "runtime\receipts\audit" -Prefix "wo_derived_truth_self_demotion_validation" -Payload $failurePayload
    Write-Host "Validation receipt: $receiptPath"
    throw
}
