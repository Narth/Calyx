# Update STATE.md with live checks, heartbeat_ts, health, navigator_interval, triage_status.
# Test/assessment metrics include CBO (cbo_core). See check_calyx_core_services.ps1.
# Usage: .\Scripts\update_state_checks.ps1 [-ForceStale] [-StaleReason text]
# Runs check_calyx_core_services.ps1, reads runtime/station_health.json, outgoing/navigator.lock, outgoing/triage.lock:
#   checks, heartbeat_ts, health, health_ts, entropy_tier, navigator_interval, triage_status

param(
    [switch]$ForceStale = $false,
    [string]$StaleReason = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\STATE.md")) {
    $repoRoot = (Get-Location).Path
}
Set-Location $repoRoot

$truthHelper = Join-Path $repoRoot "Scripts\runtime_truth_contract.ps1"
if (-not (Test-Path $truthHelper)) {
    Write-Error "Runtime truth helper not found: $truthHelper"
}
. $truthHelper

$statePath = Join-Path $repoRoot "STATE.md"
$checkScript = Join-Path $repoRoot "Scripts\check_calyx_core_services.ps1"
$topologyScript = Join-Path $repoRoot "Scripts\runtime_topology_snapshot.py"
$signalScript = Join-Path $repoRoot "tools\signal_examiner.py"
$topologySnapshotPath = Join-Path $repoRoot "runtime\runtime_topology_snapshot.json"
$signalDigestPath = Join-Path $repoRoot "runtime\signals\current_signal_digest.json"
$venvPython = Join-Path $repoRoot ".venv_cbohub311\Scripts\python.exe"
$pythonRuntime = if (Test-Path $venvPython) { $venvPython } else { "python" }
$healthPath = Join-Path $repoRoot "runtime\station_health.json"
$serviceFailureStatusPath = Join-Path $repoRoot "runtime\service_failure_status.json"
if ($ForceStale -and [string]::IsNullOrWhiteSpace($StaleReason)) {
    $StaleReason = "stale_override"
}
if (-not (Test-Path $checkScript)) {
    Write-Error "Check script not found: $checkScript"
}
if (-not (Test-Path $statePath)) {
    Write-Error "STATE.md not found: $statePath. Create STATE.md before running update_state_checks."
}

function Get-Sha256Hex {
    param([string]$Text)
    try {
        $sha = [System.Security.Cryptography.SHA256]::Create()
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        $hash = $sha.ComputeHash($bytes)
        return ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
    } catch {
        return ""
    }
}

function Get-LatestStationBootTsFromLedger {
    param([string]$RepoRoot)
    try {
        $ledgerDir = Join-Path $RepoRoot "runtime\ledger"
        if (-not (Test-Path $ledgerDir)) { return "" }
        $file = Get-ChildItem -Path $ledgerDir -Filter "station_events__*.jsonl" -File |
            Sort-Object LastWriteTime | Select-Object -Last 1
        if (-not $file) { return "" }
        $lines = Get-Content -Path $file.FullName -Tail 2000 -ErrorAction SilentlyContinue
        $latest = $null
        foreach ($line in $lines) {
            if (-not $line) { continue }
            try {
                $rec = $line | ConvertFrom-Json
                if ($rec.event -ne "station.boot") { continue }
                $raw = if ($rec.ts_utc) { $rec.ts_utc } else { $rec.ts }
                if (-not $raw) { continue }
                $ts = [datetime]::Parse($raw).ToUniversalTime()
                if (-not $latest -or $ts -gt $latest) { $latest = $ts }
            } catch { }
        }
        if ($latest) { return $latest.ToString("o") }
        return ""
    } catch {
        return ""
    }
}

function Get-StationBootInfo {
    param([string]$RepoRoot)
    $markerPath = Join-Path $RepoRoot "runtime\boot_evidence_marker.json"
    $hostBootPath = Join-Path $RepoRoot "runtime\host_boot_detected.json"
    $bootTs = ""
    $bootSessionId = ""
    $hostBootTs = ""
    $hostBootClassification = ""
    if (Test-Path $markerPath) {
        try {
            $marker = Get-Content -Path $markerPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($marker.ts_utc) { $bootTs = $marker.ts_utc }
            if ($marker.boot_session_id) { $bootSessionId = $marker.boot_session_id }
        } catch { }
    }
    if (Test-Path $hostBootPath) {
        try {
            $hostBoot = Get-Content -Path $hostBootPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($hostBoot.os_boot_ts_utc) { $hostBootTs = [string]$hostBoot.os_boot_ts_utc }
            if ($hostBoot.classification) { $hostBootClassification = [string]$hostBoot.classification }
        } catch { }
    }
    if (-not $bootTs) {
        $bootTs = Get-LatestStationBootTsFromLedger -RepoRoot $RepoRoot
    }
    if (-not $bootTs) { $bootTs = "unknown" }
    return @{
        station_boot_ts = $bootTs
        boot_session_id = $bootSessionId
        host_boot_ts = $hostBootTs
        host_boot_classification = $hostBootClassification
    }
}

