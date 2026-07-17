# Triage Orchestrator — probing health/latency/errors, tightening stability.
# Uses minimal sunrise context: reads station_health, patch_readiness. Probes CBO Core if reachable.
# Usage: .\Scripts\triage_orchestrator.ps1
# Exit: 0 = pass, 1 = warn, 2 = fail
# Artifact: outgoing/triage.lock
# See: docs/operations/NAVIGATOR_TRIAGE_MINIMAL_SUNRISE.md, COMPENDIUM.md, docs/TRIAGE.md

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
$lockPath = Join-Path $outgoingDir "triage.lock"
if (-not (Test-Path $outgoingDir)) {
    New-Item -ItemType Directory -Path $outgoingDir -Force | Out-Null
}

function Write-TriageLock {
    param([hashtable]$Payload)
    $nowUtc = [datetime]::UtcNow
    $Payload.ts = $nowUtc.ToString("o")
    $Payload.ts_utc = $Payload.ts
    Add-TruthMetadataToArtifact -Artifact $Payload -ContractName "triage" -EmittedAtUtc $nowUtc
    Write-JsonArtifact -Path $lockPath -Artifact $Payload
}

# Correlation log (correlation != causation)
$corrScript = Join-Path $repoRoot "Scripts\correlation_log.ps1"
if (Test-Path $corrScript) { & $corrScript -Component "triage" -Event "run" 2>$null }

# 1. Patch readiness gate
$patchReadiness = Join-Path $repoRoot "Scripts\patch_readiness.ps1"
if (-not (Test-Path $patchReadiness)) {
    $obj = [ordered]@{
        status = "deferred"
        health_summary = "patch_readiness.ps1 not found"
        latency_ms = $null
        recommendations = @("Install patch_readiness.ps1")
        exit_code = 2
    }
    Write-TriageLock -Payload $obj
    Write-Host "Triage> DEFERRED (patch_readiness not found)" -ForegroundColor Red
    exit 2
}

& $patchReadiness > $null 2>&1
$ready = $LASTEXITCODE -eq 0

if (-not $ready) {
    $obj = [ordered]@{
        status = "deferred"
        health_summary = "patch_readiness deferred (entropy or health)"
        latency_ms = $null
        recommendations = @("Resolve entropy or health; re-run patch_readiness.")
        exit_code = 2
    }
    Write-TriageLock -Payload $obj
    Write-Host "Triage> DEFERRED (patch_readiness failed)" -ForegroundColor Red
    exit 2
}

# 2. Read station_health.json
$healthPath = Join-Path $repoRoot "runtime\station_health.json"
$health = "unknown"
$entropyTier = "unknown"
$topEntropySources = @()
$cpuPct = $null
$ramPct = $null
$healthFresh = $false

if (Test-Path -LiteralPath $healthPath -PathType Leaf) {
    try {
        $json = Get-Content -LiteralPath $healthPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $freshness = Get-ArtifactFreshness -ContractName "station_health" -Artifact $json -Path $healthPath
        if ($freshness.is_fresh) {
            $healthFresh = $true
            $health = $json.health
            $cpuPct = $json.cpu_pct
            $ramPct = $json.ram_pct
            if ($json.entropy) {
                if ($json.entropy.tier) { $entropyTier = $json.entropy.tier }
                if ($json.entropy.entropy_sources) {
                    $topEntropySources = $json.entropy.entropy_sources | ForEach-Object { "$($_.name):$($_.cpu_pct)%" }
                }
            }
        }
    } catch { }
}

# 3. Probe CBO Core (optional; minimal sunrise)
$latencyMs = $null
$cboReachable = $false
try {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:7778/state" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    $sw.Stop()
    $latencyMs = [int]$sw.ElapsedMilliseconds
    $cboReachable = ($r.StatusCode -eq 200)
} catch {
    # CBO not up or unreachable — acceptable for minimal sunrise
}

# 4. Summarize and determine exit
$healthSummary = "health=$health entropy_tier=$entropyTier cpu=$cpuPct% ram=$ramPct%"
if ($cboReachable) { $healthSummary += " cbo_latency_ms=$latencyMs" }

$recommendations = @()
if ($health -eq "fail") {
    $recommendations += "Resolve health=fail before adding load."
}
if ($entropyTier -eq "unacceptable") {
    $recommendations += "Entropy unacceptable; defer heavy work."
}
if ($entropyTier -eq "high") {
    $recommendations += "Entropy high; proceed with caution."
}
if (-not $healthFresh) {
    $recommendations += "Fresh station_health unavailable; triage confidence reduced."
}
if (-not $cboReachable -and $recommendations.Count -eq 0) {
    $recommendations += "CBO Core not reachable; minimal sunrise or services down."
}
if ($recommendations.Count -eq 0) {
    $recommendations += "Station healthy; safe for normal operations."
}

$exitCode = 0
if (-not $healthFresh) { $exitCode = 1 }
elseif ($health -eq "fail") { $exitCode = 2 }
elseif ($health -eq "warn" -or $entropyTier -eq "high") { $exitCode = 1 }

# 5. Write lock
$lockObj = [ordered]@{
    status = if ($exitCode -eq 0) { "pass" } elseif ($exitCode -eq 1) { "warn" } else { "fail" }
    health_summary = $healthSummary
    latency_ms = $latencyMs
    cbo_reachable = $cboReachable
    top_entropy_sources = $topEntropySources
    recommendations = $recommendations
    health_source_fresh = $healthFresh
    exit_code = $exitCode
}
Write-TriageLock -Payload $lockObj

Write-Host "Triage> $($lockObj.status.ToUpper()) $healthSummary" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } elseif ($exitCode -eq 1) { "Yellow" } else { "Red" })
foreach ($rec in $recommendations) { Write-Host "  - $rec" }
exit $exitCode
