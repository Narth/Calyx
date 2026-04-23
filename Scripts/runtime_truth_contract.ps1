# Shared runtime truth freshness contract for Station Calyx.
# This helper centralizes TTLs, stale labels, state-surface mutation, and receipts.

$script:RuntimeTruthContracts = [ordered]@{
    station_health = [ordered]@{
        freshness_window_sec = 15
        stale_label = "STALE_HEALTH"
        timestamp_fields = @("emitted_ts_utc", "health_ts")
    }
    station_heartbeat = [ordered]@{
        freshness_window_sec = 120
        stale_label = "STALE_HEARTBEAT"
        timestamp_fields = @("emitted_ts_utc", "heartbeat_emitted_ts", "heartbeat_state_ts")
    }
    service_runtime_snapshot = [ordered]@{
        freshness_window_sec = 120
        stale_label = "STALE_SNAPSHOT"
        timestamp_fields = @("emitted_ts_utc", "heartbeat_emitted_ts")
    }
    runtime_topology_snapshot = [ordered]@{
        freshness_window_sec = 120
        stale_label = "STALE_TOPOLOGY"
        timestamp_fields = @("emitted_ts_utc")
    }
    state_runtime = [ordered]@{
        freshness_window_sec = 120
        stale_label = "STALE_STATE"
        timestamp_fields = @("heartbeat_ts")
    }
    navigator = [ordered]@{
        freshness_window_sec = 180
        stale_label = "STALE_ADVISORY"
        timestamp_fields = @("emitted_ts_utc", "ts_utc", "ts")
    }
    triage = [ordered]@{
        freshness_window_sec = 180
        stale_label = "STALE_ADVISORY"
        timestamp_fields = @("emitted_ts_utc", "ts_utc", "ts")
    }
    cp6 = [ordered]@{
        freshness_window_sec = 900
        stale_label = "STALE_ADVISORY"
        timestamp_fields = @("emitted_ts_utc", "ts_utc", "ts")
    }
    cp7 = [ordered]@{
        freshness_window_sec = 900
        stale_label = "STALE_ADVISORY"
        timestamp_fields = @("emitted_ts_utc", "ts_utc", "ts")
    }
    cp9 = [ordered]@{
        freshness_window_sec = 600
        stale_label = "STALE_TUNING"
        timestamp_fields = @("emitted_ts_utc", "ts_utc", "ts")
    }
}

function Get-RuntimeTruthContract {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not $script:RuntimeTruthContracts.Contains($Name)) {
        throw "Unknown runtime truth contract: $Name"
    }
    return $script:RuntimeTruthContracts[$Name]
}

function Get-UtcNowString {
    param([datetime]$NowUtc = [datetime]::UtcNow)
    return $NowUtc.ToString("o")
}

function ConvertTo-UtcDateTime {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return $null }
    $raw = [string]$Value
    if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
    try {
        return [datetimeoffset]::Parse($raw).UtcDateTime
    } catch {
        return $null
    }
}

function Read-JsonArtifact {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    try {
        return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Write-JsonArtifact {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][object]$Artifact,
        [int]$Depth = 12,
        [int]$RetryCount = 6,
        [int]$RetryDelayMs = 200
    )
    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $json = $Artifact | ConvertTo-Json -Depth $Depth
    for ($attempt = 1; $attempt -le $RetryCount; $attempt++) {
        try {
            [System.IO.File]::WriteAllText($Path, $json, [System.Text.UTF8Encoding]::new($false))
            return
        } catch {
            if ($attempt -ge $RetryCount) { throw }
            Start-Sleep -Milliseconds $RetryDelayMs
        }
    }
}

function Set-ArtifactProperty {
    param(
        [Parameter(Mandatory = $true)][object]$Artifact,
        [Parameter(Mandatory = $true)][string]$Name,
        [AllowNull()][object]$Value
    )
    if ($Artifact -is [System.Collections.IDictionary]) {
        $Artifact[$Name] = $Value
        return
    }
    $prop = $Artifact.PSObject.Properties[$Name]
    if ($prop) {
        $prop.Value = $Value
    } else {
        $Artifact | Add-Member -NotePropertyName $Name -NotePropertyValue $Value
    }
}

function Get-ArtifactCurrentTruthState {
    param(
        [AllowNull()][object]$Artifact,
        [AllowNull()][object]$Freshness
    )
    if ($Artifact) {
        $prop = $Artifact.PSObject.Properties["truth_state"]
        if ($prop -and $prop.Value) {
            return [string]$prop.Value
        }
        $stateProp = $Artifact.PSObject.Properties["runtime_truth_state"]
        if ($stateProp -and $stateProp.Value) {
            return [string]$stateProp.Value
        }
    }
    if ($Freshness) {
        $isFreshProp = $Freshness.PSObject.Properties["is_fresh"]
        if ($isFreshProp -and $isFreshProp.Value) {
            return "fresh"
        }
    }
    return "unknown"
}

function Read-StateRuntimeBlock {
    param([Parameter(Mandatory = $true)][string]$StatePath)
    if (-not (Test-Path -LiteralPath $StatePath -PathType Leaf)) { return $null }
    $keys = @(
        "heartbeat_ts",
        "health",
        "health_ts",
        "entropy_tier",
        "navigator_interval",
        "triage_status",
        "cpu_target",
        "runtime_truth_state",
        "runtime_truth_expires_ts",
        "runtime_truth_label",
        "runtime_truth_canonical",
        "checks",
        "failure_flags_active",
        "failure_change_lane",
        "failure_risk_lane",
        "failure_flag_services",
        "runtime_topology_ts",
        "runtime_topology_truth_state",
        "runtime_topology_risk",
        "runtime_topology_active_services",
        "runtime_topology_duplicates",
        "runtime_topology_authority_ambiguous",
        "runtime_topology_flagged_services"
    )
    $values = [ordered]@{}
    foreach ($key in $keys) {
        $values[$key] = ""
    }
    foreach ($line in (Get-Content -LiteralPath $StatePath -Encoding UTF8)) {
        foreach ($key in $keys) {
            if ($line.StartsWith("${key}:")) {
                $values[$key] = ($line.Substring($key.Length + 1)).Trim()
                break
            }
        }
    }
    return [pscustomobject]$values
}

function Get-ArtifactTimestampInfo {
    param(
        [AllowNull()][object]$Artifact,
        [string[]]$TimestampFields,
        [string]$Path = ""
    )
    if ($Artifact) {
        foreach ($field in $TimestampFields) {
            $prop = $Artifact.PSObject.Properties[$field]
            if (-not $prop -or $null -eq $prop.Value) { continue }
            $parsed = ConvertTo-UtcDateTime -Value $prop.Value
            if ($parsed) {
                return [ordered]@{
                    ts_utc = $parsed.ToString("o")
                    source = $field
                }
            }
        }
    }
    if ($Path -and (Test-Path -LiteralPath $Path -PathType Leaf)) {
        $item = Get-Item -LiteralPath $Path
        return [ordered]@{
            ts_utc = $item.LastWriteTimeUtc.ToString("o")
            source = "file_mtime_utc"
        }
    }
    return [ordered]@{
        ts_utc = ""
        source = ""
    }
}

