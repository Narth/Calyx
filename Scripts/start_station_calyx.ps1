# Start Station Calyx — single Discord intake, optionally CBO API, or OpenClaw (full assistant).
# Use -UseOpenClaw for OpenClaw Gateway (replaces discord_intake; same bot token).
# Usage: .\scripts\start_station_calyx.ps1 [-StartApi] [-StartDiscord] [-UseOpenClaw]

param(
    [switch]$StartApi = $false,
    [switch]$StartDiscord = $true,
    [switch]$UseOpenClaw = $false
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path "$repoRoot\calyx")) {
    $repoRoot = (Get-Location).Path
}
Set-Location $repoRoot

function Get-CalyxProcesses {
    Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        [PSCustomObject]@{ Id = $_.Id; CommandLine = $cmd }
    } | Where-Object { $_.CommandLine }
}

# Load DISCORD_BOT_TOKEN from User scope if not in current session
if (-not $env:DISCORD_BOT_TOKEN) {
    $env:DISCORD_BOT_TOKEN = [System.Environment]::GetEnvironmentVariable("DISCORD_BOT_TOKEN", "User")
}

# OpenClaw mode: stop discord_intake, run OpenClaw gateway (full assistant)
if ($UseOpenClaw) {
    if ($env:CALYX_ALLOW_QUARANTINED_OPENCLAW -ne "1") {
        Write-Error "Refusing OpenClaw launch: OpenClaw is quarantined noncanonical and must not present as Station Calyx authority. Set CALYX_ALLOW_QUARANTINED_OPENCLAW=1 only for explicit historical/diagnostic use."
        exit 1
    }
    $intakeProcs = Get-CalyxProcesses | Where-Object { $_.CommandLine -match "calyx\.cbo\.discord_intake.*--run" }
    if ($intakeProcs) {
        $intakeProcs | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 1
    }
    Write-Host "Starting OpenClaw Gateway (port 18789, Calyx workspace)..."
    & openclaw gateway --port 18789 --verbose
    exit
}

# Ensure single discord_intake: stop any existing before starting
if ($StartDiscord) {
    if ($env:CALYX_ALLOW_LEGACY_DISCORD_INTAKE -ne "1") {
        Write-Error "Refusing legacy discord_intake launch: canonical Discord transport is calyx.cbo.discord_gateway via governed sunrise. Set CALYX_ALLOW_LEGACY_DISCORD_INTAKE=1 only for explicit historical/diagnostic use."
        exit 1
    }
    if (-not $env:DISCORD_BOT_TOKEN) {
        Write-Warning "DISCORD_BOT_TOKEN not set. Set it first: [System.Environment]::SetEnvironmentVariable('DISCORD_BOT_TOKEN','your_token','User')"
        $StartDiscord = $false
    }
}
if ($StartDiscord) {
    $intakeProcs = Get-CalyxProcesses | Where-Object { $_.CommandLine -match "calyx\.cbo\.discord_intake.*--run" }
    if ($intakeProcs) {
        $intakeProcs | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 1
    }
    Write-Host "Starting discord_intake (single instance)..."
    Start-Process -FilePath "python" -ArgumentList "-m", "calyx.cbo.discord_intake", "--run", "--repo-root", "." `
        -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru | Out-Null
    Write-Host "discord_intake started."
}

# Optionally ensure CBO API is running
if ($StartApi) {
    $apiProc = Get-CalyxProcesses | Where-Object { $_.CommandLine -match "calyx\.cbo\.api" } | Select-Object -First 1
    if (-not $apiProc) {
        Write-Host "Starting CBO API..."
        Start-Process -FilePath "python" -ArgumentList "-m", "calyx.cbo.api" `
            -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru | Out-Null
        Write-Host "CBO API started."
    } else {
        Write-Host "CBO API already running (PID $($apiProc.Id))."
    }
}
