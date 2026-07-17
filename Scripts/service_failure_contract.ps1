$ErrorActionPreference = "Stop"

function Get-ServiceFailureRegistry {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $path = Join-Path $RepoRoot "policy\service_failure_registry.json"
    if (-not (Test-Path $path)) {
        throw "service_failure_registry.json not found: $path"
    }
    return Get-Content -Path $path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Get-ServiceFailureStatePath {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    return Join-Path $RepoRoot "runtime\service_failure_detector_state.json"
}

function Get-ServiceFailureStatusPath {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    return Join-Path $RepoRoot "runtime\service_failure_status.json"
}

function Read-ServiceFailureDetectorState {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $path = Get-ServiceFailureStatePath -RepoRoot $RepoRoot
    if (-not (Test-Path $path)) {
        return [ordered]@{
            schema = "station.service_failure_detector_state.v1"
            services = [ordered]@{}
            active_flags = [ordered]@{}
        }
    }
    try {
        return Get-Content -Path $path -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return [ordered]@{
            schema = "station.service_failure_detector_state.v1"
            services = [ordered]@{}
            active_flags = [ordered]@{}
        }
    }
}

function ConvertTo-ServiceFailureMap {
    param([AllowNull()][object]$Value)
    $map = [ordered]@{}
    if ($null -eq $Value) { return $map }
    if ($Value -is [System.Collections.IDictionary]) {
        foreach ($key in $Value.Keys) {
            $map[[string]$key] = $Value[$key]
        }
        return $map
    }
    foreach ($prop in $Value.PSObject.Properties) {
        $map[[string]$prop.Name] = $prop.Value
    }
    return $map
}

function Test-ServiceFailurePort {
    param(
        [string]$TargetHost,
        [int]$Port,
        [int]$TimeoutMs = 1500
    )
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $ar = $client.BeginConnect($TargetHost, $Port, $null, $null)
        $ok = $ar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
        if ($ok) {
            $client.EndConnect($ar)
            return @{ observed_ok = $true; detection_source = "port_probe"; evidence = @{ host = $TargetHost; port = $Port } }
        }
    } catch { }
    finally {
        try { $client.Close() } catch { }
        try { $client.Dispose() } catch { }
    }
    return @{ observed_ok = $false; detection_source = "port_probe"; evidence = @{ host = $TargetHost; port = $Port } }
}

function Test-ServiceFailureProcessPattern {
    param([string]$Pattern)
    $matches = @()
    try {
        $matches = Get-Process python,powershell -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
                if ($cmd -and $cmd -match $Pattern) {
                    [ordered]@{
                        pid = $_.Id
                        process_name = $_.ProcessName
                    }
                }
            } catch { }
        } | Where-Object { $_ }
    } catch { }
    return @{
        observed_ok = ($matches.Count -gt 0)
        detection_source = "process_pattern"
        evidence = @{ pattern = $Pattern; matches = @($matches | Select-Object -First 5) }
    }
}

function Get-ServiceFailureSummary {
    param([System.Collections.IList]$ActiveFlags)
    if (-not $ActiveFlags -or $ActiveFlags.Count -eq 0) {
        return [ordered]@{
            active_count = 0
            services = @()
            failure_change_lane = "clear"
            failure_risk_lane = "clear"
            highest_severity_class = ""
        }
    }
    $services = @($ActiveFlags | ForEach-Object { [string]$_.service })
    $highest = "CLASS_1_OBSERVE"
    foreach ($flag in $ActiveFlags) {
        $candidate = [string]$flag.severity_class
        if ($candidate -eq "CLASS_3_FULL_SUNRISE_CANDIDATE") { $highest = $candidate; break }
        if ($candidate -eq "CLASS_2_SCOPED_RECOVERY_CANDIDATE") { $highest = $candidate }
    }
    $risk = switch ($highest) {
        "CLASS_3_FULL_SUNRISE_CANDIDATE" { "full_sunrise_candidate" }
        "CLASS_2_SCOPED_RECOVERY_CANDIDATE" { "scoped_recovery_candidate" }
        default { "observe" }
    }
    return [ordered]@{
        active_count = $ActiveFlags.Count
        services = $services
        failure_change_lane = "service_failure_active"
        failure_risk_lane = $risk
        highest_severity_class = $highest
    }
}

function Write-ServiceFailureReceipt {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$Prefix,
        [Parameter(Mandatory = $true)][hashtable]$Payload
    )
    $receiptDir = Join-Path $RepoRoot "runtime\receipts\security"
    if (-not (Test-Path $receiptDir)) {
        New-Item -ItemType Directory -Path $receiptDir -Force | Out-Null
    }
    $stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss_fff")
    $path = Join-Path $receiptDir "${Prefix}__${stamp}.json"
    $Payload | ConvertTo-Json -Depth 8 | Set-Content -Path $path -Encoding UTF8
    return $path
}