function Get-ArtifactFreshness {
    param(
        [Parameter(Mandatory = $true)][string]$ContractName,
        [AllowNull()][object]$Artifact,
        [string]$Path = "",
        [datetime]$NowUtc = [datetime]::UtcNow
    )
    $contract = Get-RuntimeTruthContract -Name $ContractName
    $tsInfo = Get-ArtifactTimestampInfo -Artifact $Artifact -TimestampFields $contract.timestamp_fields -Path $Path
    $emittedAt = ConvertTo-UtcDateTime -Value $tsInfo.ts_utc
    $explicitExpiry = $null
    $explicitTruthState = ""
    if ($Artifact) {
        $expiryProp = $Artifact.PSObject.Properties["expires_ts_utc"]
        if ($expiryProp -and $expiryProp.Value) {
            $explicitExpiry = ConvertTo-UtcDateTime -Value $expiryProp.Value
        } else {
            $stateExpiryProp = $Artifact.PSObject.Properties["runtime_truth_expires_ts"]
            if ($stateExpiryProp -and $stateExpiryProp.Value) {
                $explicitExpiry = ConvertTo-UtcDateTime -Value $stateExpiryProp.Value
            }
        }
        $truthProp = $Artifact.PSObject.Properties["truth_state"]
        if ($truthProp -and $truthProp.Value) {
            $explicitTruthState = [string]$truthProp.Value
        } else {
            $stateTruthProp = $Artifact.PSObject.Properties["runtime_truth_state"]
            if ($stateTruthProp -and $stateTruthProp.Value) {
                $explicitTruthState = [string]$stateTruthProp.Value
            }
        }
    }
    if (-not $emittedAt) {
        return [ordered]@{
            emitted_ts_utc = ""
            freshness_window_sec = [int]$contract.freshness_window_sec
            expires_ts_utc = if ($explicitExpiry) { $explicitExpiry.ToString("o") } else { "" }
            truth_state = if ($explicitTruthState) { $explicitTruthState } else { "unknown" }
            stale_label = if ($explicitTruthState -eq "stale") { $contract.stale_label } else { $contract.stale_label }
            authoritative_for_liveness = $false
            is_fresh = $false
            timestamp_source = $tsInfo.source
            age_sec = $null
        }
    }
    $expiresAt = if ($explicitExpiry) { $explicitExpiry } else { $emittedAt.AddSeconds([int]$contract.freshness_window_sec) }
    $isFresh = ($explicitTruthState -ne "stale") -and ($NowUtc -le $expiresAt)
    return [ordered]@{
        emitted_ts_utc = $emittedAt.ToString("o")
        freshness_window_sec = [int]$contract.freshness_window_sec
        expires_ts_utc = $expiresAt.ToString("o")
        truth_state = if ($isFresh) { "fresh" } elseif ($explicitTruthState) { $explicitTruthState } else { "stale" }
        stale_label = if ($isFresh) { "" } else { $contract.stale_label }
        authoritative_for_liveness = $false
        is_fresh = $isFresh
        timestamp_source = $tsInfo.source
        age_sec = [math]::Round(($NowUtc - $emittedAt).TotalSeconds, 3)
    }
}

function New-TruthMetadata {
    param(
        [Parameter(Mandatory = $true)][string]$ContractName,
        [datetime]$EmittedAtUtc = [datetime]::UtcNow,
        [switch]$ForceStale,
        [string]$StaleReason = ""
    )
    $contract = Get-RuntimeTruthContract -Name $ContractName
    $expiresAt = if ($ForceStale) { $EmittedAtUtc } else { $EmittedAtUtc.AddSeconds([int]$contract.freshness_window_sec) }
    return [ordered]@{
        emitted_ts_utc = $EmittedAtUtc.ToString("o")
        freshness_window_sec = [int]$contract.freshness_window_sec
        expires_ts_utc = $expiresAt.ToString("o")
        truth_state = if ($ForceStale) { "stale" } else { "fresh" }
        stale_label = if ($ForceStale) { $contract.stale_label } else { "" }
        authoritative_for_liveness = $false
        stale_reason = if ($ForceStale) { $StaleReason } else { "" }
    }
}

function Add-TruthMetadataToArtifact {
    param(
        [Parameter(Mandatory = $true)][object]$Artifact,
        [Parameter(Mandatory = $true)][string]$ContractName,
        [datetime]$EmittedAtUtc = [datetime]::UtcNow,
        [switch]$ForceStale,
        [string]$StaleReason = ""
    )
    $metadata = New-TruthMetadata -ContractName $ContractName -EmittedAtUtc $EmittedAtUtc -ForceStale:$ForceStale -StaleReason $StaleReason
    foreach ($key in $metadata.Keys) {
        Set-ArtifactProperty -Artifact $Artifact -Name $key -Value $metadata[$key]
    }
}

function Write-RuntimeTruthReceipt {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$RelativeDir,
        [Parameter(Mandatory = $true)][string]$Prefix,
        [Parameter(Mandatory = $true)][hashtable]$Payload
    )
    $receiptDir = Join-Path $RepoRoot $RelativeDir
    if (-not (Test-Path -LiteralPath $receiptDir)) {
        New-Item -ItemType Directory -Path $receiptDir -Force | Out-Null
    }
    $stamp = [datetime]::UtcNow.ToString("yyyyMMdd_HHmmss_fff")
    $receiptPath = Join-Path $receiptDir ("{0}__{1}.json" -f $Prefix, $stamp)
    Write-JsonArtifact -Path $receiptPath -Artifact $Payload
    return $receiptPath
}

function Get-StationLifecycleArtifactPath {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$ArtifactName
    )
    $runtimeDir = Join-Path $RepoRoot "runtime"
    switch ($ArtifactName) {
        "station_shutdown_marker" { return (Join-Path $runtimeDir "station_shutdown_marker.json") }
        "host_boot_detected" { return (Join-Path $runtimeDir "host_boot_detected.json") }
        "station_unclean_interruption" { return (Join-Path $runtimeDir "station_unclean_interruption.json") }
        "station_recovery_status" { return (Join-Path $runtimeDir "station_recovery_status.json") }
        default { throw "Unknown station lifecycle artifact: $ArtifactName" }
    }
}

function Write-StationLifecycleArtifact {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$ArtifactName,
        [Parameter(Mandatory = $true)][hashtable]$Payload
    )
    $latestPath = Get-StationLifecycleArtifactPath -RepoRoot $RepoRoot -ArtifactName $ArtifactName
    Write-JsonArtifact -Path $latestPath -Artifact $Payload
    $receiptPath = Write-RuntimeTruthReceipt -RepoRoot $RepoRoot -RelativeDir "runtime\receipts\audit" -Prefix $ArtifactName -Payload $Payload
    return [ordered]@{
        latest_path = $latestPath
        receipt_path = $receiptPath
    }
}

function Read-StationLifecycleArtifact {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$ArtifactName
    )
    $path = Get-StationLifecycleArtifactPath -RepoRoot $RepoRoot -ArtifactName $ArtifactName
    return Read-JsonArtifact -Path $path
}