function Get-MemoryPressureTier {
    param([Nullable[int]]$RamPct, [bool]$OomImminent)
    if ($OomImminent) { return 4 }
    if ($null -eq $RamPct) { return $null }
    if ($RamPct -lt 70) { return 0 }
    elseif ($RamPct -lt 85) { return 1 }
    elseif ($RamPct -le 95) { return 2 }
    else { return 3 }
}

function Get-ServiceFailureOverlay {
    param([string]$StatusPath)
    $overlay = [ordered]@{
        active_count = 0
        change_lane = "clear"
        risk_lane = "clear"
        services = @()
        current_liveness_authority = $false
    }
    if (-not (Test-Path -LiteralPath $StatusPath -PathType Leaf)) {
        return $overlay
    }
    try {
        $status = Get-Content -LiteralPath $StatusPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($status.summary) {
            if ($null -ne $status.summary.active_count) { $overlay.active_count = [int]$status.summary.active_count }
            if ($status.summary.failure_change_lane) { $overlay.change_lane = [string]$status.summary.failure_change_lane }
            if ($status.summary.failure_risk_lane) { $overlay.risk_lane = [string]$status.summary.failure_risk_lane }
            if ($status.summary.services) {
                $overlay.services = @($status.summary.services | ForEach-Object { [string]$_ })
            }
        }
    } catch { }
    return $overlay
}

function Limit-Text {
    param(
        [string]$Text,
        [int]$Max = 180
    )
    if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
    $normalized = ($Text -replace "\s+", " ").Trim()
    if ($normalized.Length -le $Max) { return $normalized }
    return ($normalized.Substring(0, [math]::Max(0, $Max - 3)) + "...")
}

function Get-ClarityRuntimeStatus {
    param([string]$RepoRoot)
    $requiredClasses = @("safe_to_infer", "needs_receipt", "needs_operator_confirmation", "deny_until_clear")
    $activeObjectivePath = Join-Path $RepoRoot "runtime\active_objective.json"
    $sourceRegistryPath = Join-Path $RepoRoot "docs\canonical\CALYX_SOURCE_AUTHORITY_REGISTRY.json"
    $confusionProtocolPath = Join-Path $RepoRoot "docs\canonical\CALYX_CONFUSION_ESCALATION_PROTOCOL.md"
    $decisionLedgerPath = Join-Path $RepoRoot "docs\canonical\CALYX_DECISION_LEDGER.md"
    $errors = @()
    $warnings = @()
    $activeObjective = $null
    $sourceRegistry = $null
    $rootStatuses = @()

    if (Test-Path -LiteralPath $activeObjectivePath -PathType Leaf) {
        try {
            $activeObjective = Get-Content -LiteralPath $activeObjectivePath -Raw -Encoding UTF8 | ConvertFrom-Json
        } catch {
            $errors += "active_objective_invalid_json"
        }
    } else {
        $errors += "active_objective_missing"
    }

    if (Test-Path -LiteralPath $sourceRegistryPath -PathType Leaf) {
        try {
            $sourceRegistry = Get-Content -LiteralPath $sourceRegistryPath -Raw -Encoding UTF8 | ConvertFrom-Json
        } catch {
            $errors += "source_authority_registry_invalid_json"
        }
    } else {
        $errors += "source_authority_registry_missing"
    }

    if (-not (Test-Path -LiteralPath $confusionProtocolPath -PathType Leaf)) {
        $errors += "confusion_protocol_missing"
    }
    if (-not (Test-Path -LiteralPath $decisionLedgerPath -PathType Leaf)) {
        $errors += "decision_ledger_missing"
    }

    $objectiveStatus = "missing"
    $objectiveSummary = ""
    $confusionPolicy = "missing"
    if ($activeObjective) {
        $objectiveStatus = if ($activeObjective.status) { [string]$activeObjective.status } else { "unknown" }
        $objectiveSummary = Limit-Text -Text ([string]$activeObjective.objective) -Max 180
        try {
            $classes = @($activeObjective.confusion_policy.classifications | ForEach-Object { [string]$_ })
            foreach ($required in $requiredClasses) {
                if ($required -notin $classes) { $errors += "confusion_class_missing:$required" }
            }
            $defaultPolicy = if ($activeObjective.confusion_policy.default) { [string]$activeObjective.confusion_policy.default } else { "unknown" }
            $confusionPolicy = "{0}: {1}" -f $defaultPolicy, ($classes -join ",")
        } catch {
            $errors += "confusion_policy_invalid"
            $confusionPolicy = "invalid"
        }
    }

    $sourceRegistryStatus = "missing"
    if ($sourceRegistry) {
        $roots = @($sourceRegistry.roots)
        foreach ($root in $roots) {
            $pathValue = [string]$root.path
            $exists = if ($pathValue) { Test-Path -LiteralPath $pathValue } else { $false }
            if ($root.exists_required -eq $true -and -not $exists) {
                $errors += "required_source_root_missing:$($root.id)"
            }
            $rootStatuses += [ordered]@{
                id = [string]$root.id
                path = $pathValue
                authority_class = [string]$root.authority_class
                exists_required = [bool]$root.exists_required
                exists = [bool]$exists
            }
        }
        $sourceRegistryStatus = if ($errors | Where-Object { $_ -like "required_source_root_missing:*" }) { "invalid($($roots.Count) roots)" } else { "valid($($roots.Count) roots)" }
        if ($sourceRegistry.global_boundaries -and $sourceRegistry.global_boundaries.canonical_runtime_truth_by_presence_alone -ne $false) {
            $warnings += "registry_boundary_runtime_truth_by_presence_not_false"
        }
    }

    $status = if ($errors.Count -eq 0) { "pass" } else { "fail" }
    return [ordered]@{
        schema = "station.clarity_status.v1"
        authority_status = "canonical support"
        authority_note = "Clarity status validates active objective, source authority registry, confusion protocol, and decision ledger; it is support truth, not sole runtime authority."
        emitted_ts_utc = ([datetime]::UtcNow).ToString("o")
        status = $status
        active_objective_status = $objectiveStatus
        active_objective_summary = $objectiveSummary
        confusion_policy = $confusionPolicy
        source_authority_registry = $sourceRegistryStatus
        active_objective_path = "runtime/active_objective.json"
        source_authority_registry_path = "docs/canonical/CALYX_SOURCE_AUTHORITY_REGISTRY.json"
        confusion_protocol_path = "docs/canonical/CALYX_CONFUSION_ESCALATION_PROTOCOL.md"
        decision_ledger_path = "docs/canonical/CALYX_DECISION_LEDGER.md"
        roots = $rootStatuses
        errors = $errors
        warnings = $warnings
    }
}

