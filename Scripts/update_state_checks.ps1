# Update STATE.md with live checks, heartbeat_ts, and health (from station_health_loop).
# Test/assessment metrics include CBO (cbo_core). See check_calyx_core_services.ps1.
# Usage: .\Scripts\update_state_checks.ps1
# Runs check_calyx_core_services.ps1, reads runtime/station_health.json (if present), then rewrites STATE.md:
#   checks: <output from probe>
#   heartbeat_ts: <current UTC ISO>
#   health: pass|warn|fail|unknown (from station_health_loop 1s schedule)
#   health_ts: <last health check UTC ISO>

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\STATE.md")) {
    $repoRoot = (Get-Location).Path
}
Set-Location $repoRoot

$statePath = Join-Path $repoRoot "STATE.md"
$checkScript = Join-Path $repoRoot "Scripts\check_calyx_core_services.ps1"
$healthPath = Join-Path $repoRoot "runtime\station_health.json"
if (-not (Test-Path $checkScript)) {
    Write-Error "Check script not found: $checkScript"
}
if (-not (Test-Path $statePath)) {
    Write-Error "STATE.md not found: $statePath. Create STATE.md before running update_state_checks."
}

$checksOutput = & $checkScript | Select-Object -First 1
$checksOutput = ($checksOutput -replace "^\s+|\s+$", "")
if (-not $checksOutput) { $checksOutput = "dev_harness=fail,cbo_core=fail,avatar_web=fail,telemetry_gateway=fail" }

$heartbeatTs = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")

$health = "unknown"
$healthTs = ""
$entropyTier = ""
if (Test-Path -LiteralPath $healthPath -PathType Leaf) {
    try {
        $healthJson = Get-Content -LiteralPath $healthPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $health = $healthJson.health
        $healthTs = $healthJson.health_ts
        if ($healthJson.entropy -and $healthJson.entropy.tier) { $entropyTier = $healthJson.entropy.tier }
    } catch { }
}

$content = Get-Content $statePath -Raw -Encoding UTF8
$content = $content -replace "(?m)^checks:.*$", "checks: $checksOutput"
$content = $content -replace "(?m)^heartbeat_ts:.*$", "heartbeat_ts: $heartbeatTs"
$content = $content -replace "(?m)^health:.*$", "health: $health"
$content = $content -replace "(?m)^health_ts:.*$", "health_ts: $healthTs"
if ($entropyTier) {
    if ($content -match "(?m)^entropy_tier:.*$") {
        $content = $content -replace "(?m)^entropy_tier:.*$", "entropy_tier: $entropyTier"
    } else {
        $content = $content -replace "(?m)^(health_ts:.*)$", "`$1`nentropy_tier: $entropyTier"
    }
}
Set-Content -Path $statePath -Value $content -Encoding UTF8 -NoNewline

# Emit heartbeat.tick to Station Event Ledger (WO_STATION_EVENT_LEDGER_V1)
$emitScript = Join-Path $repoRoot "Scripts\emit_heartbeat_tick.py"
if (Test-Path $emitScript) {
    try { python $emitScript $checksOutput $health 2>$null } catch { }
}

Write-Output "STATE.md updated: checks=$checksOutput heartbeat_ts=$heartbeatTs health=$health entropy_tier=$entropyTier"
