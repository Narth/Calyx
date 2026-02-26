# WO_SUNRISE_CANONICAL_BOOTPATH_DISCORD_GATEWAY_V1: Canonical Sunrise orchestrator.
# Delegates to start_calyx_core_services.ps1 (gate → preflight → core services → Discord Gateway → receipt).
# Pre-loads Discord env from User so start_calyx_core_services.ps1 has them.
#
# Usage: .\Scripts\sunrise_calyx.ps1 [-StartCoreOnly]
# -StartCoreOnly: Pass -SkipGateway to core script (debug; no Discord Gateway).

param(
    [switch]$StartCoreOnly = $false
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) { $repoRoot = (Get-Location).Path }
Set-Location $repoRoot

# Pre-load Discord env (start_calyx_core_services.ps1 also loads; this ensures session has them)
if (-not $env:DISCORD_BOT_TOKEN) {
    $env:DISCORD_BOT_TOKEN = [System.Environment]::GetEnvironmentVariable("DISCORD_BOT_TOKEN", "User")
}
if (-not $env:DISCORD_HEARTBEAT_USER_ID) {
    $env:DISCORD_HEARTBEAT_USER_ID = [System.Environment]::GetEnvironmentVariable("DISCORD_HEARTBEAT_USER_ID", "User")
}
if (-not $env:DISCORD_HEARTBEAT_USER_ID) { $env:DISCORD_HEARTBEAT_USER_ID = "315642751419023371" }
if (-not $env:DISCORD_CHANNEL_ALLOWLIST) {
    $env:DISCORD_CHANNEL_ALLOWLIST = [System.Environment]::GetEnvironmentVariable("DISCORD_CHANNEL_ALLOWLIST", "User")
}
if (-not $env:DISCORD_CHANNEL_ALLOWLIST) { $env:DISCORD_CHANNEL_ALLOWLIST = "1465903939659632807" }
if (-not $env:DISCORD_AUTHORIZED_USERS) {
    $env:DISCORD_AUTHORIZED_USERS = [System.Environment]::GetEnvironmentVariable("DISCORD_AUTHORIZED_USERS", "User")
}
if (-not $env:DISCORD_AUTHORIZED_USERS) { $env:DISCORD_AUTHORIZED_USERS = "315642751419023371" }

$coreScript = Join-Path $repoRoot "Scripts\start_calyx_core_services.ps1"
if (-not (Test-Path $coreScript)) {
    Write-Error "start_calyx_core_services.ps1 not found."; exit 1
}

$args = @()
if ($StartCoreOnly) { $args += "-SkipGateway" }

& $coreScript @args
$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "Sunrise complete. Governed mode active. Discord DM -> CBO Core (7778)."
} else {
    Write-Host "Sunrise failed (exit $exitCode). Check receipt and audit events."
}
exit $exitCode
