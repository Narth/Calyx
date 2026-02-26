# WO_SUNRISE_CANONICAL_BOOTPATH_DISCORD_GATEWAY_V1: Canonical Sunrise — Dev Harness, CBO Core, Avatar Web, Telemetry Gateway, Discord Gateway.
# Boot order: External emitter gate → Preflight → Core services → Discord Gateway → Verify → Receipt.
# Usage: .\Scripts\start_calyx_core_services.ps1 [-StopFirst] [-SkipGateway]
# -StopFirst: stop any process on core ports before starting.
# -SkipGateway: core services only (debug); Discord Gateway not started.

param(
    [switch]$StopFirst = $false,
    [switch]$SkipGateway = $false
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

# R2: External emitter gate (must pass before any services)
Write-Host "Sunrise: external emitter gate..."
$gateResult = & $venvPython -m calyx.kernel.external_emitter_gate 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "External emitter gate failed. OpenClaw or denylist emitter detected. Stop/disable before sunrise. $gateResult"
    exit 1
}
Write-Host "Gate OK: no external emitters."

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

# WO_VERIFIED_CLAIMS_LEDGER_V1: Sunrise preflight — verify required dirs exist
$preflightDirs = @(
    (Join-Path $repoRoot "runtime\ledger"),
    (Join-Path $repoRoot "runtime\receipts"),
    (Join-Path $repoRoot "runtime\receipts\canonical"),
    (Join-Path $repoRoot "runtime\receipts\security"),
    (Join-Path $repoRoot "runtime\receipts\budget")
)
foreach ($d in $preflightDirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
    }
    if (-not (Test-Path $d -PathType Container)) {
        Write-Error "Preflight failed: required dir missing: $d"
        exit 1
    }
}
Write-Host "Preflight OK: runtime/ledger, runtime/receipts, runtime/receipts/canonical, runtime/receipts/security, runtime/receipts/budget"

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

