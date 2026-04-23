# Start Station Calyx with GOVERNED Discord — all Discord DM traffic routes to CBO Core.
# WO_OPENCLAW_UNIFIED_EXECUTOR: No activity reaches this machine without Station vetting.
#
# Discord → Calyx Discord Gateway → CBO Core (7778) → governance → response
# OpenClaw does NOT handle Discord in this mode. One bot = one connection.
#
# Usage: .\Scripts\start_station_governed.ps1 [-StopOpenClaw] [-StartCoreOnly] [-StopFirst]
# -StopOpenClaw: Stop any running OpenClaw gateway (it would conflict with our Discord bot)
# -StartCoreOnly: Start only CBO Core services; caller will start Discord Gateway separately
# -StopFirst: Sunset — stop services on 7777,7778,7780,7781 before starting (clean restart after patches)

param(
    [switch]$StopOpenClaw = $true,
    [switch]$StartCoreOnly = $false,
    [switch]$StopFirst = $false
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) {
    $repoRoot = (Get-Location).Path
}
Set-Location $repoRoot

# Load DISCORD_BOT_TOKEN
if (-not $env:DISCORD_BOT_TOKEN) {
    $env:DISCORD_BOT_TOKEN = [System.Environment]::GetEnvironmentVariable("DISCORD_BOT_TOKEN", "User")
}
# Heartbeat: report STATE/HEALTH to user DM every 30 min (DISCORD_HEARTBEAT_USER_ID from DISCORD_IDS)
if (-not $env:DISCORD_HEARTBEAT_USER_ID) {
    $env:DISCORD_HEARTBEAT_USER_ID = [System.Environment]::GetEnvironmentVariable("DISCORD_HEARTBEAT_USER_ID", "User")
}
if (-not $env:DISCORD_HEARTBEAT_USER_ID) {
    $env:DISCORD_HEARTBEAT_USER_ID = "315642751419023371"
}
# WO_GATEWAY_DENY_BY_DEFAULT: allowlists required for governance
if (-not $env:DISCORD_CHANNEL_ALLOWLIST) {
    $env:DISCORD_CHANNEL_ALLOWLIST = [System.Environment]::GetEnvironmentVariable("DISCORD_CHANNEL_ALLOWLIST", "User")
}
if (-not $env:DISCORD_CHANNEL_ALLOWLIST) {
    $env:DISCORD_CHANNEL_ALLOWLIST = "1465903939659632807"
}
if (-not $env:DISCORD_AUTHORIZED_USERS) {
    $env:DISCORD_AUTHORIZED_USERS = [System.Environment]::GetEnvironmentVariable("DISCORD_AUTHORIZED_USERS", "User")
}
if (-not $env:DISCORD_AUTHORIZED_USERS) {
    $env:DISCORD_AUTHORIZED_USERS = "315642751419023371"
}

# 1. Stop OpenClaw if it owns Discord (same bot token = conflict)
if ($StopOpenClaw) {
    $nodeProcs = Get-Process node -ErrorAction SilentlyContinue
    foreach ($p in $nodeProcs) {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)" -ErrorAction SilentlyContinue).CommandLine
            if ($cmd -match "openclaw.*gateway") {
                Write-Host "Stopping OpenClaw gateway (PID $($p.Id)) - Discord must use Calyx Gateway for governance."
                Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 2
            }
        } catch { }
    }
}

# 2. Start CBO Core (and core services)
$coreScript = Join-Path $repoRoot "Scripts\start_calyx_core_services.ps1"
if (Test-Path $coreScript) {
    if ($StopFirst) { Write-Host "Sunset: stopping services on 7777, 7778, 7780, 7781..." }
    Write-Host "Starting CBO Core services (7777, 7778, 7780, 7781)..."
    $coreArgs = @()
    if ($StopFirst) { $coreArgs += "-StopFirst" }
    & $coreScript @coreArgs
} else {
    Write-Warning "start_calyx_core_services.ps1 not found. Start CBO Core manually (port 7778)."
}

if ($StartCoreOnly) {
    Write-Host "Core-only mode. Start Discord Gateway separately: python -m calyx.cbo.discord_gateway"
    exit
}

# 3. Start Calyx Discord Gateway — Discord → CBO only
$venvPython = Join-Path $repoRoot ".venv_cbohub311\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    $venvPython = "python"
}
if (-not $env:DISCORD_BOT_TOKEN) {
    Write-Warning "DISCORD_BOT_TOKEN not set. Discord Gateway will not start. Set it in User env."
} else {
    $gatewayProcs = Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        if ($cmd -match "calyx\.cbo\.discord_gateway") { $_ }
    }
    if ($gatewayProcs) {
        Write-Host "Calyx Discord Gateway already running (PID $($gatewayProcs[0].Id))."
    } else {
        Write-Host "Starting Calyx Discord Gateway (Discord -> CBO, governed)..."
        Start-Process -FilePath $venvPython -ArgumentList "-m", "calyx.cbo.discord_gateway" `
            -WorkingDirectory $repoRoot -WindowStyle Normal
        Start-Sleep -Seconds 2
        Write-Host "Calyx Discord Gateway started. All Discord DMs route to CBO Core."
    }
}

Write-Host ""
Write-Host "Governed mode active. Discord DM -> CBO Core (7778). No OpenClaw Discord."
Write-Host "Ledger: runtime\ledger\station_events__*.jsonl"
