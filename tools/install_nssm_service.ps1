<#
Install NSSM service for Calyx Daemon (Windows)

Usage (run as Administrator from repo root C:\Calyx):
  powershell -ExecutionPolicy Bypass -File .\tools\install_nssm_service.ps1

What it does:
- Ensures directories exist for logs
- Locates a usable Python launcher (prefers 'py -3')
- Downloads NSSM (if not present) and extracts nssm.exe into .\tools\nssm\
- Installs a Windows service named 'CalyxDaemon' that runs:
    py -3 -u tools\calyx_daemon.py
  with WorkingDirectory set to the repo root.
- Configures stdout/stderr log paths and restart on failure
- Starts the service

Note: This script does NOT run automatically under non-elevated PowerShell. Run as Admin.
#>

param()

function Write-Log($m) { Write-Host "[nssm-installer] $m" }

$RepoRoot = (Get-Location).Path
$Tools = Join-Path $RepoRoot 'tools'
$NssmDir = Join-Path $Tools 'nssm'
$NssmExe = Join-Path $NssmDir 'nssm.exe'
$LogDir = Join-Path $RepoRoot 'outgoing\shared_logs'
$StdOut = Join-Path $LogDir 'calyx_daemon.out.log'
$StdErr = Join-Path $LogDir 'calyx_daemon.err.log'
$ServiceName = 'CalyxDaemon'

# Ensure log dir
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

# Find python launcher
$py = $null
try { $py = (Get-Command py -ErrorAction Stop).Source } catch { }
if (-not $py) {
    try { $py = (Get-Command python -ErrorAction Stop).Source } catch { }
}
if (-not $py) {
    Write-Log "ERROR: No 'py' or 'python' found on PATH. Install Python 3.8+ and re-run."
    exit 1
}
Write-Log "Using Python launcher: $py"

# Ensure NSSM present
if (-not (Test-Path $NssmExe)) {
    Write-Log "nssm.exe not found in $NssmDir — attempting download"
    $zipUrl = 'https://nssm.cc/release/nssm-2.24.zip'
    $tmpZip = Join-Path $env:TEMP 'nssm-2.24.zip'
    try {
        Write-Log "Downloading NSSM from $zipUrl"
        Invoke-WebRequest -Uri $zipUrl -OutFile $tmpZip -UseBasicParsing -ErrorAction Stop
        Write-Log "Extracting NSSM"
        Expand-Archive -Path $tmpZip -DestinationPath $NssmDir -Force
        # nssm zip contains a versioned folder; find nssm.exe under it
        $found = Get-ChildItem -Path $NssmDir -Recurse -Filter 'nssm.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) {
            Copy-Item -Path $found.FullName -Destination $NssmExe -Force
            Write-Log "nssm.exe extracted to $NssmExe"
        } else {
            Write-Log "Could not locate nssm.exe after extraction. Please install NSSM manually and re-run."
            exit 2
        }
    } catch {
        Write-Log "Failed to download or extract NSSM: $_"
        Write-Log "Please install NSSM manually and place nssm.exe at $NssmExe"
        exit 3
    } finally {
        if (Test-Path $tmpZip) { Remove-Item $tmpZip -Force }
    }
} else {
    Write-Log "Found nssm.exe at $NssmExe"
}

# Compose service command and args
$AppPath = 'py'
$AppArgs = '-3 -u tools\calyx_daemon.py'
# If 'py' launcher not available, use full python path
try {
    $pyCheck = (Get-Command py -ErrorAction SilentlyContinue).Source
    if (-not $pyCheck) { $AppPath = $py; $AppArgs = '-u tools\calyx_daemon.py' }
} catch {}

# Install service via nssm
Write-Log "Installing service $ServiceName"
& $NssmExe install $ServiceName $AppPath $AppArgs
# Configure service settings
& $NssmExe set $ServiceName AppDirectory $RepoRoot
& $NssmExe set $ServiceName AppStdout $StdOut
& $NssmExe set $ServiceName AppStderr $StdErr
& $NssmExe set $ServiceName Start SERVICE_AUTO_START
& $NssmExe set $ServiceName AppRestartDelay 5000

Write-Log "Starting service $ServiceName"
& $NssmExe start $ServiceName

Write-Log "Service installation complete. Check service status via: sc query $ServiceName"