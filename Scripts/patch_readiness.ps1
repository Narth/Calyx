# Patch Readiness Gate — entropy-aware pre-check before patches and repairs.
# Reads station_health.json (or falls back to build_safety_check) and verifies entropy + health.
# Usage: .\Scripts\patch_readiness.ps1 [-Strict] [-RequireCoreServices]
# Exit: 0 = ready to patch, 1 = not ready (defer; reason printed).
# See: docs/operations/ENTROPY_AND_ENERGY_BASELINE.md

param(
    [switch]$Strict = $false,           # If set, require entropy_tier=pass (reject "high")
    [switch]$RequireCoreServices = $false
)

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

$runtimeDir = Join-Path $repoRoot "runtime"
$healthPath = Join-Path $runtimeDir "station_health.json"

function Get-LightCpuPct {
    try {
        $p = Get-CimInstance -ClassName Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'" -ErrorAction SilentlyContinue
        if ($p -and $null -ne $p.PercentProcessorTime) { [int]$p.PercentProcessorTime } else { $null }
    } catch { $null }
}

# Safe Travels: 50% target. Over 60 = high, over 75 = unacceptable (wider margins).
function Get-EntropyTierFromCpu {
    param([int]$cpu)
    if ($null -eq $cpu) { return "unknown" }
    if ($cpu -ge 75) { return "unacceptable" }
    if ($cpu -ge 60) { return "high" }
    return "pass"
}

# --- Main ---
$entropyTier = $null
$health = $null
$cadence70 = 0
$source = $null

# 1. Try station_health.json (from health loop)
if (Test-Path -LiteralPath $healthPath -PathType Leaf) {
    try {
        $json = Get-Content -LiteralPath $healthPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $freshness = Get-ArtifactFreshness -ContractName "station_health" -Artifact $json -Path $healthPath
        if ($freshness.is_fresh) {
            $entropyTier = if ($json.entropy -and $json.entropy.tier) { $json.entropy.tier } else { $null }
            $health = $json.health
            $cadence70 = if ($json.entropy -and $null -ne $json.entropy.cadence_70) { [int]$json.entropy.cadence_70 } else { 0 }
            $source = "station_health.json"
        }
    } catch { }
}

# 2. Fallback: quick WMI CPU + build_safety_check
if (-not $source) {
    $cpu = Get-LightCpuPct
    $entropyTier = Get-EntropyTierFromCpu $cpu

    $buildCheck = Join-Path $repoRoot "Scripts\build_safety_check.ps1"
    if (Test-Path $buildCheck) {
        $buildArgs = @()
        if ($RequireCoreServices) { $buildArgs += '-RequireCoreServices' }
        & $buildCheck @buildArgs > $null 2>&1
        $ec = $LASTEXITCODE
        $health = if ($ec -eq 0) { "pass" } elseif ($ec -eq 1) { "warn" } else { "fail" }
    } else {
        $health = if ($null -ne $cpu -and $cpu -ge 92) { "fail" } elseif ($null -ne $cpu -and $cpu -ge 75) { "warn" } else { "pass" }
    }
    $cadence70 = 0
    $source = "fallback"
}

# 3. Determine readiness
$ready = $true
$reason = @()

if ($health -eq "fail") {
    $ready = $false
    $reason += "health=fail"
}
if ($entropyTier -eq "unacceptable") {
    $ready = $false
    $reason += "entropy_tier=unacceptable (CPU >= 75%; defer)"
}
if ($Strict -and $entropyTier -eq "high") {
    $ready = $false
    $reason += "entropy_tier=high (Strict mode; CPU 60-75%)"
}
if ($entropyTier -eq "unknown" -and $health -ne "pass") {
    $ready = $false
    $reason += "entropy unknown and health not pass"
}
# Cadence gate: bulk/frequent 70%+ in last 60 samples = repeatedly maxing; no good for health cadence
if ($cadence70 -gt 10) {
    $ready = $false
    $reason += "cadence_70=$cadence70 (repeatedly maxing; defer until cooldown)"
}

if ($ready) {
    Write-Host "PATCH_READY entropy_tier=$entropyTier health=$health (source: $source)" -ForegroundColor Green
    exit 0
}

Write-Host "PATCH_DEFER $($reason -join '; ')" -ForegroundColor Red
Write-Host "  entropy_tier=$entropyTier health=$health (source: $source)" -ForegroundColor DarkGray
Write-Host "  Resolve load or wait for entropy_tier=pass and health!=fail. Re-run patch_readiness.ps1." -ForegroundColor Yellow
exit 1