function Get-HostBootTimeUtc {
    try {
        $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
        if ($os -and $os.LastBootUpTime) {
            return ([datetime]$os.LastBootUpTime).ToUniversalTime()
        }
    } catch { }
    try {
        $evt = Get-WinEvent -FilterHashtable @{ LogName = "System"; Id = 12 } -MaxEvents 1 -ErrorAction Stop | Select-Object -First 1
        if ($evt -and $evt.TimeCreated) {
            return ([datetime]$evt.TimeCreated).ToUniversalTime()
        }
    } catch { }
    return $null
}

function Test-StationPortListening {
    param([int]$Port)
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($conn) { return $true }
    } catch { }
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $client.Connect("127.0.0.1", $Port)
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

function Get-StationProcessMatches {
    param(
        [string]$ProcessName,
        [string]$CommandPattern
    )
    $matches = @()
    try {
        $procs = Get-Process $ProcessName -ErrorAction SilentlyContinue
        foreach ($proc in $procs) {
            try {
                $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.Id)" -ErrorAction SilentlyContinue).CommandLine
                if ($cmd -and $cmd -match $CommandPattern) {
                    $matches += $proc
                }
            } catch { }
        }
    } catch { }
    return ,$matches
}

function Get-StationActiveServiceSummary {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )
    $serviceNames = [System.Collections.Generic.HashSet[string]]::new()
    $portMap = [ordered]@{
        dev_harness = 7777
        cbo_core = 7778
        avatar_web = 7780
        telemetry_gateway = 7781
    }
    foreach ($name in $portMap.Keys) {
        if (Test-StationPortListening -Port $portMap[$name]) {
            [void]$serviceNames.Add($name)
        }
    }
    $processMatchers = @(
        @{ service = "station_health_loop"; process = "powershell"; pattern = "station_health_loop\.ps1" },
        @{ service = "service_failure_watch"; process = "powershell"; pattern = "service_failure_watch\.ps1" },
        @{ service = "navigator_triage_loop"; process = "powershell"; pattern = "navigator_triage_loop\.ps1" },
        @{ service = "energy_churn_cp9_loop"; process = "powershell"; pattern = "energy_churn_cp9_loop\.ps1" },
        @{ service = "cp6_cp7_loop"; process = "powershell"; pattern = "cp6_cp7_loop\.ps1" },
        @{ service = "bridge_overseer"; process = "python"; pattern = "calyx\.cbo\.bridge_overseer" },
        @{ service = "cli_avatar"; process = "python"; pattern = "cbo_hub\.cli_avatar\.main" },
        @{ service = "discord_gateway"; process = "python"; pattern = "calyx\.cbo\.discord_gateway" }
    )
    foreach ($matcher in $processMatchers) {
        $hits = Get-StationProcessMatches -ProcessName $matcher.process -CommandPattern $matcher.pattern
        if ($hits.Count -gt 0) {
            [void]$serviceNames.Add([string]$matcher.service)
        }
    }
    return @($serviceNames | Sort-Object)
}

function Get-StationActiveLeaseSummary {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )
    $runtimeSwarmDir = Join-Path $RepoRoot "runtime\cbo\swarm"
    $activeLeases = @()
    $inFlightOperations = [System.Collections.Generic.HashSet[string]]::new()
    if (-not (Test-Path -LiteralPath $runtimeSwarmDir -PathType Container)) {
        return [ordered]@{
            active_leases = @()
            in_flight_operations = @()
        }
    }
    foreach ($artifact in (Get-ChildItem -Path $runtimeSwarmDir -Filter "worker_leases.json" -File -Recurse -ErrorAction SilentlyContinue)) {
        $payload = Read-JsonArtifact -Path $artifact.FullName
        if (-not $payload -or -not $payload.leases) { continue }
        foreach ($lease in @($payload.leases)) {
            $state = [string]$lease.lease_state
            if ($state -in @("completed", "revoked", "expired")) { continue }
            $row = [ordered]@{
                swarm_run_id = [string]$lease.swarm_run_id
                work_envelope_id = [string]$lease.work_envelope_id
                lease_id = [string]$lease.lease_id
                worker_id = [string]$lease.worker_id
                lease_state = $state
            }
            $activeLeases += $row
            if ($row.swarm_run_id) {
                [void]$inFlightOperations.Add($row.swarm_run_id)
            }
        }
    }
    return [ordered]@{
        active_leases = @($activeLeases)
        in_flight_operations = @($inFlightOperations | Sort-Object)
    }
}

function Get-StationLifecycleEvidenceTable {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )
    return @(
        @{ surface = "STATE.md"; path = (Join-Path $RepoRoot "STATE.md"); contract = "state_runtime"; kind = "state" },
        @{ surface = "station_health.json"; path = (Join-Path $RepoRoot "runtime\station_health.json"); contract = "station_health"; kind = "json" },
        @{ surface = "station_heartbeat.json"; path = (Join-Path $RepoRoot "runtime\station_heartbeat.json"); contract = "station_heartbeat"; kind = "json" },
        @{ surface = "service_runtime_snapshot.json"; path = (Join-Path $RepoRoot "runtime\service_runtime_snapshot.json"); contract = "service_runtime_snapshot"; kind = "json" },
        @{ surface = "runtime_topology_snapshot.json"; path = (Join-Path $RepoRoot "runtime\runtime_topology_snapshot.json"); contract = "runtime_topology_snapshot"; kind = "json" }
    )
}

function Get-StationLifecycleEvidenceSummary {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [datetime]$NowUtc = [datetime]::UtcNow
    )
    $rows = @()
    $latestTs = $null
    $latestSurface = ""
    $latestPath = ""
    foreach ($surfaceInfo in (Get-StationLifecycleEvidenceTable -RepoRoot $RepoRoot)) {
        $artifact = if ($surfaceInfo.kind -eq "state") {
            Read-StateRuntimeBlock -StatePath $surfaceInfo.path
        } else {
            Read-JsonArtifact -Path $surfaceInfo.path
        }
        $freshness = Get-ArtifactFreshness -ContractName $surfaceInfo.contract -Artifact $artifact -Path $surfaceInfo.path -NowUtc $NowUtc
        $surfaceTs = ConvertTo-UtcDateTime -Value $freshness.emitted_ts_utc
        if ($surfaceTs -and ((-not $latestTs) -or $surfaceTs -gt $latestTs)) {
            $latestTs = $surfaceTs
            $latestSurface = [string]$surfaceInfo.surface
            $latestPath = [string]$surfaceInfo.path
        }
        $rows += [ordered]@{
            surface = [string]$surfaceInfo.surface
            path = [string]$surfaceInfo.path
            exists = (Test-Path -LiteralPath $surfaceInfo.path -PathType Leaf)
            timestamp_utc = if ($surfaceTs) { $surfaceTs.ToString("o") } else { "" }
            truth_state = if ($artifact) { Get-ArtifactCurrentTruthState -Artifact $artifact -Freshness $freshness } else { "missing" }
            is_fresh = [bool]$freshness.is_fresh
            stale_reason = if ($freshness.stale_reason) { [string]$freshness.stale_reason } else { "" }
        }
    }
    return [ordered]@{
        latest_artifact_ts_utc = if ($latestTs) { $latestTs.ToString("o") } else { "" }
        latest_artifact_surface = $latestSurface
        latest_artifact_path = $latestPath
        surfaces = @($rows)
    }
}

