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

$truthHelper = Join-Path $repoRoot "Scripts\runtime_truth_contract.ps1"
if (-not (Test-Path $truthHelper)) {
    Write-Error "runtime_truth_contract.ps1 not found."; exit 1
}
. $truthHelper

$hostBootReceipt = Emit-HostBootDetected -RepoRoot $repoRoot -ObservedAtUtc ([datetime]::UtcNow)
Write-Host "Host boot receipt: $($hostBootReceipt.receipt_path)"
$uncleanInterruptionReceipt = Emit-StationUncleanInterruption -RepoRoot $repoRoot -ObservedAtUtc ([datetime]::UtcNow)
Write-Host "Interruption assessment receipt: $($uncleanInterruptionReceipt.receipt_path)"

# Pre-load Discord env: User env > DISCORD_IDS.md. No hardcoded fallbacks (governance hygiene).
function Get-DiscordIdsFromFile {
    param([string]$IdsPath)
    if (-not (Test-Path $IdsPath)) { return $null }
    $content = Get-Content $IdsPath -Raw -ErrorAction SilentlyContinue
    if (-not $content) { return $null }
    $channels = @(); $users = @()
    foreach ($line in ($content -split "`n")) {
        if ($line -match "Station Health Channel ID[^\d]*(\d{17,20})") { $channels += $matches[1] }
        if ($line -match "Authorized User ID[^\d]*(\d{17,20})") { $users += $matches[1] }
    }
    return @{ channels = $channels; users = $users }
}
$idsPath = Join-Path $repoRoot "DISCORD_IDS.md"
$idsFromFile = Get-DiscordIdsFromFile -IdsPath $idsPath

if (-not $env:DISCORD_BOT_TOKEN) {
    $env:DISCORD_BOT_TOKEN = [System.Environment]::GetEnvironmentVariable("DISCORD_BOT_TOKEN", "User")
}
if (-not $env:DISCORD_HEARTBEAT_USER_ID) {
    $env:DISCORD_HEARTBEAT_USER_ID = [System.Environment]::GetEnvironmentVariable("DISCORD_HEARTBEAT_USER_ID", "User")
}
if (-not $env:DISCORD_HEARTBEAT_USER_ID -and $idsFromFile -and $idsFromFile.users.Count -gt 0) {
    $env:DISCORD_HEARTBEAT_USER_ID = $idsFromFile.users[0]
}
if (-not $env:DISCORD_CHANNEL_ALLOWLIST) {
    $env:DISCORD_CHANNEL_ALLOWLIST = [System.Environment]::GetEnvironmentVariable("DISCORD_CHANNEL_ALLOWLIST", "User")
}
if (-not $env:DISCORD_CHANNEL_ALLOWLIST -and $idsFromFile -and $idsFromFile.channels.Count -gt 0) {
    $env:DISCORD_CHANNEL_ALLOWLIST = $idsFromFile.channels -join ","
}
if (-not $env:DISCORD_AUTHORIZED_USERS) {
    $env:DISCORD_AUTHORIZED_USERS = [System.Environment]::GetEnvironmentVariable("DISCORD_AUTHORIZED_USERS", "User")
}
if (-not $env:DISCORD_AUTHORIZED_USERS -and $idsFromFile -and $idsFromFile.users.Count -gt 0) {
    $env:DISCORD_AUTHORIZED_USERS = $idsFromFile.users -join ","
}

$coreScript = Join-Path $repoRoot "Scripts\start_calyx_core_services.ps1"
if (-not (Test-Path $coreScript)) {
    Write-Error "start_calyx_core_services.ps1 not found."; exit 1
}

$args = @()
if ($StartCoreOnly) { $args += "-SkipGateway" }

$coreFailure = $null
$exitCode = 1
try {
    & $coreScript @args
    $exitCode = $LASTEXITCODE
} catch {
    $coreFailure = $_.Exception.Message
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
        $exitCode = $LASTEXITCODE
    } else {
        $exitCode = 1
    }
    Write-Warning "Core sunrise path failed: $coreFailure"
}

try {
    $recoveryReceipt = Emit-StationRecoveryStatus -RepoRoot $repoRoot -ObservedAtUtc ([datetime]::UtcNow) -StartExitCode $exitCode -StartCoreOnly:$StartCoreOnly
    Write-Host "Recovery status receipt: $($recoveryReceipt.receipt_path)"
} catch {
    Write-Warning "Failed to emit recovery status receipt: $($_.Exception.Message)"
}

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "Sunrise complete. Governed mode active. Discord DM -> CBO Core (7778)."
} else {
    Write-Host "Sunrise failed (exit $exitCode). Check receipt and audit events."
}
exit $exitCode
