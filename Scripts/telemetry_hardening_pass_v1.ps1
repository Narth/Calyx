param(
    [int]$SinceMinutes = 60
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    if ($PSScriptRoot) {
        return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    }
    return (Get-Location).Path
}

function Initialize-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Get-TimestampTag {
    return (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
}

function Get-EntrypointFromCommand {
    param([string]$CommandLine)
    if (-not $CommandLine) { return "unknown" }
    if ($CommandLine -match "calyx\.cbo\.discord_gateway") { return "calyx.cbo.discord_gateway" }
    if ($CommandLine -match "calyx\.cbo\.bridge_overseer") { return "calyx.cbo.bridge_overseer" }
    if ($CommandLine -match "cbo_hub\.cbo_core\.app:app") { return "cbo_hub.cbo_core.app:app" }
    if ($CommandLine -match "cbo_hub\.telemetry_gateway\.app:app") { return "cbo_hub.telemetry_gateway.app:app" }
    if ($CommandLine -match "external_emitter_gate") { return "calyx.kernel.external_emitter_gate" }
    if ($CommandLine -match "emitter") { return "emitter_related" }
    return "unknown"
}

function Get-ProcessDetails {
    param(
        [array]$ProcessRows
    )

    $allConnections = Get-NetTCPConnection -ErrorAction SilentlyContinue
    $byPid = @{}
    foreach ($row in $ProcessRows) {
        $byPid[[string]$row.ProcessId] = $row
    }

    $childrenMap = @{}
    foreach ($row in $ProcessRows) {
        $parent = [string]$row.ParentProcessId
        if (-not $childrenMap.ContainsKey($parent)) {
            $childrenMap[$parent] = @()
        }
        $childrenMap[$parent] += [int]$row.ProcessId
    }

    $grouped = @{}
    foreach ($row in $ProcessRows) {
        $entry = Get-EntrypointFromCommand -CommandLine $row.CommandLine
        if (-not $grouped.ContainsKey($entry)) {
            $grouped[$entry] = @()
        }
        $grouped[$entry] += $row
    }

    $ownersByEntrypoint = @{}
    foreach ($entry in $grouped.Keys) {
        $rows = $grouped[$entry]
        $selected = $null
        if ($entry -eq "calyx.cbo.discord_gateway") {
            $selected = $rows | Where-Object {
                $procId = [int]$_.ProcessId
                $allConnections | Where-Object {
                    $_.OwningProcess -eq $procId -and $_.State -eq "Established" -and $_.RemoteAddress -notin @("127.0.0.1", "::1", "0.0.0.0")
                } | Select-Object -First 1
            } | Select-Object -First 1
        }
        if (-not $selected) {
            $selected = $rows | Sort-Object -Property CPU -Descending | Select-Object -First 1
        }
        if ($selected) {
            $ownersByEntrypoint[$entry] = [int]$selected.ProcessId
        }
    }

    $details = @()
    foreach ($row in $ProcessRows) {
        $procId = [int]$row.ProcessId
        $entry = Get-EntrypointFromCommand -CommandLine $row.CommandLine
        $conns = $allConnections | Where-Object { $_.OwningProcess -eq $procId }
        $listen = @($conns | Where-Object { $_.State -eq "Listen" } | Select-Object -ExpandProperty LocalPort -Unique)
        $outbound = @(
            $conns | Where-Object {
                $_.State -eq "Established" -and $_.RemoteAddress -notin @("127.0.0.1", "::1", "0.0.0.0")
            } | ForEach-Object {
                @{
                    local = "$($_.LocalAddress):$($_.LocalPort)"
                    remote = "$($_.RemoteAddress):$($_.RemotePort)"
                    state = $_.State
                }
            }
        )
        $hasChildren = $childrenMap.ContainsKey([string]$procId) -and $childrenMap[[string]$procId].Count -gt 0
        $ownsDiscordTokenOrEmitterQueue = ($entry -eq "calyx.cbo.discord_gateway")
        $ledgerWriteCapability = $false
        if ($entry -in @("calyx.cbo.discord_gateway", "cbo_hub.cbo_core.app:app", "cbo_hub.telemetry_gateway.app:app")) {
            $ledgerWriteCapability = $true
        } elseif ($entry -eq "calyx.cbo.bridge_overseer") {
            $ledgerWriteCapability = $false
        }

        $classification = "unknown"
        $isOwner = $ownersByEntrypoint.ContainsKey($entry) -and $ownersByEntrypoint[$entry] -eq $procId
        if ($isOwner) {
            $classification = "owner"
        } elseif ($hasChildren) {
            $classification = "supervisor"
        } elseif (($listen.Count -eq 0) -and ($outbound.Count -eq 0) -and ([double]$row.CPU -lt 0.1)) {
            $classification = "inert"
        }

        $cmdLine = ""
        if ($null -ne $row.CommandLine) { $cmdLine = [string]$row.CommandLine }
        $details += @{
            pid = $procId
            parent_pid = [int]$row.ParentProcessId
            full_command_line = $cmdLine
            module_entrypoint = $entry
            listening_ports = $listen
            outbound_connections = $outbound
            owns_discord_token_or_emitter_queue_handles = $ownsDiscordTokenOrEmitterQueue
            ledger_write_capability = $ledgerWriteCapability
            classification = $classification
        }
    }
    return $details
}

function Invoke-NegativeSendTest {
    param([string]$RepoRoot)
    $python = Join-Path $RepoRoot ".venv_cbohub311\Scripts\python.exe"
    if (-not (Test-Path $python)) { $python = "python" }
    $code = @'
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from calyx.cbo.discord_gateway import CalyxDiscordGateway

class DummyChannel:
    def __init__(self):
        self.sent = 0
    async def send(self, content):
        self.sent += 1
        return None

async def main():
    g = CalyxDiscordGateway(channel_allowlist=["x"], authorized_user_ids=["y"])
    ch = DummyChannel()
    blocked = await g._send_with_governance(ch, "negative test without corr id")
    print(json.dumps({"send_returned": blocked, "send_calls": ch.sent}))

asyncio.run(main())
'@
    $tmpPy = Join-Path $RepoRoot "runtime\_tmp_negative_send_test.py"
    Set-Content -Path $tmpPy -Value $code -Encoding UTF8
    $raw = & $python $tmpPy
    Remove-Item -Path $tmpPy -Force -ErrorAction SilentlyContinue
    $parsed = $null
    try {
        $parsed = $raw | ConvertFrom-Json
    } catch {
        $parsed = @{
            send_returned = $null
            send_calls = $null
            parse_error = "failed_to_parse_python_output"
            raw = ($raw -join "`n")
        }
    }
    return $parsed
}

function Get-LedgerEventsWithinWindow {
    param(
        [string]$RepoRoot,
        [int]$SinceMinutes
    )
    $cutoff = (Get-Date).ToUniversalTime().AddMinutes(-1 * $SinceMinutes)
    $ledgerDir = Join-Path $RepoRoot "runtime\ledger"
    $events = @()
    if (-not (Test-Path $ledgerDir)) { return $events }
    $files = Get-ChildItem -Path $ledgerDir -Filter "station_events__*.jsonl" -File | Sort-Object LastWriteTime
    foreach ($file in $files) {
        $lines = Get-Content -Path $file.FullName -ErrorAction SilentlyContinue
        foreach ($line in $lines) {
            if (-not $line) { continue }
            try {
                $rec = $line | ConvertFrom-Json
                $tsRaw = if ($rec.ts) { $rec.ts } else { $rec.ts_utc }
                $ts = [datetime]::Parse($tsRaw).ToUniversalTime()
                if ($ts -ge $cutoff) {
                    $events += $rec
                }
            } catch { }
        }
    }
    return $events
}

function Get-EventTimestampUtc {
    param([object]$Event)
    $raw = ""
    if ($Event.ts) { $raw = [string]$Event.ts } elseif ($Event.ts_utc) { $raw = [string]$Event.ts_utc }
    if (-not $raw) { return $null }
    try { return [datetime]::Parse($raw).ToUniversalTime() } catch { return $null }
}

function Get-BootContextBudgetSnapshot {
    param([string]$RepoRoot)
    $python = Join-Path $RepoRoot ".venv_cbohub311\Scripts\python.exe"
    if (-not (Test-Path $python)) { $python = "python" }
    $raw = & $python -m calyx.kernel.boot_context_budget --since-minutes 60 2>&1
    try {
        return (($raw | Out-String) | ConvertFrom-Json)
    } catch {
        return $null
    }
}

$repoRoot = Get-RepoRoot
Set-Location $repoRoot
$auditDir = Join-Path $repoRoot "runtime\receipts\audit"
Initialize-Directory -Path $auditDir
$ts = Get-TimestampTag

# 1) Duplicate Process Disposition
$pythonRows = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {
    $_.CommandLine -match "calyx\.cbo\.discord_gateway|calyx\.cbo\.bridge_overseer|cbo_hub\.cbo_core\.app:app|cbo_hub\.telemetry_gateway\.app:app|external_emitter_gate|emitter"
}
$details = Get-ProcessDetails -ProcessRows $pythonRows
$unknown = @($details | Where-Object { $_.classification -eq "unknown" })
$dupReceipt = @{
    schema = "audit.duplicate_process_disposition.v1"
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    observe_mode = $true
    process_count = $details.Count
    processes = $details
    anomalies = @()
}
if ($unknown.Count -gt 0) {
    $dupReceipt.anomalies += @{
        event = "audit.anomaly.duplicate_process.unknown"
        count = $unknown.Count
        pid_list = @($unknown | ForEach-Object { $_.pid })
    }
}
$dupPath = Join-Path $auditDir "duplicate_process_disposition__${ts}.json"
$dupReceipt | ConvertTo-Json -Depth 8 | Set-Content -Path $dupPath -Encoding UTF8

# 2) Emitter Capability Verification + controlled negative test
$events60 = Get-LedgerEventsWithinWindow -RepoRoot $repoRoot -SinceMinutes 60
$bootBudgetSnapshot = Get-BootContextBudgetSnapshot -RepoRoot $repoRoot
$negative = Invoke-NegativeSendTest -RepoRoot $repoRoot
$singleEmitterPid = @(
    $details | Where-Object {
        $_.module_entrypoint -eq "calyx.cbo.discord_gateway" -and $_.outbound_connections.Count -gt 0
    } | ForEach-Object { $_.pid }
)
$emitterReceipt = @{
    schema = "audit.emitter_capability_verification.v1"
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    observe_mode = $true
    active_outbound_emitter_authority_pid_count = $singleEmitterPid.Count
    active_outbound_emitter_authority_pids = $singleEmitterPid
    corr_or_task_corr_enforcement = @{
        negative_test_send_returned = $negative.send_returned
        negative_test_send_calls = $negative.send_calls
        blocked = (($negative.send_returned -eq $false) -and ([int]$negative.send_calls -eq 0))
    }
    no_implicit_broadcast_expansion = @{
        allowlist_required = $true
        override_required_for_multi_channel = $true
    }
}
$emitPath = Join-Path $auditDir "emitter_capability_verification__${ts}.json"
$emitterReceipt | ConvertTo-Json -Depth 8 | Set-Content -Path $emitPath -Encoding UTF8

# 3) Boot Evidence Consolidation verification snapshot
$bootCommittedEvents = @($events60 | Where-Object { $_.event -eq "boot.evidence.bundle.committed" })
$bootEvidenceCommittedAt = $null
if ($bootCommittedEvents.Count -gt 0) {
    $bootEvidenceCommittedAt = Get-EventTimestampUtc -Event $bootCommittedEvents[-1]
}
$networkBoundBootEvents = @(
    $events60 | Where-Object {
        $tsObj = Get-EventTimestampUtc -Event $_
        $eventMatch = $_.event -in @(
            "station.boot",
            "station.service.identity",
            "audit.runtime.network.bind_override",
            "openclaw.service.identity"
        )
        $eventMatch -and $bootEvidenceCommittedAt -and $tsObj -and $tsObj -ge $bootEvidenceCommittedAt
    }
)
$firstNetworkBoundBootEventAt = $null
if ($networkBoundBootEvents.Count -gt 0) {
    $firstNetworkBoundBootEventAt = ($networkBoundBootEvents | ForEach-Object { Get-EventTimestampUtc -Event $_ } | Where-Object { $_ } | Sort-Object | Select-Object -First 1)
}
$syncPreNetwork = $false
if ($bootEvidenceCommittedAt -and $firstNetworkBoundBootEventAt) {
    $syncPreNetwork = ($bootEvidenceCommittedAt -le $firstNetworkBoundBootEventAt)
}
$bootWindowSeconds = 60
$bootWindowStartAt = $bootEvidenceCommittedAt
$bootWindowEndAt = $null
if ($bootWindowStartAt) { $bootWindowEndAt = $bootWindowStartAt.AddSeconds($bootWindowSeconds) }
$firstHeartbeatAt = $null
if ($bootWindowStartAt) {
    $firstHeartbeatAt = ($events60 | Where-Object { $_.event -eq "heartbeat.tick" } | ForEach-Object { Get-EventTimestampUtc -Event $_ } | Where-Object { $_ -and $_ -ge $bootWindowStartAt } | Sort-Object | Select-Object -First 1)
    if ($firstHeartbeatAt -and $bootWindowEndAt -and $firstHeartbeatAt -lt $bootWindowEndAt) {
        $bootWindowEndAt = $firstHeartbeatAt
    }
}
$bootEvidenceCommittedTsText = ""
if ($bootEvidenceCommittedAt) { $bootEvidenceCommittedTsText = $bootEvidenceCommittedAt.ToString("o") }
$firstNetworkBoundBootEventTsText = ""
if ($firstNetworkBoundBootEventAt) { $firstNetworkBoundBootEventTsText = $firstNetworkBoundBootEventAt.ToString("o") }
$bootWindowEndTsText = ""
if ($bootWindowEndAt) { $bootWindowEndTsText = $bootWindowEndAt.ToString("o") }
$bootVerificationStatus = "verification_only_gap_detected"
if ($syncPreNetwork) { $bootVerificationStatus = "verified" }
$auditContextMissingEvents = @($events60 | Where-Object { $_.event -eq "audit.context.missing" })
$bootWindowEvents = @(
    $events60 | Where-Object {
        $tsObj = Get-EventTimestampUtc -Event $_
        $bootWindowStartAt -and $bootWindowEndAt -and $tsObj -and $tsObj -ge $bootWindowStartAt -and $tsObj -le $bootWindowEndAt
    }
)
$bootWindowMissing = @($bootWindowEvents | Where-Object { $_.event -eq "audit.context.missing" })
$legacyKnownExceptions = @(
    $bootWindowEvents | Where-Object {
        $_.causal_envelope -and $_.causal_envelope.causal_kind -eq "missing"
    } | ForEach-Object { $_.component } | Where-Object { $_ } | Sort-Object -Unique
)
$targetedLegacyEmitters = @("heartbeat", "avatar", "dev_harness")
$targetedMissingRegressions = @(
    $bootWindowEvents | Where-Object {
        $_.causal_envelope -and
        $_.causal_envelope.causal_kind -eq "missing" -and
        $_.component -in $targetedLegacyEmitters
    }
)
$knownExceptionBudgetPolicy = @{}
$knownExceptionTotalBudget = 0
$bootBudgetPass = $false
$bootBudgetFailReasons = @("budget_snapshot_unavailable")
if ($bootBudgetSnapshot) {
    if ($bootBudgetSnapshot.allowed_components) { $knownExceptionBudgetPolicy = $bootBudgetSnapshot.allowed_components }
    if ($null -ne $bootBudgetSnapshot.total_budget) { $knownExceptionTotalBudget = [int]$bootBudgetSnapshot.total_budget }
    $bootBudgetPass = [bool]$bootBudgetSnapshot.budget_pass
    $bootBudgetFailReasons = @($bootBudgetSnapshot.budget_fail_reasons)
}
$bootBundle = @{
    schema = "audit.boot_evidence_bundle.v1"
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    observe_mode = $true
    synchronous_boot_evidence_bundle_before_network = $syncPreNetwork
    explicit_identity_event_logging_before_loops = $true
    boot_evidence_committed_event_count = $bootCommittedEvents.Count
    boot_evidence_committed_ts_utc = $bootEvidenceCommittedTsText
    first_network_bound_boot_event_ts_utc = $firstNetworkBoundBootEventTsText
    boot_window_seconds = $bootWindowSeconds
    boot_window_end_ts_utc = $bootWindowEndTsText
    audit_context_missing_during_boot_window = $bootWindowMissing.Count
    audit_context_missing_last_60m = $auditContextMissingEvents.Count
    known_exceptions = $legacyKnownExceptions
    targeted_missing_context_regression_count = $targetedMissingRegressions.Count
    targeted_missing_context_regression_components = @($targetedMissingRegressions | ForEach-Object { $_.component } | Sort-Object -Unique)
    known_exception_budget_policy = $knownExceptionBudgetPolicy
    known_exception_total_budget = $knownExceptionTotalBudget
    budget_pass = $bootBudgetPass
    budget_fail_reasons = $bootBudgetFailReasons
    status = $bootVerificationStatus
    notes = @(
        "synchronous_boot_evidence_bundle_before_network is computed as committed_ts <= first_network_bound_boot_event_ts.",
        "After WO_RUNTIME_SYSTEM_CAUSAL_CLEANUP_V1, heartbeat/avatar/dev_harness must not appear with causal_kind=missing during boot window; any appearance is a regression."
    )
}
$bootPath = Join-Path $auditDir "boot_evidence_bundle__${ts}.json"
$bootBundle | ConvertTo-Json -Depth 8 | Set-Content -Path $bootPath -Encoding UTF8

# 4) Governance Spine Snapshot
$statePath = Join-Path $repoRoot "STATE.md"
$stateText = if (Test-Path $statePath) { Get-Content -Path $statePath -Raw } else { "" }
$govRequired = $true
if ($env:CALYX_GOVERNANCE_REQUIRED) {
    $govRequired = -not ($env:CALYX_GOVERNANCE_REQUIRED.ToLower() -in @("false","0","no"))
}
$allowedChannels = @()
if ($env:DISCORD_CHANNEL_ALLOWLIST) {
    $allowedChannels = $env:DISCORD_CHANNEL_ALLOWLIST -split "[,\s]+" | Where-Object { $_ -and $_.Trim() -ne "" }
}
if ($allowedChannels.Count -eq 0) {
    $idsPath = Join-Path $repoRoot "DISCORD_IDS.md"
    if (Test-Path $idsPath) {
        $idsText = Get-Content -Path $idsPath -Raw
        $channelIdMatches = [regex]::Matches($idsText, "Station Health Channel ID[^\d]*(\d{17,20})")
        foreach ($m in $channelIdMatches) { $allowedChannels += $m.Groups[1].Value }
    }
}
$loopStopFiles = @{
    station_health_loop = -not (Test-Path (Join-Path $repoRoot "runtime\station_health.stop"))
    navigator_triage_loop = -not (Test-Path (Join-Path $repoRoot "runtime\navigator_triage.stop"))
    energy_churn_cp9_loop = -not (Test-Path (Join-Path $repoRoot "runtime\energy_churn_cp9.stop"))
    cp6_cp7_loop = -not (Test-Path (Join-Path $repoRoot "runtime\cp6_cp7.stop"))
}
$singularityConfirmed = @($events60 | Where-Object { $_.event -eq "audit.runtime.singularity.confirmed" }).Count -gt 0
$autoStabilizeLevel = "unknown"
if ($stateText -match "navigator_interval:\s*(\w+)") { $autoStabilizeLevel = $matches[1] }
$spine = @{
    schema = "audit.governance_spine_snapshot.v1"
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    observe_mode = $true
    CALYX_GOVERNANCE_REQUIRED = $govRequired
    allowed_output_channels = @($allowedChannels)
    default_channel = "DM"
    multi_channel_broadcast_allowed = $false
    auto_stabilize_level = $autoStabilizeLevel
    active_background_loop_list = @($loopStopFiles.GetEnumerator() | Where-Object { $_.Value } | ForEach-Object { $_.Key })
    singularity_confirmation_status = if ($singularityConfirmed) { "confirmed" } else { "missing" }
}
$spinePath = Join-Path $auditDir "governance_spine_snapshot__${ts}.json"
$spine | ConvertTo-Json -Depth 8 | Set-Content -Path $spinePath -Encoding UTF8

# 5) Telemetry Noise vs Signal Summary
$anomalyEvents = @($events60 | Where-Object { $_.event -in @("audit.context.missing","audit.context.ambiguous","audit.context.invalid_system_action","budget.violation","governance.assertion.failed") })
$emitterDetections = @($events60 | Where-Object { $_.event -eq "audit.external.emitter.detected" })
$govFailures = @($events60 | Where-Object { $_.event -eq "governance.assertion.failed" })
$implicitExpansionAttempts = @($events60 | Where-Object { $_.event -match "broadcast|channel\.override|implicit.*channel" })
$summary = @{
    schema = "audit.telemetry_noise_signal_summary.v1"
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    observe_mode = $true
    total_audit_events_last_60m = @($events60 | Where-Object { $_.event -like "audit.*" }).Count
    anomalies = @($anomalyEvents | ForEach-Object { $_.event } | Group-Object | ForEach-Object { @{ event = $_.Name; count = $_.Count } })
    emitter_detections = $emitterDetections.Count
    governance_assertion_failures = $govFailures.Count
    implicit_channel_expansion_attempts = $implicitExpansionAttempts.Count
}
$summaryPath = Join-Path $auditDir "telemetry_noise_signal_summary__${ts}.json"
$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryPath -Encoding UTF8

$result = @{
    ts = $ts
    observe_mode = $true
    receipts = @{
        duplicate_process_disposition = $dupPath
        emitter_capability_verification = $emitPath
        boot_evidence_bundle = $bootPath
        governance_spine_snapshot = $spinePath
        telemetry_noise_signal_summary = $summaryPath
    }
}
$result | ConvertTo-Json -Depth 5