function Emit-StationShutdownMarker {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [ValidateSet("manual", "patch", "restart")][string]$Reason = "manual",
        [datetime]$ObservedAtUtc = [datetime]::UtcNow,
        [AllowNull()][object[]]$ServiceSummary,
        [AllowNull()][hashtable]$LeaseSummary,
        [AllowNull()][string[]]$InFlightOperations
    )
    $observedUtc = $ObservedAtUtc.ToUniversalTime()
    $services = if ($null -ne $ServiceSummary) { @($ServiceSummary) } else { @(Get-StationActiveServiceSummary -RepoRoot $RepoRoot) }
    $leaseInfo = if ($LeaseSummary) { $LeaseSummary } else { Get-StationActiveLeaseSummary -RepoRoot $RepoRoot }
    $activeLeases = if ($leaseInfo.active_leases) { @($leaseInfo.active_leases) } else { @() }
    $operations = if ($null -ne $InFlightOperations) { @($InFlightOperations) } elseif ($leaseInfo.in_flight_operations) { @($leaseInfo.in_flight_operations) } else { @() }
    $payload = [ordered]@{
        schema = "station.shutdown_marker.v1"
        shutdown_ts_utc = $observedUtc.ToString("o")
        reason = $Reason
        active_services = @($services | Sort-Object)
        active_service_count = @($services).Count
        active_leases = @($activeLeases)
        active_lease_count = @($activeLeases).Count
        in_flight_operations = @($operations | Sort-Object)
        in_flight_operation_count = @($operations).Count
    }
    return Write-StationLifecycleArtifact -RepoRoot $RepoRoot -ArtifactName "station_shutdown_marker" -Payload $payload
}

function Emit-HostBootDetected {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [datetime]$ObservedAtUtc = [datetime]::UtcNow,
        [AllowNull()][datetime]$HostBootUtc,
        [AllowNull()][hashtable]$LifecycleSummary,
        [AllowNull()][object]$ShutdownMarker
    )
    $observedUtc = $ObservedAtUtc.ToUniversalTime()
    $bootUtc = if ($HostBootUtc) { $HostBootUtc.ToUniversalTime() } else { Get-HostBootTimeUtc }
    $summary = if ($LifecycleSummary) { $LifecycleSummary } else { Get-StationLifecycleEvidenceSummary -RepoRoot $RepoRoot -NowUtc $observedUtc }
    $marker = if ($ShutdownMarker) { $ShutdownMarker } else { Read-StationLifecycleArtifact -RepoRoot $RepoRoot -ArtifactName "station_shutdown_marker" }
    $latestArtifactUtc = ConvertTo-UtcDateTime -Value $summary.latest_artifact_ts_utc
    $shutdownUtc = if ($marker) { ConvertTo-UtcDateTime -Value $marker.shutdown_ts_utc } else { $null }
    $classification = "normal_restart"
    $reasons = @()
    if ($latestArtifactUtc) {
        if (-not $shutdownUtc) {
            $classification = "post_interruption_restart"
            $reasons += "missing_clean_shutdown_marker"
        } elseif ($shutdownUtc.AddSeconds(2) -lt $latestArtifactUtc) {
            $classification = "post_interruption_restart"
            $reasons += "shutdown_marker_older_than_last_station_artifact"
        }
    }
    if ($bootUtc -and $latestArtifactUtc) {
        $deltaSeconds = [math]::Round(($bootUtc - $latestArtifactUtc).TotalSeconds, 3)
    } else {
        $deltaSeconds = $null
    }
    $payload = [ordered]@{
        schema = "station.host_boot_detected.v1"
        observed_ts_utc = $observedUtc.ToString("o")
        os_boot_ts_utc = if ($bootUtc) { $bootUtc.ToString("o") } else { "" }
        last_station_artifact_ts_utc = if ($latestArtifactUtc) { $latestArtifactUtc.ToString("o") } else { "" }
        last_station_artifact_surface = if ($summary.latest_artifact_surface) { [string]$summary.latest_artifact_surface } else { "" }
        delta_from_last_station_artifact_sec = $deltaSeconds
        previous_station_artifacts_detected = [bool]$latestArtifactUtc
        clean_shutdown_marker_present = [bool]$shutdownUtc
        clean_shutdown_marker_ts_utc = if ($shutdownUtc) { $shutdownUtc.ToString("o") } else { "" }
        classification = $classification
        classification_reasons = @($reasons)
    }
    return Write-StationLifecycleArtifact -RepoRoot $RepoRoot -ArtifactName "host_boot_detected" -Payload $payload
}

function Emit-StationUncleanInterruption {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [datetime]$ObservedAtUtc = [datetime]::UtcNow,
        [AllowNull()][datetime]$HostBootUtc,
        [AllowNull()][hashtable]$LifecycleSummary,
        [AllowNull()][object]$ShutdownMarker,
        [AllowNull()][object]$HostBootArtifact
    )
    $observedUtc = $ObservedAtUtc.ToUniversalTime()
    $summary = if ($LifecycleSummary) { $LifecycleSummary } else { Get-StationLifecycleEvidenceSummary -RepoRoot $RepoRoot -NowUtc $observedUtc }
    $bootArtifact = if ($HostBootArtifact) { $HostBootArtifact } else { Read-StationLifecycleArtifact -RepoRoot $RepoRoot -ArtifactName "host_boot_detected" }
    if (-not $bootArtifact) {
        $bootPaths = Emit-HostBootDetected -RepoRoot $RepoRoot -ObservedAtUtc $observedUtc -HostBootUtc $HostBootUtc -LifecycleSummary $summary -ShutdownMarker $ShutdownMarker
        $bootArtifact = Read-JsonArtifact -Path $bootPaths.latest_path
    }
    $bootUtc = if ($HostBootUtc) { $HostBootUtc.ToUniversalTime() } else { ConvertTo-UtcDateTime -Value $bootArtifact.os_boot_ts_utc }
    $marker = if ($ShutdownMarker) { $ShutdownMarker } else { Read-StationLifecycleArtifact -RepoRoot $RepoRoot -ArtifactName "station_shutdown_marker" }
    $affectedSurfaces = @()
    foreach ($row in @($summary.surfaces)) {
        $surfaceTs = ConvertTo-UtcDateTime -Value $row.timestamp_utc
        if ($bootUtc -and $surfaceTs -and $surfaceTs -lt $bootUtc) {
            $affectedSurfaces += [ordered]@{
                surface = [string]$row.surface
                path = [string]$row.path
                timestamp_utc = [string]$row.timestamp_utc
                truth_state = [string]$row.truth_state
            }
        }
    }
    $detected = ($bootArtifact.classification -eq "post_interruption_restart")
    $confidence = if ($detected -and (-not $marker)) { "high" } elseif ($detected) { "medium" } else { "high" }
    $payload = [ordered]@{
        schema = "station.unclean_interruption.v1"
        observed_ts_utc = $observedUtc.ToString("o")
        interruption_detected = $detected
        classification = if ($detected) { "unclean_interruption_detected" } else { "no_unclean_interruption_detected" }
        confidence = $confidence
        os_boot_ts_utc = if ($bootUtc) { $bootUtc.ToString("o") } else { "" }
        last_station_artifact_ts_utc = if ($summary.latest_artifact_ts_utc) { [string]$summary.latest_artifact_ts_utc } else { "" }
        inferred_interruption_window = [ordered]@{
            start_after_utc = if ($summary.latest_artifact_ts_utc) { [string]$summary.latest_artifact_ts_utc } else { "" }
            end_at_or_before_utc = if ($bootUtc) { $bootUtc.ToString("o") } else { "" }
        }
        affected_surfaces = @($affectedSurfaces)
        missing_clean_shutdown_marker = (-not $marker)
        stale_truth_surfaces_at_boot = @($affectedSurfaces | Where-Object { $_.truth_state -eq "stale" -or $_.truth_state -eq "missing" })
        host_boot_detected_ref = Get-StationLifecycleArtifactPath -RepoRoot $RepoRoot -ArtifactName "host_boot_detected"
    }
    return Write-StationLifecycleArtifact -RepoRoot $RepoRoot -ArtifactName "station_unclean_interruption" -Payload $payload
}