function Get-ServiceInfo {
    param([int]$Port)
    $info = [ordered]@{
        pid = $null
        uptime_s = $null
        rss_mb = $null
        status = "fail"
        start_ts = ""
    }
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" -or $_.State -eq 2 } | Select-Object -First 1
        if ($conn -and $conn.OwningProcess) {
            $owningPid = [int]$conn.OwningProcess
            $info.pid = $owningPid
            $info.status = "ok"
            try {
                $proc = Get-Process -Id $owningPid -ErrorAction SilentlyContinue
                if ($proc) {
                    $info.rss_mb = [math]::Round($proc.WorkingSet64 / 1MB, 2)
                    $info.uptime_s = [math]::Round((New-TimeSpan -Start $proc.StartTime -End (Get-Date)).TotalSeconds, 0)
                    $info.start_ts = $proc.StartTime.ToUniversalTime().ToString("o")
                }
            } catch { }
        }
    } catch { }
    if (-not $info.pid) {
        try {
            $lines = & netstat -ano -p TCP 2>$null | Select-String "LISTENING"
            foreach ($l in $lines) {
                $line = if ($l -and $l.Line) { $l.Line } else { [string]$l }
                $parts = ($line -split "\s+") | Where-Object { $_ -ne "" }
                if ($parts.Count -lt 5) { continue }
                $local = $parts[1]
                if ($local -match ":$Port$") {
                    $owningPid = [int]$parts[4]
                    $info.pid = $owningPid
                    $info.status = "ok"
                    try {
                        $proc = Get-Process -Id $owningPid -ErrorAction SilentlyContinue
                        if ($proc) {
                            $info.rss_mb = [math]::Round($proc.WorkingSet64 / 1MB, 2)
                            $info.uptime_s = [math]::Round((New-TimeSpan -Start $proc.StartTime -End (Get-Date)).TotalSeconds, 0)
                            $info.start_ts = $proc.StartTime.ToUniversalTime().ToString("o")
                        }
                    } catch { }
                    break
                }
            }
        } catch { }
    }
    return $info
}

function Get-AuthorityStatusForService {
    param([string]$Name)
    switch ($Name) {
        "dev_harness" { return "canonical core" }
        "cbo_core" { return "canonical core" }
        "avatar_web" { return "canonical core" }
        "telemetry_gateway" { return "canonical support" }
        default { return "unknown" }
    }
}

