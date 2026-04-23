# Sunset Calyx — explicit safe shutdown of all Calyx services.
# Stops: Calyx Discord Gateway, Dev Harness (7777), CBO Core (7778), Avatar Web (7780), Telemetry Gateway (7781).
# Gently: signals background loops first, then core services.
# Usage: .\Scripts\sunset_calyx.ps1 [-StopOpenClaw] [-WaitForPortsFree]
# -StopOpenClaw: Also stop OpenClaw gateway (conflicts with Calyx Discord)
# -WaitForPortsFree: Retry until ports are free (default: wait up to 15s)

param(
    [switch]$StopOpenClaw = $true,
    [switch]$WaitForPortsFree = $true,
    [int]$MaxWaitSec = 15,
    [ValidateSet("manual", "patch", "restart")][string]$ShutdownReason = "manual"
)

$ErrorActionPreference = "Continue"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) { $repoRoot = (Get-Location).Path }
Set-Location $repoRoot

$truthHelper = Join-Path $repoRoot "Scripts\runtime_truth_contract.ps1"
if (-not (Test-Path $truthHelper)) {
    Write-Error "runtime_truth_contract.ps1 not found: $truthHelper"
    exit 1
}
. $truthHelper

$corePorts = @(7777, 7778, 7780, 7781)
$runtimeDir = Join-Path $repoRoot "runtime"

try {
    $shutdownMarker = Emit-StationShutdownMarker -RepoRoot $repoRoot -Reason $ShutdownReason -ObservedAtUtc ([datetime]::UtcNow)
    Write-Host "Shutdown marker receipt: $($shutdownMarker.receipt_path)"
} catch {
    Write-Warning "Failed to emit shutdown marker: $($_.Exception.Message)"
}

# 0. Gentle: signal background loops to stop (they check stop files each loop)
Write-Host "Sunset: signaling background loops..."
$loopStopFiles = @(
    "station_health.stop",
    "navigator_triage.stop",
    "energy_churn_cp9.stop",
    "cp6_cp7.stop"
)
foreach ($f in $loopStopFiles) {
    $path = Join-Path $runtimeDir $f
    try {
        New-Item -ItemType File -Path $path -Force -ErrorAction SilentlyContinue | Out-Null
    } catch { }
}
Start-Sleep -Seconds 3

function Test-PortFree {
    param([int]$Port)
    try {
        $conn = New-Object System.Net.Sockets.TcpClient
        $conn.Connect("127.0.0.1", $Port)
        $conn.Close()
        return $false
    } catch { return $true }
}

function Stop-ProcessOnPort {
    param([int]$Port)
    $pids = @()
    try {
        $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        foreach ($c in $conns) {
            if ($c.OwningProcess -and $c.OwningProcess -notin $pids) {
                $pids += $c.OwningProcess
            }
        }
    } catch { }
    if ($pids.Count -eq 0) {
        try {
            $lines = netstat -ano 2>$null | Select-String ":$Port\s+.*LISTENING"
            foreach ($line in $lines) {
                $parts = ($line -split '\s+', 0, 'RemoveEmptyEntries')
                $pidStr = $parts[-1]
                if ($pidStr -match '^\d+$' -and [int]$pidStr -notin $pids) { $pids += [int]$pidStr }
            }
        } catch { }
    }
    foreach ($procId in $pids) {
        try {
            Write-Host "  Stopping PID $procId (port $Port)..."
            taskkill /F /T /PID $procId 2>$null
        } catch { }
    }
}

function Stop-PowerShellProcessByPattern {
    param([string]$Pattern)
    try {
        $targets = Get-Process powershell -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
                if ($cmd -and $cmd -match $Pattern) { $_ }
            } catch { }
        }
        foreach ($target in $targets) {
            Write-Host "  Stopping PowerShell loop PID $($target.Id) ($Pattern)..."
            taskkill /F /T /PID $target.Id 2>$null
        }
    } catch { }
}

Write-Host "Sunset: stopping Calyx services..."

# 1. Stop Calyx Discord Gateway (python -m calyx.cbo.discord_gateway)
$gatewayProcs = Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        if ($cmd -match "calyx\.cbo\.discord_gateway") { $_ }
    } catch { }
}
foreach ($p in $gatewayProcs) {
    Write-Host "  Stopping Calyx Discord Gateway (PID $($p.Id))..."
    taskkill /F /T /PID $p.Id 2>$null
}

# 1b. Stop loop hosts that did not honor the stop files quickly enough.
Stop-PowerShellProcessByPattern -Pattern "station_health_loop\.ps1"
Stop-PowerShellProcessByPattern -Pattern "service_failure_watch\.ps1"
Stop-PowerShellProcessByPattern -Pattern "navigator_triage_loop\.ps1"
Stop-PowerShellProcessByPattern -Pattern "energy_churn_cp9_loop\.ps1"
Stop-PowerShellProcessByPattern -Pattern "cp6_cp7_loop\.ps1"

# 1c. Stop CBO Bridge Overseer and CLI Avatar
Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        if ($cmd -match "calyx\.cbo\.bridge_overseer") {
            Write-Host "  Stopping CBO Bridge Overseer (PID $($_.Id))..."
            taskkill /F /T /PID $_.Id 2>$null
        }
        elseif ($cmd -match "cbo_hub\.cli_avatar\.main") {
            Write-Host "  Stopping CLI Avatar (PID $($_.Id))..."
            taskkill /F /T /PID $_.Id 2>$null
        }
    } catch { }
}

# 2. Stop OpenClaw gateway if requested
if ($StopOpenClaw) {
    $nodeProcs = Get-Process node -ErrorAction SilentlyContinue
    foreach ($p in $nodeProcs) {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)" -ErrorAction SilentlyContinue).CommandLine
            if ($cmd -match "openclaw.*gateway") {
                Write-Host "  Stopping OpenClaw gateway (PID $($p.Id))..."
                taskkill /F /T /PID $p.Id 2>$null
            }
        } catch { }
    }
}

# 3. Stop Core services by port (taskkill /F /T for process tree)
foreach ($port in $corePorts) {
    Stop-ProcessOnPort -Port $port
}

Start-Sleep -Seconds 2

# 4. Retry until ports free
if ($WaitForPortsFree) {
    $elapsed = 0
    while ($elapsed -lt $MaxWaitSec) {
        $allFree = $true
        foreach ($port in $corePorts) {
            if (-not (Test-PortFree -Port $port)) {
                $allFree = $false
                Stop-ProcessOnPort -Port $port
            }
        }
        if ($allFree) {
            Write-Host "All ports free."
            break
        }
        Start-Sleep -Seconds 2
        $elapsed += 2
    }
    if ($elapsed -ge $MaxWaitSec) {
        Write-Host "Warning: Some ports may still be in use after ${MaxWaitSec}s."
    }
}

try {
    $updateScript = Join-Path $repoRoot "Scripts\update_state_checks.ps1"
    if (Test-Path $updateScript) {
        & $updateScript -ForceStale -StaleReason "graceful_shutdown" | Out-Null
    }
    $shutdownTruthReceipt = Write-RuntimeTruthTransition -RepoRoot $repoRoot -Transition "shutdown_stale_marked" -Reason "graceful_shutdown" -Surfaces @("STATE.md", "runtime/station_heartbeat.json", "runtime/service_runtime_snapshot.json", "runtime/runtime_topology_snapshot.json", "outgoing/*.lock")
    Write-Host "Runtime truth transition receipt: $shutdownTruthReceipt"
} catch {
    Write-Warning "Failed to stale-mark runtime truth during sunset: $($_.Exception.Message)"
}

Write-Host "Sunset complete."
