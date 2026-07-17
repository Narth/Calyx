# Navigator (Traffic Navigator) — control/cadence modulation; hot/cool intervals and pause control.
# Uses minimal sunrise context: reads STATE, patch_readiness, entropy. No service startup.
# Usage: .\Scripts\navigator.ps1
# Exit: 0 = hot (proceed), 1 = pause (block), 2 = cool (caution)
# Artifact: outgoing/navigator.lock
# See: docs/operations/NAVIGATOR_TRIAGE_MINIMAL_SUNRISE.md, COMPENDIUM.md

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) {
    $repoRoot = (Get-Location).Path
}

$truthHelper = Join-Path $repoRoot "Scripts\runtime_truth_contract.ps1"
if (-not (Test-Path $truthHelper)) {
    throw "runtime_truth_contract.ps1 not found: $truthHelper"
}
. $truthHelper

$outgoingDir = Join-Path $repoRoot "outgoing"
$lockPath = Join-Path $outgoingDir "navigator.lock"
if (-not (Test-Path $outgoingDir)) {
    New-Item -ItemType Directory -Path $outgoingDir -Force | Out-Null
}

function Write-NavigatorLock {
    param([hashtable]$Payload)
    $nowUtc = [datetime]::UtcNow
    $Payload.ts = $nowUtc.ToString("o")
    $Payload.ts_utc = $Payload.ts
    Add-TruthMetadataToArtifact -Artifact $Payload -ContractName "navigator" -EmittedAtUtc $nowUtc
    Write-JsonArtifact -Path $lockPath -Artifact $Payload
}

# Correlation log (correlation != causation)
$corrScript = Join-Path $repoRoot "Scripts\correlation_log.ps1"
if (Test-Path $corrScript) { & $corrScript -Component "navigator" -Event "run" 2>$null }

# 1. Patch readiness gate
$patchReadiness = Join-Path $repoRoot "Scripts\patch_readiness.ps1"
if (-not (Test-Path $patchReadiness)) {
    $obj = [ordered]@{
        interval_status = "pause"
        entropy_tier = "unknown"
        health = "unknown"
        recommendation = "patch_readiness.ps1 not found; defer."
        exit_code = 1
    }
    Write-NavigatorLock -Payload $obj
    Write-Host "Navigator> PAUSE (patch_readiness not found)" -ForegroundColor Red
    exit 1
}

& $patchReadiness > $null 2>&1
$ready = $LASTEXITCODE -eq 0

if (-not $ready) {
    $obj = [ordered]@{
        interval_status = "pause"
        entropy_tier = "unacceptable_or_fail"
        health = "fail_or_unacceptable"
        cadence_70 = $null
        cadence_55 = $null
        safe_travels_zone = $false
        cpu_target = "unknown"
        carbon_intensity_g_co2eq_per_kwh = $null
        power_window = $null
        recommendation = "Defer. Resolve entropy or health; re-run patch_readiness."
        exit_code = 1
    }
    Write-NavigatorLock -Payload $obj
    Write-Host "Navigator> PAUSE (patch_readiness deferred)" -ForegroundColor Red
    exit 1
}

# 2. Read carbon intensity (optional; Electricity Maps)
$carbonPath = Join-Path $repoRoot "runtime\carbon_intensity.json"
$carbonG = $null
$powerWindow = $null
if (Test-Path -LiteralPath $carbonPath -PathType Leaf) {
    try {
        $cjson = Get-Content -LiteralPath $carbonPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($cjson.carbon_intensity_g_co2eq_per_kwh) { $carbonG = [int]$cjson.carbon_intensity_g_co2eq_per_kwh }
        if ($cjson.power_window) { $powerWindow = $cjson.power_window }
    } catch { }
}

# 3. Read STATE / station_health for tier and cadence
$healthPath = Join-Path $repoRoot "runtime\station_health.json"
$entropyTier = "unknown"
$health = "unknown"
$cadence70 = 0
$cadence55 = 0
$safeTravelsZone = $false
$cpuTarget = "unknown"
$healthFresh = $false

if (Test-Path -LiteralPath $healthPath -PathType Leaf) {
    try {
        $json = Get-Content -LiteralPath $healthPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $freshness = Get-ArtifactFreshness -ContractName "station_health" -Artifact $json -Path $healthPath
        if ($freshness.is_fresh) {
            $healthFresh = $true
            if ($json.entropy -and $json.entropy.tier) { $entropyTier = $json.entropy.tier }
            if ($json.health) { $health = $json.health }
            if ($json.entropy -and $null -ne $json.entropy.cadence_70) { $cadence70 = [int]$json.entropy.cadence_70 }
            if ($json.entropy -and $null -ne $json.entropy.cadence_55) { $cadence55 = [int]$json.entropy.cadence_55 }
            if ($json.entropy -and $null -ne $json.entropy.safe_travels_zone) { $safeTravelsZone = [bool]$json.entropy.safe_travels_zone }
            if ($json.entropy -and $json.entropy.cpu_target) { $cpuTarget = $json.entropy.cpu_target }
        }
    } catch { }
}

# 4. Determine interval. Safe Travels: 50% target. Under = hot (allow ML). Over = cool/pause.
$intervalStatus = "hot"
$recommendation = "Safe Travels: under target; allow ML to reach 50%."
$exitCode = 0

if (-not $healthFresh) {
    $intervalStatus = "cool"
    $recommendation = "Fresh station_health unavailable; advisory confidence reduced. Proceed with caution."
    $exitCode = 2
} elseif ($entropyTier -eq "unacceptable" -or $health -eq "fail" -or $cadence70 -gt 10) {
    $intervalStatus = "pause"
    $recommendation = if ($cadence70 -gt 10) { "Cadence_70=$cadence70 (repeatedly maxing). Cooldown required." } else { "Do not add load. Resolve entropy or health." }
    $exitCode = 1
} elseif ($entropyTier -eq "high" -or $health -eq "warn") {
    $intervalStatus = "cool"
    $recommendation = "Over 50% target; hold back. Preserve hardware."
    $exitCode = 2
} elseif ($safeTravelsZone -or $cpuTarget -eq "safe_travels") {
    $recommendation = "Safe Travels: in zone (40-60%). Ideal."
} elseif ($cpuTarget -eq "under") {
    $recommendation = "Safe Travels: under target; commit more to ML."
}

# 5. Write lock
$obj = [ordered]@{
    interval_status = $intervalStatus
    entropy_tier = $entropyTier
    health = $health
    cadence_70 = $cadence70
    cadence_55 = $cadence55
    safe_travels_zone = $safeTravelsZone
    cpu_target = $cpuTarget
    carbon_intensity_g_co2eq_per_kwh = $carbonG
    power_window = $powerWindow
    health_source_fresh = $healthFresh
    recommendation = $recommendation
    exit_code = $exitCode
}

Write-NavigatorLock -Payload $obj

$carbonStr = if ($carbonG) { " carbon=$carbonG g/kWh ($powerWindow)" } else { "" }
$targetStr = if ($cpuTarget -ne "unknown") { " cpu_target=$cpuTarget" } else { "" }
Write-Host "Navigator> $($intervalStatus.ToUpper()) entropy_tier=$entropyTier health=$health cadence_70=$cadence70$targetStr$carbonStr" -ForegroundColor $(if ($intervalStatus -eq "hot") { "Green" } elseif ($intervalStatus -eq "cool") { "Yellow" } else { "Red" })
Write-Host "  $recommendation"
exit $exitCode