function Test-HiddenRestartSuspected {
    param(
        [string]$RepoRoot,
        [array]$RestartServices,
        [string]$HeartbeatEmittedTs,
        [int]$WindowSec = 180
    )
    if (-not $RestartServices -or $RestartServices.Count -eq 0) { return $false }
    $serviceToComponent = @{
        dev_harness = "dev_harness"
        cbo_core = "cbo"
        avatar_web = "avatar"
        telemetry_gateway = "telemetry"
    }
    $evidence = @{}
    foreach ($s in $RestartServices) { $evidence[$s] = $false }
    try {
        $ledgerDir = Join-Path $RepoRoot "runtime\ledger"
        if (-not (Test-Path $ledgerDir)) { return $true }
        $file = Get-ChildItem -Path $ledgerDir -Filter "station_events__*.jsonl" -File |
            Sort-Object LastWriteTime | Select-Object -Last 1
        if (-not $file) { return $true }
        $hbTs = [datetime]::Parse($HeartbeatEmittedTs).ToUniversalTime()
        $lines = Get-Content -Path $file.FullName -Tail 3000 -ErrorAction SilentlyContinue
        foreach ($line in $lines) {
            if (-not $line) { continue }
            try {
                $rec = $line | ConvertFrom-Json
                if (-not ($rec.event -in @("station.boot", "station.service.identity"))) { continue }
                $raw = if ($rec.ts_utc) { $rec.ts_utc } else { $rec.ts }
                if (-not $raw) { continue }
                $ts = [datetime]::Parse($raw).ToUniversalTime()
                if ([math]::Abs(($hbTs - $ts).TotalSeconds) -gt $WindowSec) { continue }
                if ($rec.event -eq "station.service.identity" -and $rec.data -and $rec.data.service) {
                    $svc = [string]$rec.data.service
                    if ($evidence.ContainsKey($svc)) { $evidence[$svc] = $true }
                } elseif ($rec.event -eq "station.boot") {
                    $comp = [string]$rec.component
                    foreach ($s in $RestartServices) {
                        if ($serviceToComponent[$s] -eq $comp) { $evidence[$s] = $true }
                    }
                }
            } catch { }
        }
    } catch { }
    foreach ($s in $RestartServices) {
        if (-not $evidence[$s]) { return $true }
    }
    return $false
}

$recoveryActions = Invoke-RuntimeTruthRecovery -RepoRoot $repoRoot
$priorDerivedObservations = @(Get-DerivedTruthSurfaceObservations -RepoRoot $repoRoot -NowUtc ([datetime]::UtcNow))

$checksOutput = & $checkScript | Select-Object -First 1
$checksOutput = ($checksOutput -replace "^\s+|\s+$", "")
if (-not $checksOutput) { $checksOutput = "dev_harness=fail,cbo_core=fail,avatar_web=fail,telemetry_gateway=fail" }
$allChecksOk = (($checksOutput -split ",") | Where-Object { $_ -match "=fail$" }).Count -eq 0

$heartbeatNowUtc = [datetime]::UtcNow
$heartbeatTs = $heartbeatNowUtc.ToString("o")
$heartbeatEmittedTs = $heartbeatTs
$bootInfo = Get-StationBootInfo -RepoRoot $repoRoot
$stationBootTs = $bootInfo.station_boot_ts
$bootSessionId = $bootInfo.boot_session_id
$hostBootTs = $bootInfo.host_boot_ts
$hostBootClassification = $bootInfo.host_boot_classification

$health = "unknown"
$healthTs = ""
$entropyTier = "unknown"
$ramPct = $null
$oomImminent = $false
$memoryPressureTier = $null
$cpuTarget = "unknown"
$healthFresh = $false
if (Test-Path -LiteralPath $healthPath -PathType Leaf) {
    try {
        $healthJson = Get-Content -LiteralPath $healthPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $healthTruth = Get-ArtifactFreshness -ContractName "station_health" -Artifact $healthJson -Path $healthPath -NowUtc $heartbeatNowUtc
        if ($healthTruth.is_fresh -and -not $ForceStale) {
            $healthFresh = $true
            $health = $healthJson.health
            $healthTs = $healthJson.health_ts
            if ($healthJson.entropy -and $healthJson.entropy.tier) { $entropyTier = $healthJson.entropy.tier }
            if ($healthJson.entropy -and $healthJson.entropy.cpu_target) { $cpuTarget = $healthJson.entropy.cpu_target }
            if ($null -ne $healthJson.ram_pct) { $ramPct = [int]$healthJson.ram_pct }
            if ($null -ne $healthJson.oom_imminent) { $oomImminent = [bool]$healthJson.oom_imminent }
            if ($null -ne $healthJson.memory_pressure_tier) { $memoryPressureTier = [int]$healthJson.memory_pressure_tier }
        } else {
            $healthTs = if ($healthJson.health_ts) { [string]$healthJson.health_ts } else { "" }
        }
    } catch { }
}
if ($null -eq $memoryPressureTier) {
    try {
        if (-not $oomImminent) {
            $oomFlag = $env:CALYX_OOM_IMMINENT
            if ($null -ne $oomFlag) {
                $oomFlag = $oomFlag.ToString().Trim().ToLower()
                if ($oomFlag -in @("1", "true", "yes")) { $oomImminent = $true }
            }
        }
    } catch { }
    $memoryPressureTier = Get-MemoryPressureTier -RamPct $ramPct -OomImminent $oomImminent
}
$serviceFailureOverlay = Get-ServiceFailureOverlay -StatusPath $serviceFailureStatusPath
$failureFlagsActive = [string]$serviceFailureOverlay.active_count
$failureChangeLane = [string]$serviceFailureOverlay.change_lane
$failureRiskLane = [string]$serviceFailureOverlay.risk_lane
$failureFlagServices = (($serviceFailureOverlay.services | Where-Object { $_ }) -join ",")
$clarityStatus = Get-ClarityRuntimeStatus -RepoRoot $repoRoot
$clarityStatusPath = Join-Path $repoRoot "runtime\clarity_status.json"
Write-JsonArtifact -Path $clarityStatusPath -Artifact $clarityStatus

