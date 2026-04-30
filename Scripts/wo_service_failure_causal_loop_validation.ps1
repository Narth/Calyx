param()

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) { $repoRoot = (Get-Location).Path }
Set-Location $repoRoot

. (Join-Path $repoRoot "Scripts\service_failure_contract.ps1")

$updateScript = Join-Path $repoRoot "Scripts\update_state_checks.ps1"
$restartScript = Join-Path $repoRoot "Scripts\restart_service.ps1"
$statePath = Join-Path $repoRoot "STATE.md"
$heartbeatPath = Join-Path $repoRoot "runtime\station_heartbeat.json"
$snapshotPath = Join-Path $repoRoot "runtime\service_runtime_snapshot.json"
$receiptDir = Join-Path $repoRoot "runtime\receipts\audit"
if (-not (Test-Path $receiptDir)) {
    New-Item -ItemType Directory -Path $receiptDir -Force | Out-Null
}

function Invoke-DetectorScanPair {
    param([string]$RepoRoot)
    Invoke-ServiceFailureScan -RepoRoot $RepoRoot | Out-Null
    Start-Sleep -Seconds 1
    return Invoke-ServiceFailureScan -RepoRoot $RepoRoot
}

function Read-JsonFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Get-StateValue {
    param(
        [string]$Path,
        [string]$Key
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return "" }
    foreach ($line in (Get-Content -LiteralPath $Path -Encoding UTF8)) {
        if ($line.StartsWith("${Key}:")) {
            return ($line.Substring($Key.Length + 1)).Trim()
        }
    }
    return ""
}

function Stop-PortService {
    param([int]$Port)
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($conn -and $conn.OwningProcess) {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    } catch { }
    Start-Sleep -Seconds 2
}

function Stop-PowerShellLoop {
    param([string]$Pattern)
    try {
        Get-Process powershell -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
                if ($cmd -and $cmd -match $Pattern) {
                    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
                }
            } catch { }
        }
    } catch { }
    Start-Sleep -Seconds 2
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
    }) | Out-Null
}

$results = [System.Collections.Generic.List[object]]::new()
$cleanupNeeded = @{
    cbo_core = $false
    navigator_triage_loop = $false
}

