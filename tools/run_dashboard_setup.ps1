<#
PowerShell helper to set up and start the dashboard backend and UI ack bridge.
Run this in a separate operator PowerShell window from the repo root (C:\Calyx).
It will:
 - check for python
 - create/activate a venv at .venv
 - install Flask
 - start dashboard backend and ui_ack_bridge as background processes
 - write process PIDs to outgoing/shared_logs/processes.json
 - poll the backend API for /api/chat/agent-responses to confirm HTTP 200
 - print status and evidence file locations

Usage (from repo root):
  powershell -ExecutionPolicy Bypass -File .\tools\run_dashboard_setup.ps1
#>

Param()

function Write-Log($msg) { Write-Host "[setup] $msg" }

$RepoRoot = (Split-Path -Parent $MyInvocation.MyCommand.Definition) | Split-Path -Parent
Set-Location $RepoRoot

# Paths
$VenvPath = Join-Path $RepoRoot '.venv'
$StatusDir = Join-Path $RepoRoot 'outgoing\shared_logs'
$StatusFile = Join-Path $StatusDir 'processes.json'
$EvidencePath = Join-Path $RepoRoot 'station_calyx\data\evidence.jsonl'

# Ensure status dir
if (-not (Test-Path $StatusDir)) { New-Item -ItemType Directory -Path $StatusDir | Out-Null }

# Find python
$python = $null
try {
    $python = (Get-Command python -ErrorAction Stop).Source
} catch {
    try { $python = (Get-Command python3 -ErrorAction Stop).Source } catch { }
}
if (-not $python) {
    Write-Log "Python not found on PATH. Please install Python 3.8+ and re-run this script. Aborting."
    exit 1
}

Write-Log "Using python: $python"

# Create venv if missing
if (-not (Test-Path $VenvPath)) {
    Write-Log "Creating virtual environment at $VenvPath"
    & $python -m venv $VenvPath
}

# Activate venv for this script
$ActivateScript = Join-Path $VenvPath 'Scripts\Activate.ps1'
if (Test-Path $ActivateScript) {
    Write-Log "Activating venv"
    . $ActivateScript
} else {
    Write-Log "Activation script not found; proceeding with system python"
}

# Ensure pip and install Flask
Write-Log "Ensuring pip and installing Flask"
try {
    & $python -m pip install --upgrade pip | Out-Null
    & $python -m pip install flask | Out-Null
    Write-Log "Flask installed"
} catch {
    Write-Log "pip install failed: $_"
    Write-Log "Proceeding; backend may fail to start if dependencies missing."
}

function Start-ServiceProc($name, $scriptPath) {
    Write-Log "Starting $name -> $scriptPath"
    $p = Start-Process -FilePath $python -ArgumentList "-u", $scriptPath -PassThru -WindowStyle Hidden
    Start-Sleep -Milliseconds 300
    if ($p -and $p.Id) {
        Write-Log "$name started pid=$($p.Id)"
        return @{ service=$name; pid=$p.Id; script=$scriptPath }
    } else {
        Write-Log "Failed to start $name"
        return @{ service=$name; pid=$null; script=$scriptPath }
    }
}

# Start dashboard backend and ack bridge
$processes = @()
$backendScript = 'dashboard\backend\main.py'
$ackBridgeScript = 'tools\ui_ack_bridge.py'

$processes += Start-ServiceProc 'dashboard_backend' $backendScript
$processes += Start-ServiceProc 'ui_ack_bridge' $ackBridgeScript

# Persist process list
$processes | ConvertTo-Json | Out-File -FilePath $StatusFile -Encoding utf8
Write-Log "Wrote process info to $StatusFile"

# Poll backend API
$backendUrl = 'http://127.0.0.1:8080/api/chat/agent-responses'
$ok = $false
for ($i=0; $i -lt 12; $i++) {
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri $backendUrl -ErrorAction Stop -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($ok) {
    Write-Log "Dashboard backend responding (HTTP 200)"
    Write-Log "Evidence file: $EvidencePath"
    Write-Log "Outbox dir: $RepoRoot\outgoing\comms\standard"
    Write-Log "Ack sink: $RepoRoot\outgoing\shared_logs"
    Write-Log "Check UI to confirm replies are visible."
    exit 0
} else {
    Write-Log "Dashboard backend did not respond at $backendUrl. Check $StatusFile and backend log output."
    exit 2
}