# Navigator + Triage (ship's wheel + medical unit)
$navigatorInterval = "unknown"
$triageStatus = "unknown"
$navLock = Join-Path $repoRoot "outgoing\navigator.lock"
$triageLock = Join-Path $repoRoot "outgoing\triage.lock"
if (-not $ForceStale -and (Test-Path -LiteralPath $navLock -PathType Leaf)) {
    try {
        $navJson = Get-Content -LiteralPath $navLock -Raw -Encoding UTF8 | ConvertFrom-Json
        $navTruth = Get-ArtifactFreshness -ContractName "navigator" -Artifact $navJson -Path $navLock -NowUtc $heartbeatNowUtc
        if ($navTruth.is_fresh -and $navJson.interval_status) { $navigatorInterval = $navJson.interval_status }
    } catch { }
}
if (-not $ForceStale -and (Test-Path -LiteralPath $triageLock -PathType Leaf)) {
    try {
        $triJson = Get-Content -LiteralPath $triageLock -Raw -Encoding UTF8 | ConvertFrom-Json
        $triTruth = Get-ArtifactFreshness -ContractName "triage" -Artifact $triJson -Path $triageLock -NowUtc $heartbeatNowUtc
        if ($triTruth.is_fresh -and $triJson.status) { $triageStatus = $triJson.status }
    } catch { }
}

$stateTruthMetadata = New-TruthMetadata -ContractName "state_runtime" -EmittedAtUtc $heartbeatNowUtc -ForceStale:$ForceStale -StaleReason $StaleReason
$stateRuntimeValues = @{
    heartbeat_ts = $heartbeatTs
    health = if ($ForceStale) { "unknown" } else { $health }
    health_ts = $healthTs
    entropy_tier = if ($ForceStale) { "unknown" } else { $entropyTier }
    navigator_interval = if ($ForceStale) { "unknown" } else { $navigatorInterval }
    triage_status = if ($ForceStale) { "unknown" } else { $triageStatus }
    cpu_target = if ($ForceStale) { "unknown" } else { $cpuTarget }
    runtime_truth_state = $stateTruthMetadata.truth_state
    runtime_truth_expires_ts = $stateTruthMetadata.expires_ts_utc
    runtime_truth_label = if ($ForceStale) { $stateTruthMetadata.stale_label } else { "DERIVED_FRESH" }
    runtime_truth_canonical = if ($ForceStale) { "advisory digest from live_probes ($StaleReason)" } else { "advisory digest from live_probes" }
    state_authority_status = "canonical support"
    state_authority_note = "STATE.md is advisory generated support; not sole authoritative truth"
    active_objective_status = [string]$clarityStatus.active_objective_status
    active_objective_summary = [string]$clarityStatus.active_objective_summary
    confusion_policy = [string]$clarityStatus.confusion_policy
    source_authority_registry = [string]$clarityStatus.source_authority_registry
    checks = $checksOutput
    failure_flags_active = $failureFlagsActive
    failure_change_lane = $failureChangeLane
    failure_risk_lane = $failureRiskLane
    failure_flag_services = $failureFlagServices
    runtime_topology_ts = ""
    runtime_topology_truth_state = if ($ForceStale) { "stale" } else { "unknown" }
    runtime_topology_risk = "unknown"
    runtime_topology_active_services = "none"
    runtime_topology_authority_summary = "none"
    runtime_topology_duplicates = "none"
    runtime_topology_authority_ambiguous = "none"
    runtime_topology_flagged_services = "none"
    signal_level = "unknown"
    signal_top = "unknown"
    signal_count = "0"
    signal_operator_brief = ""
    signal_requires_operator_confirmation = "false"
}
Update-StateRuntimeBlock -StatePath $statePath -Values $stateRuntimeValues

if ($ForceStale) {
    foreach ($artifactInfo in (Get-AdvisoryArtifactTable -RepoRoot $repoRoot)) {
        Set-JsonArtifactStale -Path $artifactInfo.path -ContractName $artifactInfo.contract -Reason $StaleReason | Out-Null
    }
}

# --- Canonical heartbeat artifact + service snapshot ---
$servicePorts = [ordered]@{
    dev_harness = 7777
    cbo_core = 7778
    avatar_web = 7780
    telemetry_gateway = 7781
}
$services = [ordered]@{}
$snapshotServices = [ordered]@{}
foreach ($name in $servicePorts.Keys) {
    $info = Get-ServiceInfo -Port $servicePorts[$name]
    $authorityStatus = Get-AuthorityStatusForService -Name $name
    $services[$name] = [ordered]@{
        pid = $info.pid
        uptime_s = $info.uptime_s
        rss_mb = $info.rss_mb
        status = $info.status
        authority_status = $authorityStatus
    }
    $snapshotServices[$name] = [ordered]@{
        pid = $info.pid
        start_ts = $info.start_ts
        uptime_s = $info.uptime_s
        status = $info.status
        authority_status = $authorityStatus
    }
}