function Invoke-ServiceFailureScan {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [switch]$EmitReceipts = $true
    )
    $registry = Get-ServiceFailureRegistry -RepoRoot $RepoRoot
    $state = Read-ServiceFailureDetectorState -RepoRoot $RepoRoot
    $serviceState = ConvertTo-ServiceFailureMap -Value $state.services
    $activeFlags = ConvertTo-ServiceFailureMap -Value $state.active_flags
    $nowUtc = [datetime]::UtcNow
    $stateChanged = $false
    $newActiveFlags = [ordered]@{}

    foreach ($svc in $registry.services) {
        $name = [string]$svc.service
        if ($null -ne $svc.enabled -and -not [bool]$svc.enabled) {
            if ($activeFlags.Contains($name)) {
                $activeFlags.Remove($name)
                $stateChanged = $true
            }
            $serviceState[$name] = [ordered]@{
                consecutive_failures = 0
                consecutive_successes = 0
                last_probe_ts_utc = $nowUtc.ToString("o")
                last_probe_ok = $true
                detection_source = "registry_disabled"
                evidence = @{
                    registry_enabled = $false
                    disposition = "quarantined_noncanonical_not_expected_resident"
                }
            }
            continue
        }
        $detection = $svc.detection
        $probe = switch ([string]$detection.kind) {
            "port" { Test-ServiceFailurePort -TargetHost ([string]$detection.host) -Port ([int]$detection.port) }
            "process_pattern" { Test-ServiceFailureProcessPattern -Pattern ([string]$detection.pattern) }
            default { @{ observed_ok = $false; detection_source = "unsupported"; evidence = @{ kind = [string]$detection.kind } } }
        }

        $entry = if ($serviceState.Contains($name)) { $serviceState[$name] } else { [ordered]@{ consecutive_failures = 0; consecutive_successes = 0 } }
        $failCount = 0
        $successCount = 0
        try { $failCount = [int]$entry.consecutive_failures } catch { }
        try { $successCount = [int]$entry.consecutive_successes } catch { }

        if ($probe.observed_ok) {
            $successCount += 1
            $failCount = 0
        } else {
            $failCount += 1
            $successCount = 0
        }

        $entry = [ordered]@{
            consecutive_failures = $failCount
            consecutive_successes = $successCount
            last_probe_ts_utc = $nowUtc.ToString("o")
            last_probe_ok = [bool]$probe.observed_ok
            detection_source = [string]$probe.detection_source
            evidence = $probe.evidence
        }
        $serviceState[$name] = $entry

        $wasActive = $activeFlags.Contains($name)
        $failThreshold = [int]$detection.fail_threshold
        $clearThreshold = [int]$detection.clear_threshold

        if ((-not $probe.observed_ok) -and $failCount -ge $failThreshold) {
            if (-not $wasActive) {
                $flag = [ordered]@{
                    service = $name
                    tier = [string]$svc.tier
                    severity_class = [string]$svc.severity_class
                    failure_class = if ([string]$probe.detection_source -eq "port_probe") { "failed_probe_threshold" } else { "missing_process_threshold" }
                    detection_source = [string]$probe.detection_source
                    detected_ts_utc = $nowUtc.ToString("o")
                    evidence = $probe.evidence
                    evidence_reference = ""
                    current_liveness_authority = $false
                    change_lane_canonical = $true
                    risk_lane_canonical = $true
                }
                if ($EmitReceipts) {
                    $receiptPath = Write-ServiceFailureReceipt -RepoRoot $RepoRoot -Prefix "service_failure_flag" -Payload @{
                        schema = "station.service_failure_flag.v1"
                        ts_utc = $nowUtc.ToString("o")
                        service = $name
                        tier = [string]$svc.tier
                        severity_class = [string]$svc.severity_class
                        failure_class = $flag.failure_class
                        detection_source = [string]$probe.detection_source
                        evidence = $probe.evidence
                        current_liveness_authority = $false
                        change_lane_canonical = $true
                        risk_lane_canonical = $true
                    }
                    $flag.evidence_reference = $receiptPath
                }
                $activeFlags[$name] = $flag
                $stateChanged = $true
            }
        } elseif ($probe.observed_ok -and $wasActive -and $successCount -ge $clearThreshold) {
            $flag = $activeFlags[$name]
            if ($EmitReceipts) {
                Write-ServiceFailureReceipt -RepoRoot $RepoRoot -Prefix "service_failure_clear" -Payload @{
                    schema = "station.service_failure_clear.v1"
                    ts_utc = $nowUtc.ToString("o")
                    service = $name
                    prior_severity_class = [string]$flag.severity_class
                    detection_source = [string]$probe.detection_source
                    evidence = $probe.evidence
                    cleared_by = "independent_revalidation"
                } | Out-Null
            }
            $activeFlags.Remove($name)
            $stateChanged = $true
        }
    }

    foreach ($key in $activeFlags.Keys) {
        $newActiveFlags[$key] = $activeFlags[$key]
    }
    $summary = Get-ServiceFailureSummary -ActiveFlags @($newActiveFlags.Values)

    $status = [ordered]@{
        schema = "station.service_failure_status.v1"
        ts_utc = $nowUtc.ToString("o")
        active_flags = @($newActiveFlags.Values)
        summary = $summary
    }
    $statusPath = Get-ServiceFailureStatusPath -RepoRoot $RepoRoot
    $statePath = Get-ServiceFailureStatePath -RepoRoot $RepoRoot
    $status | ConvertTo-Json -Depth 8 | Set-Content -Path $statusPath -Encoding UTF8
    ([ordered]@{
        schema = "station.service_failure_detector_state.v1"
        ts_utc = $nowUtc.ToString("o")
        services = $serviceState
        active_flags = $newActiveFlags
    } | ConvertTo-Json -Depth 10) | Set-Content -Path $statePath -Encoding UTF8

    return [ordered]@{
        status_path = $statusPath
        state_path = $statePath
        state_changed = $stateChanged
        active_flags = @($newActiveFlags.Values)
        summary = $summary
    }
}
