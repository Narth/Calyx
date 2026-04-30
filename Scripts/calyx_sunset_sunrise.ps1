# Calyx Sunset → Sunrise — explicit safe shutdown and startup of all Calyx services.
# Use after system-level changes (cbo_hub, calyx, Scripts, config) so services load new code.
#
# Usage: .\Scripts\calyx_sunset_sunrise.ps1 [-SkipReadiness] [-CoreOnly]
# -SkipReadiness: Skip patch_readiness gate before sunset
# -CoreOnly: Start only CBO Core; do not start Discord Gateway

param(
    [switch]$SkipReadiness = $false,
    [switch]$CoreOnly = $false
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) { $repoRoot = (Get-Location).Path }
Set-Location $repoRoot

$truthHelper = Join-Path $repoRoot "Scripts\runtime_truth_contract.ps1"
if (-not (Test-Path $truthHelper)) {
    Write-Error "runtime_truth_contract.ps1 not found: $truthHelper"
}
. $truthHelper

# 1. Patch readiness (optional)
if (-not $SkipReadiness) {
    $readinessScript = Join-Path $repoRoot "Scripts\patch_readiness.ps1"
    if (Test-Path $readinessScript) {
        & $readinessScript
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Patch readiness failed. Defer. Use -SkipReadiness to override." -ForegroundColor Yellow
            exit 1
        }
    }
}

$patchEnterReceipt = Write-RuntimeTruthTransition -RepoRoot $repoRoot -Transition "patch_window_enter" -Reason "sunset_to_sunrise_window" -Surfaces @("STATE.md", "runtime/station_heartbeat.json", "runtime/service_runtime_snapshot.json", "runtime/runtime_topology_snapshot.json")
Write-Host "Runtime truth transition receipt: $patchEnterReceipt"

# 2. Sunset
$sunsetScript = Join-Path $repoRoot "Scripts\sunset_calyx.ps1"
if (-not (Test-Path $sunsetScript)) { Write-Error "sunset_calyx.ps1 not found." }
& $sunsetScript -StopOpenClaw -WaitForPortsFree -ShutdownReason patch
Start-Sleep -Seconds 2

# 3. Sunrise
$sunriseScript = Join-Path $repoRoot "Scripts\sunrise_calyx.ps1"
if (-not (Test-Path $sunriseScript)) { Write-Error "sunrise_calyx.ps1 not found." }
if ($CoreOnly) {
    & $sunriseScript -StartCoreOnly
} else {
    & $sunriseScript
}

$patchExitReceipt = Write-RuntimeTruthTransition -RepoRoot $repoRoot -Transition "patch_window_exit" -Reason "sunrise_complete" -Surfaces @("STATE.md", "runtime/station_heartbeat.json", "runtime/service_runtime_snapshot.json", "runtime/runtime_topology_snapshot.json")
Write-Host "Runtime truth transition receipt: $patchExitReceipt"

Write-Host ""
Write-Host "Calyx sunset → sunrise complete. Test: Discord DM or Dev Harness http://127.0.0.1:7777"