# R1/R2: Start Discord Gateway (canonical boot path)
$gatewayStarted = $false
$gatewayPid = $null
if (-not $SkipGateway) {
    if (-not $env:DISCORD_BOT_TOKEN) {
        $env:DISCORD_BOT_TOKEN = [System.Environment]::GetEnvironmentVariable("DISCORD_BOT_TOKEN", "User")
    }
    if (-not $env:DISCORD_HEARTBEAT_USER_ID) {
        $env:DISCORD_HEARTBEAT_USER_ID = [System.Environment]::GetEnvironmentVariable("DISCORD_HEARTBEAT_USER_ID", "User")
    }
    if (-not $env:DISCORD_HEARTBEAT_USER_ID) { $env:DISCORD_HEARTBEAT_USER_ID = "315642751419023371" }
    if (-not $env:DISCORD_CHANNEL_ALLOWLIST) {
        $env:DISCORD_CHANNEL_ALLOWLIST = [System.Environment]::GetEnvironmentVariable("DISCORD_CHANNEL_ALLOWLIST", "User")
    }
    if (-not $env:DISCORD_CHANNEL_ALLOWLIST) { $env:DISCORD_CHANNEL_ALLOWLIST = "1465903939659632807" }
    if (-not $env:DISCORD_AUTHORIZED_USERS) {
        $env:DISCORD_AUTHORIZED_USERS = [System.Environment]::GetEnvironmentVariable("DISCORD_AUTHORIZED_USERS", "User")
    }
    if (-not $env:DISCORD_AUTHORIZED_USERS) { $env:DISCORD_AUTHORIZED_USERS = "315642751419023371" }

    $existingGateway = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
            $cmd -match "calyx\.cbo\.discord_gateway"
        } catch { $false }
    }
    if ($existingGateway) {
        Write-Host "[Discord Gateway] Already running (PID $($existingGateway[0].Id))."
        $gatewayStarted = $true
        $gatewayPid = $existingGateway[0].Id
    } elseif ($env:DISCORD_BOT_TOKEN) {
        Write-Host "[Discord Gateway] Starting..."
        Start-Process -FilePath $venvPython -ArgumentList "-m", "calyx.cbo.discord_gateway" `
            -WorkingDirectory $repoRoot -WindowStyle Normal
        Start-Sleep -Seconds 5
        $gatewayProcs = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
            try {
                $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
                $cmd -match "calyx\.cbo\.discord_gateway"
            } catch { $false }
        }
        if ($gatewayProcs) {
            $gatewayStarted = $true
            $gatewayPid = $gatewayProcs[0].Id
            Write-Host "[Discord Gateway] Started (PID $gatewayPid)."
        } else {
            Write-Error "R4: Discord Gateway failed to start. Sunrise fail-closed."
            $receiptDir = Join-Path $repoRoot "runtime\receipts"
            $receiptPath = Join-Path $receiptDir "sunrise_receipt__$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
            @{
                ts_utc = (Get-Date).ToUniversalTime().ToString("o")
                wo = "WO_SUNRISE_CANONICAL_BOOTPATH_DISCORD_GATEWAY_V1"
                status = "failed"
                gateway_started = $false
                reason = "discord_gateway_failed_to_start"
                audit_events = @("audit.runtime.component.failed", "audit.runtime.singularity_violation")
            } | ConvertTo-Json | Set-Content $receiptPath -Encoding UTF8
            exit 1
        }
    } else {
        Write-Warning "DISCORD_BOT_TOKEN not set. Discord Gateway not started (SkipGateway implied)."
    }
}

# Allow services to bind, then run health check and refresh STATE
$validationDelaySec = 10
Write-Host "Waiting $validationDelaySec s for services to bind, then running validation..."
Start-Sleep -Seconds $validationDelaySec
$checkScript = Join-Path $repoRoot "Scripts\check_calyx_core_services.ps1"
$updateScript = Join-Path $repoRoot "Scripts\update_state_checks.ps1"
$checkResult = "unknown"
if (Test-Path $checkScript) {
    $checkResult = & $checkScript 2>&1 | Select-Object -First 1
    Write-Host "Check result: $checkResult"
}
if (Test-Path $updateScript) {
    & $updateScript
} else {
    Write-Warning "update_state_checks.ps1 not found; STATE.md not refreshed."
}

# R4: Post-sunrise audit_health (sender singularity, no external emitters)
$auditHealthPassed = $null  # null = skipped
if (-not $SkipGateway -and $gatewayStarted) {
    $auditScript = Join-Path $repoRoot "Scripts\audit_health.py"
    if (Test-Path $auditScript) {
        Write-Host "Post-sunrise: audit_health (--since-minutes 5)..."
        & $venvPython $auditScript --since-minutes 5 2>&1 | ForEach-Object { Write-Host $_ }
        $auditHealthPassed = ($LASTEXITCODE -eq 0)
        if (-not $auditHealthPassed) {
            Write-Host "audit_health failed. Sunrise fail-closed (sender identity / external emitter check)."
            exit 1
        }
    }
}

# R3: Sunrise receipt
$receiptDir = Join-Path $repoRoot "runtime\receipts"
$receiptPath = Join-Path $receiptDir "sunrise_receipt__$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$openclawTaskState = "unknown"
try {
    $ocTask = Get-ScheduledTask -TaskName "OpenClaw Gateway" -ErrorAction SilentlyContinue
    $openclawTaskState = if ($ocTask) { $ocTask.State.ToString() } else { "not_found" }
} catch { }
$receipt = @{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    wo = "WO_SUNRISE_CANONICAL_BOOTPATH_DISCORD_GATEWAY_V1"
    status = if ($gatewayStarted -or $SkipGateway) { "ok" } else { "degraded" }
    services = @("dev_harness", "cbo_core", "avatar_web", "telemetry_gateway", "discord_gateway")
    discord_gateway_started = $gatewayStarted
    discord_gateway_pid = $gatewayPid
    external_emitter_gate = "passed"
    openclaw_gateway_task_state = $openclawTaskState
    audit_health_passed = $auditHealthPassed
    checks = $checkResult
}
$receipt | ConvertTo-Json | Set-Content $receiptPath -Encoding UTF8
Write-Host "Sunrise receipt: $receiptPath"

# R4: Fail closed if gateway expected but not started
if (-not $SkipGateway -and -not $env:DISCORD_BOT_TOKEN) {
    Write-Warning "Discord Gateway skipped (no token). Sunrise degraded."
} elseif (-not $SkipGateway -and -not $gatewayStarted) {
    Write-Error "Discord Gateway failed to start. Sunrise fail-closed."
    exit 1
}

Write-Host "Validation complete."
