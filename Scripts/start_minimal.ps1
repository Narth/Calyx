# Start minimal Calyx Core services by mode. Reduces load vs full sunrise.
# Usage: .\Scripts\start_minimal.ps1 -Mode <bridge|remote|patch|full> [-StopFirst]
# Modes: bridge=CBO only; remote=CBO+Telemetry; patch=DevHarness+CBO; full=all four.
# See: docs/operations/PATCH_DELIVERY_WIRING_PLAN.md, docs/operations/NAVIGATOR_TRIAGE_MINIMAL_SUNRISE.md

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("bridge","remote","patch","full")]
    [string]$Mode,
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

$allServices = @(
    @{ Name = "Dev Harness";       Port = 7777; Host = "127.0.0.1"; Module = "cbo_hub.dev_harness.app:app" },
    @{ Name = "CBO Core";          Port = 7778; Host = "127.0.0.1"; Module = "cbo_hub.cbo_core.app:app" },
    @{ Name = "Avatar Web";       Port = 7780; Host = "127.0.0.1"; Module = "cbo_hub.avatar_web.app:app" },
    @{ Name = "Telemetry Gateway"; Port = 7781; Host = "0.0.0.0";   Module = "cbo_hub.telemetry_gateway.app:app" }
)

$modePorts = @{
    bridge = @(7778)
    remote = @(7778, 7781)
    patch  = @(7777, 7778)
    full   = @(7777, 7778, 7780, 7781)
}

$portsToStart = $modePorts[$Mode]
$servicesToStart = $allServices | Where-Object { $portsToStart -contains $_.Port }

if ($StopFirst) {
    Write-Host "Stopping any process on $($portsToStart -join ', ')..."
    $portsToStart | ForEach-Object { Stop-ProcessOnPort -Port $_ }
}

foreach ($svc in $servicesToStart) {
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

Write-Host "Minimal sunrise ($Mode) done. Ports: $($portsToStart -join ', ')"
$validationDelaySec = 5
Write-Host "Waiting ${validationDelaySec}s for services to bind..."
Start-Sleep -Seconds $validationDelaySec
$checkScript = Join-Path $repoRoot "Scripts\check_calyx_core_services.ps1"
$updateScript = Join-Path $repoRoot "Scripts\update_state_checks.ps1"
if (Test-Path $checkScript) {
    $checkResult = & $checkScript 2>&1 | Select-Object -First 1
    Write-Host "Check result: $checkResult"
}
if (Test-Path $updateScript) {
    & $updateScript
}
Write-Host "Validation complete."