$snapshotPath = Join-Path $repoRoot "runtime\service_runtime_snapshot.json"
$prevSnapshot = $null
if (Test-Path -LiteralPath $snapshotPath -PathType Leaf) {
    try { $prevSnapshot = Get-Content -LiteralPath $snapshotPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $prevSnapshot = $null }
}
$restartServices = @()
if ($prevSnapshot -and $prevSnapshot.services) {
    foreach ($name in $services.Keys) {
        try {
            $prevPid = $prevSnapshot.services.$name.pid
            $currPid = $services[$name].pid
            if ($prevPid -and $currPid -and ([int]$prevPid -ne [int]$currPid)) {
                $restartServices += $name
            }
        } catch { }
    }
}
$restartDetected = ($restartServices.Count -gt 0)
$prevRestartCount = 0
try { if ($prevSnapshot -and $prevSnapshot.restart_count -ne $null) { $prevRestartCount = [int]$prevSnapshot.restart_count } } catch { }
$restartCount = $prevRestartCount + $restartServices.Count
$restartTransition = $restartDetected -and -not ($prevSnapshot -and $prevSnapshot.restart_detected -eq $true)
$hiddenRestartSuspected = $false
if ($restartDetected) {
    $hiddenRestartSuspected = Test-HiddenRestartSuspected -RepoRoot $repoRoot -RestartServices $restartServices -HeartbeatEmittedTs $heartbeatEmittedTs
}

$snapshotPayload = [ordered]@{
    schema = "station.service_runtime_snapshot.v1"
    authority_model_source = "docs/canonical/CALYX_CANONICAL_SYSTEM_MAP.md"
    authority_boundary_note = "Service runtime snapshot is generated support evidence, not sole liveness authority."
    clarity_status = $clarityStatus
    heartbeat_emitted_ts = $heartbeatEmittedTs
    station_boot_ts = $stationBootTs
    boot_session_id = $bootSessionId
    host_boot_ts = $hostBootTs
    host_boot_classification = $hostBootClassification
    restart_detected = $restartDetected
    restart_count = $restartCount
    memory_pressure_tier = $memoryPressureTier
    service_failure_active = ($serviceFailureOverlay.active_count -gt 0)
    service_failure_active_count = $serviceFailureOverlay.active_count
    service_failure_change_lane = $serviceFailureOverlay.change_lane
    service_failure_risk_lane = $serviceFailureOverlay.risk_lane
    service_failure_services = @($serviceFailureOverlay.services)
    service_failure_current_liveness_authority = $false
    derived_from_live_probe = $true
    services = $snapshotServices
}
$snapshotJson = $snapshotPayload | ConvertTo-Json -Depth 6 -Compress
$serviceSnapshotSha = Get-Sha256Hex -Text $snapshotJson
$snapshotPayload["service_snapshot_sha256"] = $serviceSnapshotSha
Add-TruthMetadataToArtifact -Artifact $snapshotPayload -ContractName "service_runtime_snapshot" -EmittedAtUtc $heartbeatNowUtc -ForceStale:$ForceStale -StaleReason $StaleReason
Write-JsonArtifact -Path $snapshotPath -Artifact $snapshotPayload

$heartbeatPayload = [ordered]@{
    schema = "station.heartbeat.v1"
    authority_model_source = "docs/canonical/CALYX_CANONICAL_SYSTEM_MAP.md"
    authority_boundary_note = "Station heartbeat is generated support evidence, not sole liveness authority."
    clarity_status = $clarityStatus
    heartbeat_emitted_ts = $heartbeatEmittedTs
    heartbeat_state_ts = $heartbeatTs
    station_boot_ts = $stationBootTs
    boot_session_id = $bootSessionId
    host_boot_ts = $hostBootTs
    host_boot_classification = $hostBootClassification
    memory_pressure_tier = $memoryPressureTier
    oom_imminent = $oomImminent
    services = $services
    restart_detected = $restartDetected
    restart_count = $restartCount
    hidden_restart_suspected = $hiddenRestartSuspected
    restart_services = $restartServices
    service_failure_active = ($serviceFailureOverlay.active_count -gt 0)
    service_failure_active_count = $serviceFailureOverlay.active_count
    service_failure_change_lane = $serviceFailureOverlay.change_lane
    service_failure_risk_lane = $serviceFailureOverlay.risk_lane
    service_failure_services = @($serviceFailureOverlay.services)
    service_failure_current_liveness_authority = $false
    derived_from_live_probe = $true
    service_snapshot_sha256 = $serviceSnapshotSha
}
$heartbeatJsonNoSha = $heartbeatPayload | ConvertTo-Json -Depth 6 -Compress
$heartbeatSha = Get-Sha256Hex -Text $heartbeatJsonNoSha
$heartbeatPayload["heartbeat_payload_sha256"] = $heartbeatSha
$heartbeatPath = Join-Path $repoRoot "runtime\station_heartbeat.json"
Add-TruthMetadataToArtifact -Artifact $heartbeatPayload -ContractName "station_heartbeat" -EmittedAtUtc $heartbeatNowUtc -ForceStale:$ForceStale -StaleReason $StaleReason
Write-JsonArtifact -Path $heartbeatPath -Artifact $heartbeatPayload