try {
    $baseline = Invoke-DetectorScanPair -RepoRoot $repoRoot
    if (Test-Path $updateScript) { & $updateScript | Out-Null }
    Add-ValidationResult -Results $results -Name "baseline_clear" -Passed ($baseline.summary.active_count -eq 0) -Detail "Baseline active_count=$($baseline.summary.active_count)"

    Stop-PortService -Port 7778
    $cleanupNeeded.cbo_core = $true
    $coreFailure = Invoke-DetectorScanPair -RepoRoot $repoRoot
    if (Test-Path $updateScript) { & $updateScript | Out-Null }
    $coreFlag = @($coreFailure.active_flags | Where-Object { $_.service -eq "cbo_core" }) | Select-Object -First 1
    Add-ValidationResult -Results $results -Name "core_loss_detected" -Passed ([bool]$coreFlag) -Detail "Active services=$(@($coreFailure.summary.services) -join ',')"
    Add-ValidationResult -Results $results -Name "core_loss_classified_full_sunrise" -Passed ($coreFlag -and $coreFlag.severity_class -eq "CLASS_3_FULL_SUNRISE_CANDIDATE") -Detail "Severity=$($coreFlag.severity_class)"
    Add-ValidationResult -Results $results -Name "core_flag_not_liveness_authority" -Passed ($coreFlag -and -not [bool]$coreFlag.current_liveness_authority) -Detail "current_liveness_authority=$($coreFlag.current_liveness_authority)"
    Add-ValidationResult -Results $results -Name "state_overlay_core_failure" -Passed ((Get-StateValue -Path $statePath -Key "failure_risk_lane") -eq "full_sunrise_candidate") -Detail "STATE failure_risk_lane=$(Get-StateValue -Path $statePath -Key 'failure_risk_lane')"
    $heartbeatJson = Read-JsonFile -Path $heartbeatPath
    $snapshotJson = Read-JsonFile -Path $snapshotPath
    Add-ValidationResult -Results $results -Name "json_overlay_core_failure" -Passed (($heartbeatJson.service_failure_risk_lane -eq "full_sunrise_candidate") -and ($snapshotJson.service_failure_risk_lane -eq "full_sunrise_candidate")) -Detail "heartbeat=$($heartbeatJson.service_failure_risk_lane) snapshot=$($snapshotJson.service_failure_risk_lane)"

    & $restartScript -Service cbo_core | Out-Null
    $cleanupNeeded.cbo_core = $false
    Start-Sleep -Seconds 6
    $postCoreRestore = Invoke-DetectorScanPair -RepoRoot $repoRoot
    if (Test-Path $updateScript) { & $updateScript | Out-Null }
    Add-ValidationResult -Results $results -Name "core_loss_no_auto_action" -Passed (@($postCoreRestore.active_flags | Where-Object { $_.service -eq "cbo_core" }).Count -eq 0) -Detail "cbo_core active after governed restart=$(@($postCoreRestore.active_flags | Where-Object { $_.service -eq 'cbo_core' }).Count)"

    Stop-PowerShellLoop -Pattern "navigator_triage_loop\.ps1"
    $cleanupNeeded.navigator_triage_loop = $true
    $secondaryFailure = Invoke-DetectorScanPair -RepoRoot $repoRoot
    if (Test-Path $updateScript) { & $updateScript | Out-Null }
    $secondaryFlag = @($secondaryFailure.active_flags | Where-Object { $_.service -eq "navigator_triage_loop" }) | Select-Object -First 1
    Add-ValidationResult -Results $results -Name "secondary_loss_detected" -Passed ([bool]$secondaryFlag) -Detail "Active services=$(@($secondaryFailure.summary.services) -join ',')"
    Add-ValidationResult -Results $results -Name "secondary_loss_classified_scoped_recovery" -Passed ($secondaryFlag -and $secondaryFlag.severity_class -eq "CLASS_2_SCOPED_RECOVERY_CANDIDATE") -Detail "Severity=$($secondaryFlag.severity_class)"
    Add-ValidationResult -Results $results -Name "classification_differs_between_core_and_secondary" -Passed ($coreFlag -and $secondaryFlag -and ($coreFlag.severity_class -ne $secondaryFlag.severity_class)) -Detail "core=$($coreFlag.severity_class) secondary=$($secondaryFlag.severity_class)"
    Add-ValidationResult -Results $results -Name "secondary_flag_not_liveness_authority" -Passed ($secondaryFlag -and -not [bool]$secondaryFlag.current_liveness_authority) -Detail "current_liveness_authority=$($secondaryFlag.current_liveness_authority)"

    & $restartScript -Service navigator_triage_loop | Out-Null
    $cleanupNeeded.navigator_triage_loop = $false
    Start-Sleep -Seconds 6
    $finalClear = Invoke-DetectorScanPair -RepoRoot $repoRoot
    if (Test-Path $updateScript) { & $updateScript | Out-Null }
    Add-ValidationResult -Results $results -Name "final_clear_after_governed_restart" -Passed ($finalClear.summary.active_count -eq 0) -Detail "Final active_count=$($finalClear.summary.active_count)"
} finally {
    if ($cleanupNeeded.cbo_core) {
        try { & $restartScript -Service cbo_core | Out-Null } catch { }
    }
    if ($cleanupNeeded.navigator_triage_loop) {
        try { & $restartScript -Service navigator_triage_loop | Out-Null } catch { }
    }
    try {
        Invoke-DetectorScanPair -RepoRoot $repoRoot | Out-Null
        if (Test-Path $updateScript) { & $updateScript | Out-Null }
    } catch { }
}

$passed = (@($results | Where-Object { -not $_.passed }).Count -eq 0)
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss_fff")
$receiptPath = Join-Path $receiptDir "wo_service_failure_causal_loop_validation__${stamp}.json"
$receipt = [ordered]@{
    schema = "station.audit.wo_service_failure_causal_loop_validation.v1"
    wo_id = "WO_SERVICE_FAILURE_CAUSAL_LOOP_V1"
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    passed = $passed
    results = @($results)
}
$receipt | ConvertTo-Json -Depth 8 | Set-Content -Path $receiptPath -Encoding UTF8
Write-Output $receiptPath

if (-not $passed) {
    exit 1
}