function Emit-StationRecoveryStatus {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [datetime]$ObservedAtUtc = [datetime]::UtcNow,
        [int]$StartExitCode = 0,
        [switch]$StartCoreOnly,
        [AllowNull()][hashtable]$ServiceStatuses,
        [AllowNull()][hashtable]$PortStatuses
    )
    $observedUtc = $ObservedAtUtc.ToUniversalTime()
    $serviceMap = if ($ServiceStatuses) {
        $ServiceStatuses
    } else {
        [ordered]@{
            dev_harness = if (Test-StationPortListening -Port 7777) { "ok" } else { "missing" }
            cbo_core = if (Test-StationPortListening -Port 7778) { "ok" } else { "missing" }
            avatar_web = if (Test-StationPortListening -Port 7780) { "ok" } else { "missing" }
            telemetry_gateway = if (Test-StationPortListening -Port 7781) { "ok" } else { "missing" }
        }
    }
    $ports = if ($PortStatuses) {
        $normalizedPorts = [ordered]@{}
        foreach ($key in $PortStatuses.Keys) {
            $normalizedPorts[[string]$key] = $PortStatuses[$key]
        }
        $normalizedPorts
    } else {
        [ordered]@{
            "7777" = if (Test-StationPortListening -Port 7777) { "listening" } else { "not_listening" }
            "7778" = if (Test-StationPortListening -Port 7778) { "listening" } else { "not_listening" }
            "7780" = if (Test-StationPortListening -Port 7780) { "listening" } else { "not_listening" }
            "7781" = if (Test-StationPortListening -Port 7781) { "listening" } else { "not_listening" }
        }
    }
    $truthSurfaces = @()
    foreach ($surfaceInfo in (Get-DerivedTruthSurfaceTable -RepoRoot $RepoRoot)) {
        $artifact = if ($surfaceInfo.kind -eq "state") {
            Read-StateRuntimeBlock -StatePath $surfaceInfo.path
        } else {
            Read-JsonArtifact -Path $surfaceInfo.path
        }
        $freshness = Get-ArtifactFreshness -ContractName $surfaceInfo.contract -Artifact $artifact -Path $surfaceInfo.path -NowUtc $observedUtc
        $truthSurfaces += [ordered]@{
            surface = [string]$surfaceInfo.surface
            path = [string]$surfaceInfo.path
            truth_state = if ($artifact) { Get-ArtifactCurrentTruthState -Artifact $artifact -Freshness $freshness } else { "missing" }
            is_fresh = [bool]$freshness.is_fresh
            emitted_ts_utc = if ($freshness.emitted_ts_utc) { [string]$freshness.emitted_ts_utc } else { "" }
        }
    }
    $restored = @($serviceMap.Keys | Where-Object { $serviceMap[$_] -eq "ok" } | Sort-Object)
    $failed = @($serviceMap.Keys | Where-Object { $serviceMap[$_] -ne "ok" } | Sort-Object)
    $topologyArtifact = Read-JsonArtifact -Path (Join-Path $RepoRoot "runtime\runtime_topology_snapshot.json")
    $payload = [ordered]@{
        schema = "station.recovery_status.v1"
        observed_ts_utc = $observedUtc.ToString("o")
        start_exit_code = $StartExitCode
        start_mode = if ($StartCoreOnly) { "core_only" } else { "full_station" }
        restored_services = @($restored)
        missing_or_failed_services = @($failed)
        services = $serviceMap
        port_bindings = $ports
        truth_surfaces = @($truthSurfaces)
        topology_snapshot_available = [bool]$topologyArtifact
        topology_truth_state = if ($topologyArtifact -and $topologyArtifact.truth_state) { [string]$topologyArtifact.truth_state } else { "missing" }
        recovery_classification = if (($StartExitCode -eq 0) -and ($failed.Count -eq 0)) { "complete" } elseif ($restored.Count -gt 0) { "partial" } else { "failed" }
    }
    return Write-StationLifecycleArtifact -RepoRoot $RepoRoot -ArtifactName "station_recovery_status" -Payload $payload
}

function Write-DerivedTruthTransitionReceipt {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$Transition,
        [Parameter(Mandatory = $true)][string]$Reason,
        [Parameter(Mandatory = $true)][object[]]$SurfaceTransitions,
        [datetime]$ObservedAtUtc = [datetime]::UtcNow
    )
    if (-not $SurfaceTransitions -or $SurfaceTransitions.Count -eq 0) { return $null }
    $payload = [ordered]@{
        schema = "station.runtime_truth_transition.v1"
        ts_utc = $ObservedAtUtc.ToString("o")
        transition = $Transition
        reason = $Reason
        surfaces = @($SurfaceTransitions | ForEach-Object { $_.surface })
        surface_transitions = $SurfaceTransitions
    }
    return Write-RuntimeTruthReceipt -RepoRoot $RepoRoot -RelativeDir "runtime\receipts\security" -Prefix "runtime_truth_transition" -Payload $payload
}