$topologySummary = $null
if (Test-Path -LiteralPath $topologyScript -PathType Leaf) {
    try {
        $topologyArgs = @($topologyScript, "--repo-root", $repoRoot, "--emitted-at", $heartbeatEmittedTs)
        if ($ForceStale) {
            $topologyArgs += "--force-stale"
            $topologyArgs += "--stale-reason"
            $topologyArgs += $StaleReason
        }
        & $pythonRuntime @topologyArgs 2>$null | Out-Null
        if (Test-Path -LiteralPath $topologySnapshotPath -PathType Leaf) {
            $topologyArtifact = Read-JsonArtifact -Path $topologySnapshotPath
            if ($topologyArtifact -and $topologyArtifact.state_summary) {
                $topologySummary = $topologyArtifact.state_summary
            }
        }
    } catch { }
}
if ($topologySummary) {
    $stateRuntimeValues.runtime_topology_ts = [string]$topologySummary.runtime_topology_ts
    $stateRuntimeValues.runtime_topology_truth_state = [string]$topologySummary.runtime_topology_truth_state
    $stateRuntimeValues.runtime_topology_risk = [string]$topologySummary.runtime_topology_risk
    $stateRuntimeValues.runtime_topology_active_services = [string]$topologySummary.runtime_topology_active_services
    if ($topologySummary.runtime_topology_authority_summary) {
        $stateRuntimeValues.runtime_topology_authority_summary = [string]$topologySummary.runtime_topology_authority_summary
    }
    $stateRuntimeValues.runtime_topology_duplicates = [string]$topologySummary.runtime_topology_duplicates
    $stateRuntimeValues.runtime_topology_authority_ambiguous = [string]$topologySummary.runtime_topology_authority_ambiguous
    $stateRuntimeValues.runtime_topology_flagged_services = [string]$topologySummary.runtime_topology_flagged_services
    Update-StateRuntimeBlock -StatePath $statePath -Values $stateRuntimeValues
}

$signalSummary = $null
if (Test-Path -LiteralPath $signalScript -PathType Leaf) {
    try {
        & $pythonRuntime $signalScript "--repo-root" $repoRoot 2>$null | Out-Null
        if (Test-Path -LiteralPath $signalDigestPath -PathType Leaf) {
            $signalDigest = Read-JsonArtifact -Path $signalDigestPath
            if ($signalDigest) {
                $signalSummary = $signalDigest
            }
        }
    } catch { }
}
if ($signalSummary) {
    $stateRuntimeValues.signal_level = if ($signalSummary.signal_level) { [string]$signalSummary.signal_level } else { "unknown" }
    $stateRuntimeValues.signal_top = if ($signalSummary.top_signal) { [string]$signalSummary.top_signal } else { "unknown" }
    $stateRuntimeValues.signal_count = if ($null -ne $signalSummary.signal_count) { [string]$signalSummary.signal_count } else { "0" }
    $stateRuntimeValues.signal_requires_operator_confirmation = if ($signalSummary.requires_operator_confirmation -eq $true) { "true" } else { "false" }
    $stateRuntimeValues.signal_operator_brief = Limit-Text -Text ([string]$signalSummary.operator_brief) -Max 220
    Update-StateRuntimeBlock -StatePath $statePath -Values $stateRuntimeValues
}

