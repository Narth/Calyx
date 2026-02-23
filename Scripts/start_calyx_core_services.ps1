# Start Calyx Core services: Dev Harness (7777), CBO Core (7778), Avatar Web (7780), Telemetry Gateway (7781).
# Usage: .\Scripts\start_calyx_core_services.ps1 [-StopFirst]
# -StopFirst: stop any process listening on 7777, 7778, 7780, 7781 before starting (clean restart).

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

$corePorts = @(7777, 7778, 7780, 7781)
if ($StopFirst) {
    Write-Host "Stopping any process on $($corePorts -join ', ')..."
    $corePorts | ForEach-Object { Stop-ProcessOnPort -Port $_ }
}

# Host: 127.0.0.1 for local-only; 0.0.0.0 for Telemetry Gateway (reachable via tunnel)
$services = @(
    @{ Name = "Dev Harness";       Port = 7777; Host = "127.0.0.1"; Module = "cbo_hub.dev_harness.app:app" },
    @{ Name = "CBO Core";         Port = 7778; Host = "127.0.0.1"; Module = "cbo_hub.cbo_core.app:app" },
    @{ Name = "Avatar Web";       Port = 7780; Host = "127.0.0.1"; Module = "cbo_hub.avatar_web.app:app" },
    @{ Name = "Telemetry Gateway"; Port = 7781; Host = "0.0.0.0";   Module = "cbo_hub.telemetry_gateway.app:app" }
)

foreach ($svc in $services) {
    $hostBind = if ($svc.Host) { $svc.Host } else { "127.0.0.1" }
    if (Test-PortInUse -Port $svc.Port) {
        Write-Host "[$($svc.Name)] Port $($svc.Port) already in use; skipping start."
        continue
    }
    Write-Host "[$($svc.Name)] Starting on $hostBind`:$($svc.Port)..."
    Start-Process -FilePath $venvPython -ArgumentList "-B", "-m", "uvicorn", $svc.Module, "--host", $hostBind, "--port", $svc.Port `
        -WorkingDirectory $repoRoot -WindowStyle Normal
    Start-Sleep -Seconds 2
}

Write-Host "Done. Dev Harness: http://127.0.0.1:7777 | CBO Core: http://127.0.0.1:7778 | Avatar Web: http://127.0.0.1:7780 | Telemetry Gateway: http://0.0.0.0:7781"
# Allow services to bind, then run health check and refresh STATE so the system validates current work
$validationDelaySec = 10
Write-Host "Waiting $validationDelaySec s for services to bind, then running validation (check + update_state_checks)..."
Start-Sleep -Seconds $validationDelaySec
$checkScript = Join-Path $repoRoot "Scripts\check_calyx_core_services.ps1"
$updateScript = Join-Path $repoRoot "Scripts\update_state_checks.ps1"
if (Test-Path $checkScript) {
    $checkResult = & $checkScript 2>&1 | Select-Object -First 1
    Write-Host "Check result: $checkResult"
}
if (Test-Path $updateScript) {
    & $updateScript
} else {
    Write-Warning "update_state_checks.ps1 not found; STATE.md not refreshed."
}
Write-Host "Validation complete."