function Set-JsonArtifactStale {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$ContractName,
        [Parameter(Mandatory = $true)][string]$Reason,
        [datetime]$ObservedAtUtc = [datetime]::UtcNow
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    $artifact = Read-JsonArtifact -Path $Path
    if (-not $artifact) {
        $artifact = [ordered]@{}
    }
    $nowUtc = $ObservedAtUtc
    $freshness = Get-ArtifactFreshness -ContractName $ContractName -Artifact $artifact -Path $Path -NowUtc $nowUtc
    $priorTruthState = Get-ArtifactCurrentTruthState -Artifact $artifact -Freshness $freshness
    if (-not $freshness.emitted_ts_utc) {
        Set-ArtifactProperty -Artifact $artifact -Name "emitted_ts_utc" -Value $nowUtc.ToString("o")
    } elseif (-not $artifact.PSObject.Properties["emitted_ts_utc"]) {
        Set-ArtifactProperty -Artifact $artifact -Name "emitted_ts_utc" -Value $freshness.emitted_ts_utc
    }
    $contract = Get-RuntimeTruthContract -Name $ContractName
    Set-ArtifactProperty -Artifact $artifact -Name "freshness_window_sec" -Value ([int]$contract.freshness_window_sec)
    Set-ArtifactProperty -Artifact $artifact -Name "expires_ts_utc" -Value $nowUtc.ToString("o")
    Set-ArtifactProperty -Artifact $artifact -Name "truth_state" -Value "stale"
    Set-ArtifactProperty -Artifact $artifact -Name "stale_label" -Value $contract.stale_label
    Set-ArtifactProperty -Artifact $artifact -Name "authoritative_for_liveness" -Value $false
    Set-ArtifactProperty -Artifact $artifact -Name "stale_reason" -Value $Reason
    Set-ArtifactProperty -Artifact $artifact -Name "stale_marked_ts_utc" -Value $nowUtc.ToString("o")
    Write-JsonArtifact -Path $Path -Artifact $artifact
    return [ordered]@{
        surface = Split-Path -Leaf $Path
        path = $Path
        prior_state = $priorTruthState
        new_state = "stale"
        emitted_ts_utc = if ($freshness.emitted_ts_utc) { $freshness.emitted_ts_utc } else { $artifact.emitted_ts_utc }
        expiry_ts_utc = if ($freshness.expires_ts_utc) { $freshness.expires_ts_utc } else { $nowUtc.ToString("o") }
        observed_demotion_ts_utc = $nowUtc.ToString("o")
        reason = $Reason
    }
}

function Set-StateKeyValue {
    param(
        [Parameter(Mandatory = $true)][System.Collections.IList]$Lines,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Value,
        [AllowEmptyString()][string]$InsertAfterKey = ""
    )
    $replacement = if ($Value -eq "") { "{0}:" -f $Key } else { "{0}: {1}" -f $Key, $Value }
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i].StartsWith("${Key}:")) {
            $Lines[$i] = $replacement
            return
        }
    }
    $insertIndex = $Lines.Count
    if ($InsertAfterKey) {
        for ($i = 0; $i -lt $Lines.Count; $i++) {
            if ($Lines[$i].StartsWith("${InsertAfterKey}:")) {
                $insertIndex = $i + 1
                break
            }
        }
    }
    $Lines.Insert($insertIndex, $replacement)
}

function Update-StateRuntimeBlock {
    param(
        [Parameter(Mandatory = $true)][string]$StatePath,
        [Parameter(Mandatory = $true)][hashtable]$Values
    )
    if (-not (Test-Path -LiteralPath $StatePath -PathType Leaf)) {
        throw "STATE.md not found: $StatePath"
    }
    $lines = [System.Collections.ArrayList]::new()
    foreach ($line in (Get-Content -LiteralPath $StatePath -Encoding UTF8)) {
        [void]$lines.Add([string]$line)
    }
    Set-StateKeyValue -Lines $lines -Key "heartbeat_ts" -Value $Values.heartbeat_ts -InsertAfterKey "Status"
    Set-StateKeyValue -Lines $lines -Key "health" -Value $Values.health -InsertAfterKey "heartbeat_ts"
    Set-StateKeyValue -Lines $lines -Key "health_ts" -Value $Values.health_ts -InsertAfterKey "health"
    Set-StateKeyValue -Lines $lines -Key "entropy_tier" -Value $Values.entropy_tier -InsertAfterKey "health_ts"
    Set-StateKeyValue -Lines $lines -Key "navigator_interval" -Value $Values.navigator_interval -InsertAfterKey "entropy_tier"
    Set-StateKeyValue -Lines $lines -Key "triage_status" -Value $Values.triage_status -InsertAfterKey "navigator_interval"
    Set-StateKeyValue -Lines $lines -Key "cpu_target" -Value $Values.cpu_target -InsertAfterKey "triage_status"
    Set-StateKeyValue -Lines $lines -Key "runtime_truth_state" -Value $Values.runtime_truth_state -InsertAfterKey "cpu_target"
    Set-StateKeyValue -Lines $lines -Key "runtime_truth_expires_ts" -Value $Values.runtime_truth_expires_ts -InsertAfterKey "runtime_truth_state"
    Set-StateKeyValue -Lines $lines -Key "runtime_truth_label" -Value $Values.runtime_truth_label -InsertAfterKey "runtime_truth_expires_ts"
    Set-StateKeyValue -Lines $lines -Key "runtime_truth_canonical" -Value $Values.runtime_truth_canonical -InsertAfterKey "runtime_truth_label"
    Set-StateKeyValue -Lines $lines -Key "checks" -Value $Values.checks -InsertAfterKey "lock"
    Set-StateKeyValue -Lines $lines -Key "failure_flags_active" -Value $Values.failure_flags_active -InsertAfterKey "checks"
    Set-StateKeyValue -Lines $lines -Key "failure_change_lane" -Value $Values.failure_change_lane -InsertAfterKey "failure_flags_active"
    Set-StateKeyValue -Lines $lines -Key "failure_risk_lane" -Value $Values.failure_risk_lane -InsertAfterKey "failure_change_lane"
    Set-StateKeyValue -Lines $lines -Key "failure_flag_services" -Value $Values.failure_flag_services -InsertAfterKey "failure_risk_lane"
    Set-StateKeyValue -Lines $lines -Key "runtime_topology_ts" -Value $Values.runtime_topology_ts -InsertAfterKey "failure_flag_services"
    Set-StateKeyValue -Lines $lines -Key "runtime_topology_truth_state" -Value $Values.runtime_topology_truth_state -InsertAfterKey "runtime_topology_ts"
    Set-StateKeyValue -Lines $lines -Key "runtime_topology_risk" -Value $Values.runtime_topology_risk -InsertAfterKey "runtime_topology_truth_state"
    Set-StateKeyValue -Lines $lines -Key "runtime_topology_active_services" -Value $Values.runtime_topology_active_services -InsertAfterKey "runtime_topology_risk"
    Set-StateKeyValue -Lines $lines -Key "runtime_topology_duplicates" -Value $Values.runtime_topology_duplicates -InsertAfterKey "runtime_topology_active_services"
    Set-StateKeyValue -Lines $lines -Key "runtime_topology_authority_ambiguous" -Value $Values.runtime_topology_authority_ambiguous -InsertAfterKey "runtime_topology_duplicates"
    Set-StateKeyValue -Lines $lines -Key "runtime_topology_flagged_services" -Value $Values.runtime_topology_flagged_services -InsertAfterKey "runtime_topology_authority_ambiguous"
    $payload = [string[]]$lines.ToArray()
    for ($attempt = 1; $attempt -le 6; $attempt++) {
        try {
            [System.IO.File]::WriteAllLines($StatePath, $payload, [System.Text.UTF8Encoding]::new($false))
            return
        } catch {
            if ($attempt -ge 6) { throw }
            Start-Sleep -Milliseconds 200
        }
    }
}

function Get-StateRuntimeHeartbeatTs {
    param([Parameter(Mandatory = $true)][string]$StatePath)
    if (-not (Test-Path -LiteralPath $StatePath -PathType Leaf)) { return "" }
    foreach ($line in (Get-Content -LiteralPath $StatePath -Encoding UTF8)) {
        if ($line.StartsWith("heartbeat_ts:")) {
            return ($line.Substring("heartbeat_ts:".Length)).Trim()
        }
    }
    return ""
}

