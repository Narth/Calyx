# Scoped restart for Station Calyx services.
# Usage: .\Scripts\restart_service.ps1 -Service <name>

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("dev_harness", "cbo_core", "avatar_web", "telemetry_gateway", "station_health_loop", "service_failure_watch", "navigator_triage_loop", "energy_churn_cp9_loop", "cp6_cp7_loop", "bridge_overseer", "cli_avatar")]
    [string]$Service
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) { $repoRoot = (Get-Location).Path }
Set-Location $repoRoot

$truthHelper = Join-Path $repoRoot "Scripts\runtime_truth_contract.ps1"
if (-not (Test-Path $truthHelper)) {
    Write-Error "runtime_truth_contract.ps1 not found: $truthHelper"
    exit 1
}
. $truthHelper

$venvPython = Join-Path $repoRoot ".venv_cbohub311\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Error "Venv not found: $venvPython"
    exit 1
}

function Stop-ProcessOnPort {
    param([int]$Port)
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($conn -and $conn.OwningProcess) {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    } catch { }
}

function Stop-PythonProcessByPattern {
    param([string]$Pattern)
    Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
            if ($cmd -match $Pattern) {
                Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
            }
        } catch { }
    }
}

function Stop-LoopScript {
    param([string]$StopFile)
    if (Test-Path $StopFile) { Remove-Item $StopFile -Force -ErrorAction SilentlyContinue }
    New-Item -ItemType File -Path $StopFile -Force | Out-Null
    Start-Sleep -Seconds 2
}

function Start-LoopScript {
    param(
        [string]$ScriptPath,
        [string]$StopFile
    )
    if (Test-Path $StopFile) { Remove-Item $StopFile -Force -ErrorAction SilentlyContinue }
    Start-Process powershell -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $ScriptPath -WorkingDirectory $repoRoot -WindowStyle Hidden
}

$serviceMap = @{
    dev_harness = @{ kind = "uvicorn"; port = 7777; host = "127.0.0.1"; module = "cbo_hub.dev_harness.app:app" }
    cbo_core = @{ kind = "uvicorn"; port = 7778; host = "127.0.0.1"; module = "cbo_hub.cbo_core.app:app" }
    avatar_web = @{ kind = "uvicorn"; port = 7780; host = "127.0.0.1"; module = "cbo_hub.avatar_web.app:app" }
    telemetry_gateway = @{ kind = "uvicorn"; port = 7781; host = "0.0.0.0"; module = "cbo_hub.telemetry_gateway.app:app" }
    station_health_loop = @{ kind = "loop"; script = (Join-Path $repoRoot "Scripts\station_health_loop.ps1"); stop = (Join-Path $repoRoot "runtime\station_health.stop") }
    service_failure_watch = @{ kind = "loop"; script = (Join-Path $repoRoot "Scripts\service_failure_watch.ps1"); stop = (Join-Path $repoRoot "runtime\service_failure_watch.stop") }
    navigator_triage_loop = @{ kind = "loop"; script = (Join-Path $repoRoot "Scripts\navigator_triage_loop.ps1"); stop = (Join-Path $repoRoot "runtime\navigator_triage.stop") }
    energy_churn_cp9_loop = @{ kind = "loop"; script = (Join-Path $repoRoot "Scripts\energy_churn_cp9_loop.ps1"); stop = (Join-Path $repoRoot "runtime\energy_churn_cp9.stop") }
    cp6_cp7_loop = @{ kind = "loop"; script = (Join-Path $repoRoot "Scripts\cp6_cp7_loop.ps1"); stop = (Join-Path $repoRoot "runtime\cp6_cp7.stop") }
    bridge_overseer = @{ kind = "python_module"; module = "calyx.cbo.bridge_overseer"; pattern = "calyx\.cbo\.bridge_overseer"; window = "Hidden" }
    cli_avatar = @{ kind = "python_module"; module = "cbo_hub.cli_avatar.main"; pattern = "cbo_hub\.cli_avatar\.main"; window = "Normal" }
}

$svc = $serviceMap[$Service]
if (-not $svc) {
    Write-Error "Unsupported service: $Service"
    exit 1
}
if ($Service -eq "bridge_overseer" -and $env:CALYX_ALLOW_QUARANTINED_BRIDGE_OVERSEER -ne "1") {
    Write-Error "Refusing restart: bridge_overseer is quarantined noncanonical and not canonical Station authority. Set CALYX_ALLOW_QUARANTINED_BRIDGE_OVERSEER=1 only for explicit historical/diagnostic use."
    exit 1
}

$restartBeginReceipt = Write-RuntimeTruthTransition -RepoRoot $repoRoot -Transition "scoped_restart_begin" -Reason $Service -Surfaces @($Service)
Write-Host "Runtime truth transition receipt: $restartBeginReceipt"

switch ($svc.kind) {
    "uvicorn" {
        Stop-ProcessOnPort -Port $svc.port
    }
    "loop" {
        Stop-LoopScript -StopFile $svc.stop
    }
    "python_module" {
        Stop-PythonProcessByPattern -Pattern $svc.pattern
    }
}

if (Test-Path (Join-Path $repoRoot "Scripts\update_state_checks.ps1")) {
    & (Join-Path $repoRoot "Scripts\update_state_checks.ps1") | Out-Null
}

switch ($svc.kind) {
    "uvicorn" {
        Start-Process -FilePath $venvPython -ArgumentList "-B", "-m", "uvicorn", $svc.module, "--host", $svc.host, "--port", $svc.port -WorkingDirectory $repoRoot -WindowStyle Normal
    }
    "loop" {
        Start-LoopScript -ScriptPath $svc.script -StopFile $svc.stop
    }
    "python_module" {
        Start-Process -FilePath $venvPython -ArgumentList "-B", "-m", $svc.module -WorkingDirectory $repoRoot -WindowStyle $svc.window
    }
}

Start-Sleep -Seconds 6
if (Test-Path (Join-Path $repoRoot "Scripts\update_state_checks.ps1")) {
    & (Join-Path $repoRoot "Scripts\update_state_checks.ps1") | Out-Null
}

$restartDoneReceipt = Write-RuntimeTruthTransition -RepoRoot $repoRoot -Transition "scoped_restart_complete" -Reason $Service -Surfaces @($Service)
Write-Host "Runtime truth transition receipt: $restartDoneReceipt"
Write-Host "Restart complete for $Service."
