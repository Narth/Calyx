# Start only the Station Calyx Telemetry Gateway (port 7781).
# For full core services use: .\Scripts\start_calyx_core_services.ps1
# Usage: .\Scripts\start_telemetry_gateway.ps1 [-StopFirst]

param(
    [switch]$StopFirst = $false
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) {
    $repoRoot = (Get-Location).Path
}
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot ".venv_cbohub311\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Error "Venv not found: $venvPython. Create .venv_cbohub311 first."
}

function Test-PortInUse {
    param([int]$Port)
    $conn = New-Object System.Net.Sockets.TcpClient
    try {
        $conn.Connect("127.0.0.1", $Port)
        $conn.Close()
        return $true
    } catch {
        return $false
    }
}

function Stop-ProcessOnPort {
    param([int]$Port)
    $found = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found -and $found.OwningProcess) {
        Stop-Process -Id $found.OwningProcess -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
}

$port = 7781
if ($StopFirst) {
    Write-Host "Stopping any process on $port..."
    Stop-ProcessOnPort -Port $port
}

if (Test-PortInUse -Port $port) {
    Write-Host "[Telemetry Gateway] Port $port already in use; skipping start."
    exit 0
}

Write-Host "[Telemetry Gateway] Starting on 0.0.0.0:$port..."
Start-Process -FilePath $venvPython -ArgumentList "-B", "-m", "cbo_hub.telemetry_gateway" `
    -WorkingDirectory $repoRoot -WindowStyle Normal
Write-Host "Done. Telemetry Gateway: http://0.0.0.0:$port (expose via ngrok for remote access)."