function Set-StateRuntimeObservedStale {
    param(
        [Parameter(Mandatory = $true)][string]$StatePath,
        [Parameter(Mandatory = $true)][string]$Reason,
        [datetime]$ObservedAtUtc = [datetime]::UtcNow,
        [AllowNull()][object]$ExistingStateArtifact
    )
    if (-not (Test-Path -LiteralPath $StatePath -PathType Leaf)) { return $null }
    $stateArtifact = if ($ExistingStateArtifact) { $ExistingStateArtifact } else { Read-StateRuntimeBlock -StatePath $StatePath }
    if (-not $stateArtifact) {
        $stateArtifact = [pscustomobject]@{}
    }
    $freshness = Get-ArtifactFreshness -ContractName "state_runtime" -Artifact $stateArtifact -Path $StatePath -NowUtc $ObservedAtUtc
    $priorTruthState = Get-ArtifactCurrentTruthState -Artifact $stateArtifact -Freshness $freshness
    $contract = Get-RuntimeTruthContract -Name "state_runtime"
    Update-StateRuntimeBlock -StatePath $StatePath -Values @{
        heartbeat_ts = if ($stateArtifact.heartbeat_ts) { [string]$stateArtifact.heartbeat_ts } elseif ($freshness.emitted_ts_utc) { [string]$freshness.emitted_ts_utc } else { $ObservedAtUtc.ToString("o") }
        health = if ($stateArtifact.health) { [string]$stateArtifact.health } else { "unknown" }
        health_ts = if ($stateArtifact.health_ts) { [string]$stateArtifact.health_ts } else { "" }
        entropy_tier = if ($stateArtifact.entropy_tier) { [string]$stateArtifact.entropy_tier } else { "unknown" }
        navigator_interval = if ($stateArtifact.navigator_interval) { [string]$stateArtifact.navigator_interval } else { "unknown" }
        triage_status = if ($stateArtifact.triage_status) { [string]$stateArtifact.triage_status } else { "unknown" }
        cpu_target = if ($stateArtifact.cpu_target) { [string]$stateArtifact.cpu_target } else { "unknown" }
        runtime_truth_state = "stale"
        runtime_truth_expires_ts = $ObservedAtUtc.ToString("o")
        runtime_truth_label = $contract.stale_label
        runtime_truth_canonical = ("live_probes ({0})" -f $Reason)
        checks = if ($stateArtifact.checks) { [string]$stateArtifact.checks } else { "dev_harness=fail,cbo_core=fail,avatar_web=fail,telemetry_gateway=fail" }
        failure_flags_active = if ($stateArtifact.failure_flags_active) { [string]$stateArtifact.failure_flags_active } else { "0" }
        failure_change_lane = if ($stateArtifact.failure_change_lane) { [string]$stateArtifact.failure_change_lane } else { "clear" }
        failure_risk_lane = if ($stateArtifact.failure_risk_lane) { [string]$stateArtifact.failure_risk_lane } else { "clear" }
        failure_flag_services = if ($stateArtifact.failure_flag_services) { [string]$stateArtifact.failure_flag_services } else { "" }
        runtime_topology_ts = if ($stateArtifact.runtime_topology_ts) { [string]$stateArtifact.runtime_topology_ts } else { "" }
        runtime_topology_truth_state = "stale"
        runtime_topology_risk = if ($stateArtifact.runtime_topology_risk) { [string]$stateArtifact.runtime_topology_risk } else { "unknown" }
        runtime_topology_active_services = if ($stateArtifact.runtime_topology_active_services) { [string]$stateArtifact.runtime_topology_active_services } else { "none" }
        runtime_topology_duplicates = if ($stateArtifact.runtime_topology_duplicates) { [string]$stateArtifact.runtime_topology_duplicates } else { "none" }
        runtime_topology_authority_ambiguous = if ($stateArtifact.runtime_topology_authority_ambiguous) { [string]$stateArtifact.runtime_topology_authority_ambiguous } else { "none" }
        runtime_topology_flagged_services = if ($stateArtifact.runtime_topology_flagged_services) { [string]$stateArtifact.runtime_topology_flagged_services } else { "none" }
    }
    return [ordered]@{
        surface = "STATE.md"
        path = $StatePath
        prior_state = $priorTruthState
        new_state = "stale"
        emitted_ts_utc = if ($freshness.emitted_ts_utc) { $freshness.emitted_ts_utc } else { $ObservedAtUtc.ToString("o") }
        expiry_ts_utc = if ($freshness.expires_ts_utc) { $freshness.expires_ts_utc } else { $ObservedAtUtc.ToString("o") }
        observed_demotion_ts_utc = $ObservedAtUtc.ToString("o")
        reason = $Reason
    }
}

function Set-StateRuntimeStale {
    param(
        [Parameter(Mandatory = $true)][string]$StatePath,
        [Parameter(Mandatory = $true)][string]$Checks,
        [string]$Health = "unknown",
        [string]$HealthTs = "",
        [string]$EntropyTier = "unknown",
        [string]$NavigatorInterval = "unknown",
        [string]$TriageStatus = "unknown",
        [string]$CpuTarget = "unknown",
        [string]$Reason = "stale"
    )
    $contract = Get-RuntimeTruthContract -Name "state_runtime"
    $nowUtc = [datetime]::UtcNow
    Update-StateRuntimeBlock -StatePath $StatePath -Values @{
        heartbeat_ts = $nowUtc.ToString("o")
        health = $Health
        health_ts = $HealthTs
        entropy_tier = $EntropyTier
        navigator_interval = $NavigatorInterval
        triage_status = $TriageStatus
        cpu_target = $CpuTarget
        runtime_truth_state = "stale"
        runtime_truth_expires_ts = $nowUtc.ToString("o")
        runtime_truth_label = $contract.stale_label
        runtime_truth_canonical = ("live_probes ({0})" -f $Reason)
        checks = $Checks
        failure_flags_active = "0"
        failure_change_lane = "clear"
        failure_risk_lane = "clear"
        failure_flag_services = ""
        runtime_topology_ts = ""
        runtime_topology_truth_state = "stale"
        runtime_topology_risk = "unknown"
        runtime_topology_active_services = "none"
        runtime_topology_duplicates = "none"
        runtime_topology_authority_ambiguous = "none"
        runtime_topology_flagged_services = "none"
    }
}

function Get-DerivedTruthSurfaceTable {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    return @(
        @{ path = (Join-Path $RepoRoot "STATE.md"); contract = "state_runtime"; surface = "STATE.md"; kind = "state" },
        @{ path = (Join-Path $RepoRoot "runtime\station_heartbeat.json"); contract = "station_heartbeat"; surface = "station_heartbeat.json"; kind = "json" },
        @{ path = (Join-Path $RepoRoot "runtime\service_runtime_snapshot.json"); contract = "service_runtime_snapshot"; surface = "service_runtime_snapshot.json"; kind = "json" },
        @{ path = (Join-Path $RepoRoot "runtime\runtime_topology_snapshot.json"); contract = "runtime_topology_snapshot"; surface = "runtime_topology_snapshot.json"; kind = "json" }
    )
}

