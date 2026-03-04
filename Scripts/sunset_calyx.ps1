# Sunset Calyx — explicit safe shutdown of all Calyx services.
# Stops: Calyx Discord Gateway, Dev Harness (7777), CBO Core (7778), Avatar Web (7780), Telemetry Gateway (7781).
# Usage: .\Scripts\sunset_calyx.ps1 [-StopOpenClaw] [-WaitForPortsFree]
# -StopOpenClaw: Also stop OpenClaw gateway (conflicts with Calyx Discord)
# -WaitForPortsFree: Retry until ports are free (default: wait up to 15s)

param(
    [switch]$StopOpenClaw = $true,
    [switch]$WaitForPortsFree = $true,
    [int]$MaxWaitSec = 15
)

$ErrorActionPreference = "Continue"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) { $repoRoot = (Get-Location).Path }
Set-Location $repoRoot

$corePorts = @(7777, 7778, 7780, 7781)

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

Write-Host "Sunset complete."
