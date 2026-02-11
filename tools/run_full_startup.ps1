Param(
  [switch]$StartDashboard = $false
)

function Write-Log($m){ Write-Host "[calyx-start] $m" }

# repo root (assumes run from repo root)
$RepoRoot = (Resolve-Path ".").Path
Set-Location $RepoRoot

Write-Log "Ensuring runtime directories"
$dirs = @(
  "governance\intents\inbox",
  "governance\intents\outbox",
  "governance\intents\processed",
  "logs\governance",
  "logs\executor",
  "outgoing\shared_logs"
)
foreach ($d in $dirs) { if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null } }

# find python
$python = $null
try { $python = (Get-Command python -ErrorAction Stop).Source } catch {}
if (-not $python) { try { $python = (Get-Command python3 -ErrorAction Stop).Source } catch {} }
if (-not $python) {
  Write-Log "ERROR: 'python' not found on PATH. Install Python 3.8+ and ensure 'python' is on PATH."
  exit 1
}
Write-Log "Using python: $python"
# find python; prefer 'python', then 'python3', then the py launcher
$python = $null
try { $python = (Get-Command python -ErrorAction Stop).Source } catch {}
if (-not $python) { try { $python = (Get-Command python3 -ErrorAction Stop).Source } catch {} }
# Fallback to Windows Python launcher 'py' which is commonly present
if (-not $python) {
    try { $pycmd = (Get-Command py -ErrorAction Stop).Source; if ($pycmd) { $python = 'py' } } catch {}
}
if (-not $python) {
    Write-Log "ERROR: 'python' not found on PATH. Install Python 3.8+ and ensure 'python' or 'py' is on PATH. Aborting."
    exit 1
}
Write-Log "Using python command: $python"

# create venv if missing
$venv = Join-Path $RepoRoot ".venv"
if (-not (Test-Path $venv)) {
  Write-Log "Creating venv at $venv"
  & $python -m venv $venv
}

# activate venv where possible
$activate = Join-Path $venv "Scripts\Activate.ps1"
if (Test-Path $activate) {
  Write-Log "Activating venv"
  . $activate
} else {
  Write-Log "No Activate.ps1 found; proceeding with system python"
}
    # Create venv if possible
$Venv = Join-Path $RepoRoot '.venv'
if ($python -ne 'py') {
    if (-not (Test-Path $Venv)) {
        Write-Log "Creating venv at $Venv"
        & $python -m venv $Venv
    }

    # Activate if possible
    $Activate = Join-Path $Venv 'Scripts\Activate.ps1'
    if (Test-Path $Activate) {
        Write-Log "Activating venv"
        . $Activate
    } else {
        Write-Log "Activation script not found; will proceed with system python"
    }

    # Install minimal deps
    Write-Log "Installing minimal Python deps: pip, flask, psutil"
    & $python -m pip install --upgrade pip | Out-Null
    & $python -m pip install flask psutil | Out-Null
} else {
    Write-Log "Using 'py' launcher; attempting to install deps via 'py -3 -m pip'"
    try {
        & py -3 -m pip install --upgrade pip | Out-Null
        & py -3 -m pip install flask psutil | Out-Null
    } catch {
        Write-Log "Failed to install packages via 'py' launcher; proceed if packages are already available."
    }
}

# install minimal deps
Write-Log "Installing pip + minimal deps (flask, psutil)"
& $python -m pip install --upgrade pip | Out-Null
& $python -m pip install flask psutil | Out-Null

# validate intents in inbox (use py -3 when available)
Write-Log "Validating intents in governance\intents\inbox"
$validateCmd = if ($python -eq 'py') { 'py -3' } else { $python }
Get-ChildItem -Path governance\intents\inbox -Filter *.json -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Log ("Validating " + $_.FullName)
    & $validateCmd tools\governance_gate.py --validate $_.FullName
}

# run daemon once (use py -3 when available)
Write-Log "Running calyx_daemon for one cycle"
$daemonCmd = if ($python -eq 'py') { 'py -3' } else { $python }
& $daemonCmd tools\calyx_daemon.py --once

# optionally start dashboard backend + ack bridge (background)
if ($StartDashboard) {
  Write-Log "Starting dashboard backend and ui_ack_bridge in background"
  $b = Start-Process -FilePath $python -ArgumentList "-u","dashboard\backend\main.py" -PassThru
  Start-Sleep -Milliseconds 300
  $a = Start-Process -FilePath $python -ArgumentList "-u","tools\ui_ack_bridge.py" -PassThru
  $plist = @(
    @{ service = "dashboard_backend"; pid = $b.Id; script = "dashboard\backend\main.py" },
    @{ service = "ui_ack_bridge"; pid = $a.Id; script = "tools\ui_ack_bridge.py" }
  )
  $plist | ConvertTo-Json | Out-File -FilePath outgoing\shared_logs\processes.json -Encoding utf8
  Write-Log ("Started dashboard backend pid=" + $b.Id + " ack_bridge pid=" + $a.Id)
}

Write-Log "Startup complete. Inspect logs:"
Write-Log " - Gate log: logs\governance\gate_log.jsonl"
Write-Log " - Exec log: logs\executor\exec_log.jsonl"
Write-Log " - Outbox: governance\intents\outbox"
Write-Log " - Evidence: station_calyx\data\evidence.jsonl"