function Get-DerivedTruthSurfaceObservations {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [datetime]$NowUtc = [datetime]::UtcNow
    )
    $rows = @()
    foreach ($surfaceInfo in (Get-DerivedTruthSurfaceTable -RepoRoot $RepoRoot)) {
        $artifact = if ($surfaceInfo.kind -eq "state") {
            Read-StateRuntimeBlock -StatePath $surfaceInfo.path
        } else {
            Read-JsonArtifact -Path $surfaceInfo.path
        }
        $freshness = Get-ArtifactFreshness -ContractName $surfaceInfo.contract -Artifact $artifact -Path $surfaceInfo.path -NowUtc $NowUtc
        $rows += [pscustomobject]@{
            surface = $surfaceInfo.surface
            path = $surfaceInfo.path
            contract = $surfaceInfo.contract
            kind = $surfaceInfo.kind
            artifact = $artifact
            freshness = [pscustomobject]$freshness
            prior_state = Get-ArtifactCurrentTruthState -Artifact $artifact -Freshness $freshness
        }
    }
    return $rows
}

function Invoke-DerivedTruthExpirySweep {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [datetime]$NowUtc = [datetime]::UtcNow,
        [int]$RecentRefreshGraceSec = 10
    )
    $observations = @(Get-DerivedTruthSurfaceObservations -RepoRoot $RepoRoot -NowUtc $NowUtc)
    if ($observations.Count -eq 0) { return @() }

    $refreshRecentlyObserved = $false
    foreach ($obs in $observations) {
        if ($obs.prior_state -eq "stale") { continue }
        $emittedAt = ConvertTo-UtcDateTime -Value $obs.freshness.emitted_ts_utc
        if ($emittedAt -and ($NowUtc - $emittedAt).TotalSeconds -le $RecentRefreshGraceSec) {
            $refreshRecentlyObserved = $true
            break
        }
    }
    if ($refreshRecentlyObserved) { return @() }

    $expiredFresh = @($observations | Where-Object { (-not $_.freshness.is_fresh) -and $_.prior_state -ne "stale" })
    if ($expiredFresh.Count -eq 0) { return @() }

    $transitions = @()
    foreach ($obs in $observations) {
        if ($obs.prior_state -eq "stale") { continue }
        $transition = if ($obs.kind -eq "state") {
            Set-StateRuntimeObservedStale -StatePath $obs.path -Reason "ttl_expired" -ObservedAtUtc $NowUtc -ExistingStateArtifact $obs.artifact
        } else {
            Set-JsonArtifactStale -Path $obs.path -ContractName $obs.contract -Reason "ttl_expired" -ObservedAtUtc $NowUtc
        }
        if ($transition) {
            $transitions += $transition
        }
    }
    if ($transitions.Count -gt 0) {
        Write-DerivedTruthTransitionReceipt -RepoRoot $RepoRoot -Transition "fresh_to_stale" -Reason "ttl_expired" -SurfaceTransitions $transitions -ObservedAtUtc $NowUtc | Out-Null
    }
    return $transitions
}

function Get-AdvisoryArtifactTable {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    return @(
        @{ path = (Join-Path $RepoRoot "outgoing\navigator.lock"); contract = "navigator"; surface = "navigator.lock" },
        @{ path = (Join-Path $RepoRoot "outgoing\triage.lock"); contract = "triage"; surface = "triage.lock" },
        @{ path = (Join-Path $RepoRoot "outgoing\cp6.lock"); contract = "cp6"; surface = "cp6.lock" },
        @{ path = (Join-Path $RepoRoot "outgoing\cp7.lock"); contract = "cp7"; surface = "cp7.lock" },
        @{ path = (Join-Path $RepoRoot "outgoing\cp9.lock"); contract = "cp9"; surface = "cp9.lock" }
    )
}

function Invoke-RuntimeTruthRecovery {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $recovered = @()
    $artifacts = @(
        @{ path = (Join-Path $RepoRoot "runtime\station_health.json"); contract = "station_health"; surface = "station_health.json" },
        @{ path = (Join-Path $RepoRoot "runtime\station_heartbeat.json"); contract = "station_heartbeat"; surface = "station_heartbeat.json" },
        @{ path = (Join-Path $RepoRoot "runtime\service_runtime_snapshot.json"); contract = "service_runtime_snapshot"; surface = "service_runtime_snapshot.json" },
        @{ path = (Join-Path $RepoRoot "runtime\runtime_topology_snapshot.json"); contract = "runtime_topology_snapshot"; surface = "runtime_topology_snapshot.json" }
    ) + (Get-AdvisoryArtifactTable -RepoRoot $RepoRoot)
    foreach ($artifactInfo in $artifacts) {
        if (-not (Test-Path -LiteralPath $artifactInfo.path -PathType Leaf)) { continue }
        $artifact = Read-JsonArtifact -Path $artifactInfo.path
        $freshness = Get-ArtifactFreshness -ContractName $artifactInfo.contract -Artifact $artifact -Path $artifactInfo.path
        $currentTruthState = ""
        if ($artifact) {
            $prop = $artifact.PSObject.Properties["truth_state"]
            if ($prop -and $prop.Value) { $currentTruthState = [string]$prop.Value }
        }
        if (-not $freshness.is_fresh -and $currentTruthState -ne "stale") {
            Set-JsonArtifactStale -Path $artifactInfo.path -ContractName $artifactInfo.contract -Reason "abnormal_termination_recovery" | Out-Null
            $recovered += [ordered]@{
                surface = $artifactInfo.surface
                path = $artifactInfo.path
                prior_truth_state = if ($currentTruthState) { $currentTruthState } else { "unlabeled" }
                stale_label = (Get-RuntimeTruthContract -Name $artifactInfo.contract).stale_label
            }
        }
    }
    if ($recovered.Count -gt 0) {
        $statePath = Join-Path $RepoRoot "STATE.md"
        if (Test-Path -LiteralPath $statePath -PathType Leaf) {
            $currentChecks = "dev_harness=fail,cbo_core=fail,avatar_web=fail,telemetry_gateway=fail"
            Set-StateRuntimeStale -StatePath $statePath -Checks $currentChecks -Reason "abnormal_termination_recovery"
        }
        $receipt = [ordered]@{
            schema = "station.runtime_truth_recovery.v1"
            ts_utc = Get-UtcNowString
            recovered_surfaces = $recovered
        }
        Write-RuntimeTruthReceipt -RepoRoot $RepoRoot -RelativeDir "runtime\receipts\audit" -Prefix "runtime_truth_recovery" -Payload $receipt | Out-Null
    }
    return ,$recovered
}

function Write-RuntimeTruthTransition {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$Transition,
        [Parameter(Mandatory = $true)][string]$Reason,
        [string[]]$Surfaces = @(),
        [hashtable]$Extra = @{}
    )
    $payload = [ordered]@{
        schema = "station.runtime_truth_transition.v1"
        ts_utc = Get-UtcNowString
        transition = $Transition
        reason = $Reason
        surfaces = $Surfaces
    }
    foreach ($key in $Extra.Keys) {
        $payload[$key] = $Extra[$key]
    }
    return Write-RuntimeTruthReceipt -RepoRoot $RepoRoot -RelativeDir "runtime\receipts\security" -Prefix "runtime_truth_transition" -Payload $payload
}