if (-not $ForceStale) {
    $restoreCandidates = @($priorDerivedObservations | Where-Object { $_.prior_state -eq "stale" -or (-not $_.freshness.is_fresh) })
    if ($restoreCandidates.Count -gt 0) {
        $observedRestoreUtc = [datetime]::UtcNow
        $priorBySurface = @{}
        foreach ($obs in $priorDerivedObservations) {
            $priorBySurface[$obs.surface] = $obs
        }
        $surfaceTransitions = @(
            [ordered]@{
                surface = "STATE.md"
                prior_state = if ($priorBySurface.ContainsKey("STATE.md")) { [string]$priorBySurface["STATE.md"].prior_state } else { "unknown" }
                new_state = "fresh"
                emitted_ts_utc = $heartbeatTs
                expiry_ts_utc = $stateTruthMetadata.expires_ts_utc
                observed_restore_ts_utc = $observedRestoreUtc.ToString("o")
                reason = "governed_refresh"
            },
            [ordered]@{
                surface = "station_heartbeat.json"
                prior_state = if ($priorBySurface.ContainsKey("station_heartbeat.json")) { [string]$priorBySurface["station_heartbeat.json"].prior_state } else { "unknown" }
                new_state = "fresh"
                emitted_ts_utc = $heartbeatPayload.emitted_ts_utc
                expiry_ts_utc = $heartbeatPayload.expires_ts_utc
                observed_restore_ts_utc = $observedRestoreUtc.ToString("o")
                reason = "governed_refresh"
            },
            [ordered]@{
                surface = "service_runtime_snapshot.json"
                prior_state = if ($priorBySurface.ContainsKey("service_runtime_snapshot.json")) { [string]$priorBySurface["service_runtime_snapshot.json"].prior_state } else { "unknown" }
                new_state = "fresh"
                emitted_ts_utc = $snapshotPayload.emitted_ts_utc
                expiry_ts_utc = $snapshotPayload.expires_ts_utc
                observed_restore_ts_utc = $observedRestoreUtc.ToString("o")
                reason = "governed_refresh"
            },
            [ordered]@{
                surface = "runtime_topology_snapshot.json"
                prior_state = if ($priorBySurface.ContainsKey("runtime_topology_snapshot.json")) { [string]$priorBySurface["runtime_topology_snapshot.json"].prior_state } else { "unknown" }
                new_state = "fresh"
                emitted_ts_utc = if ($stateRuntimeValues.runtime_topology_ts) { [string]$stateRuntimeValues.runtime_topology_ts } else { $heartbeatTs }
                expiry_ts_utc = if ($stateRuntimeValues.runtime_topology_truth_state -eq "fresh") { ([datetime]::Parse($heartbeatEmittedTs).ToUniversalTime().AddSeconds(120).ToString("o")) } else { $heartbeatTs }
                observed_restore_ts_utc = $observedRestoreUtc.ToString("o")
                reason = "governed_refresh"
            }
        )
        Write-DerivedTruthTransitionReceipt -RepoRoot $repoRoot -Transition "stale_to_fresh" -Reason "governed_refresh" -SurfaceTransitions $surfaceTransitions -ObservedAtUtc $observedRestoreUtc | Out-Null
    }
}

# Memory pressure receipt on tier change
$prevTier = $null
try { if ($prevSnapshot -and $prevSnapshot.memory_pressure_tier -ne $null) { $prevTier = [int]$prevSnapshot.memory_pressure_tier } } catch { }
if (-not $ForceStale -and $null -ne $memoryPressureTier) {
    if ($null -eq $prevTier -or $prevTier -ne $memoryPressureTier) {
        $receiptDir = Join-Path $repoRoot "runtime\receipts\memory_pressure"
        if (-not (Test-Path $receiptDir)) { New-Item -ItemType Directory -Path $receiptDir -Force | Out-Null }
        $tag = ([datetime]::Parse($heartbeatEmittedTs).ToUniversalTime()).ToString("yyyyMMdd_HHmmss")
        $receiptPath = Join-Path $receiptDir "memory_pressure__${tag}.json"
        $receipt = [ordered]@{
            schema = "station.memory_pressure.v1"
            wo_id = "WO_MEMORY_LIFECYCLE_HARDENING_V1"
            heartbeat_emitted_ts = $heartbeatEmittedTs
            station_boot_ts = $stationBootTs
            boot_session_id = $bootSessionId
            prev_tier = $prevTier
            new_tier = $memoryPressureTier
            ram_pct = $ramPct
            actions_taken = @()
            heartbeat_payload_sha256 = $heartbeatSha
        }
        $receipt | ConvertTo-Json -Depth 4 | Set-Content -Path $receiptPath -Encoding UTF8
    }
}


# Emit heartbeat.tick to Station Event Ledger (WO_STATION_EVENT_LEDGER_V1)
$emitScript = Join-Path $repoRoot "Scripts\emit_heartbeat_tick.py"
if (-not $ForceStale -and (Test-Path $emitScript)) {
    try {
        $args = @($checksOutput, $health, "--heartbeat", $heartbeatPath)
        if ($restartTransition) { $args += "--restart-transition" }
        python $emitScript @args 2>$null
    } catch { }
}

Write-Output "STATE.md updated: checks=$checksOutput heartbeat_ts=$heartbeatTs health=$($stateRuntimeValues.health) entropy_tier=$($stateRuntimeValues.entropy_tier) navigator_interval=$($stateRuntimeValues.navigator_interval) triage_status=$($stateRuntimeValues.triage_status) cpu_target=$($stateRuntimeValues.cpu_target) runtime_truth_state=$($stateRuntimeValues.runtime_truth_state) active_objective_status=$($stateRuntimeValues.active_objective_status) confusion_policy=$($stateRuntimeValues.confusion_policy) source_authority_registry=$($stateRuntimeValues.source_authority_registry) failure_flags_active=$failureFlagsActive failure_risk_lane=$failureRiskLane runtime_topology_risk=$($stateRuntimeValues.runtime_topology_risk) runtime_topology_duplicates=$($stateRuntimeValues.runtime_topology_duplicates) signal_level=$($stateRuntimeValues.signal_level) signal_top=$($stateRuntimeValues.signal_top)"
