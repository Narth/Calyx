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

$truthHelper = Join-Path $repoRoot "Scripts\runtime_truth_contract.ps1"
if (-not (Test-Path $truthHelper)) {
    Write-Error "runtime_truth_contract.ps1 not found: $truthHelper"
    exit 1
}
. $truthHelper

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

function Test-FreshStationHealth {
    param(
        [string]$HealthPath,
        [int]$WaitSec = 15
    )
    for ($i = 0; $i -le $WaitSec; $i++) {
        if (Test-Path -LiteralPath $HealthPath -PathType Leaf) {
            try {
                $healthJson = Read-JsonArtifact -Path $HealthPath
                $freshness = Get-ArtifactFreshness -ContractName "station_health" -Artifact $healthJson -Path $HealthPath
                if ($freshness.is_fresh) { return $true }
            } catch { }
        }
        if ($i -lt $WaitSec) { Start-Sleep -Seconds 1 }
    }
    return $false
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

# Boot Evidence Pre-Network Gate (V1): commit bundle before any service bind/connect.
$bootSessionId = "boot-$([guid]::NewGuid().ToString())"
$env:CALYX_BOOT_SESSION_ID = $bootSessionId
Write-Host "Boot evidence: committing pre-network bundle (session=$bootSessionId)..."
$bootCommitResult = & $venvPython -m calyx.kernel.boot_evidence commit --source "sunrise.start_calyx_core_services" --boot-session-id $bootSessionId 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Boot evidence commit failed. Sunrise fail-closed. $bootCommitResult"
    exit 1
}
Write-Host "Boot evidence committed."

# WO_BOOT_CONTEXT_BUDGET_V1: evaluate context-missing budget during boot and force observe mode on exceedance.
$bootBudgetRaw = & $venvPython -m calyx.kernel.boot_context_budget --since-minutes 30 --enforce 2>&1
$bootBudget = $null
try { $bootBudget = ($bootBudgetRaw | Out-String) | ConvertFrom-Json } catch { }
if (-not $bootBudget) {
    Write-Error "Boot context budget evaluation failed to parse. Sunrise fail-closed."
    exit 1
}
$bootContextTotal = [int]$bootBudget.boot_context_missing_total
$bootContextByComponent = ($bootBudget.boot_context_missing_by_component | ConvertTo-Json -Compress)
$bootBudgetPass = [bool]$bootBudget.budget_pass
$bootBudgetStatus = if ($bootBudgetPass) { "pass" } else { "fail" }
Write-Host "Boot context budget: boot_context_missing_total=$bootContextTotal boot_context_missing_by_component=$bootContextByComponent budget_status=$bootBudgetStatus"

$updateScript = Join-Path $repoRoot "Scripts\update_state_checks.ps1"
$healthPath = Join-Path $repoRoot "runtime\station_health.json"
if (Test-Path $updateScript) {
    & $updateScript -ForceStale -StaleReason "sunrise_in_progress" | Out-Null
}
$sunriseBeginReceipt = Write-RuntimeTruthTransition -RepoRoot $repoRoot -Transition "sunrise_begin" -Reason "sunrise_in_progress" -Surfaces @("STATE.md", "runtime/station_heartbeat.json", "runtime/service_runtime_snapshot.json", "runtime/runtime_topology_snapshot.json", "outgoing/*.lock")
Write-Host "Runtime truth transition receipt: $sunriseBeginReceipt"

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

# Ollama CPU affinity — 4 cores to llamas (4-7), 4 to Station Calyx (0-3). Run if Ollama is up.
$affinityScript = Join-Path $repoRoot "Scripts\set_ollama_affinity.ps1"
if (Test-Path $affinityScript) {
    & $affinityScript 2>&1 | ForEach-Object { Write-Host $_ }
}

# Station health loop — live CPU/RAM/entropy for STATE, heartbeats, BloomOS. Part of Station home.
$stopFile = Join-Path $repoRoot "runtime\station_health.stop"
$loopScript = Join-Path $repoRoot "Scripts\station_health_loop.ps1"
if (Test-Path $loopScript) {
    New-Item -ItemType File -Path $stopFile -Force | Out-Null; Start-Sleep -Seconds 2
    if (Test-Path $stopFile) { Remove-Item $stopFile -Force -ErrorAction SilentlyContinue }
    Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',$loopScript -WindowStyle Hidden
    Write-Host "[Station health loop] Started (background). Stop: New-Item -ItemType File -Path runtime\station_health.stop -Force"
} else {
    Write-Warning "station_health_loop.ps1 not found; CPU/RAM in heartbeats may be stale."
}

# Service failure watcher — independent failure detection and canonical change/risk flagging.
$failureWatchStopFile = Join-Path $repoRoot "runtime\service_failure_watch.stop"
$failureWatchScript = Join-Path $repoRoot "Scripts\service_failure_watch.ps1"
if (Test-Path $failureWatchScript) {
    New-Item -ItemType File -Path $failureWatchStopFile -Force | Out-Null; Start-Sleep -Seconds 1
    if (Test-Path $failureWatchStopFile) { Remove-Item $failureWatchStopFile -Force -ErrorAction SilentlyContinue }
    Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',$failureWatchScript -WindowStyle Hidden
    Write-Host "[Service failure watcher] Started (background). Stop: New-Item -ItemType File -Path runtime\service_failure_watch.stop -Force"
} else {
    Write-Warning "service_failure_watch.ps1 not found; independent service failure detection will be unavailable."
}

# Navigator + Triage loop — ship's wheel and medical unit. Cadence and health for BloomOS; CBO gates on pause.
$navTriageStopFile = Join-Path $repoRoot "runtime\navigator_triage.stop"
$navTriageScript = Join-Path $repoRoot "Scripts\navigator_triage_loop.ps1"
if (Test-Path $navTriageScript) {
    New-Item -ItemType File -Path $navTriageStopFile -Force | Out-Null; Start-Sleep -Seconds 1
    if (Test-Path $navTriageStopFile) { Remove-Item $navTriageStopFile -Force -ErrorAction SilentlyContinue }
    Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',$navTriageScript -WindowStyle Hidden
    Write-Host "[Navigator+Triage loop] Started (background). Stop: New-Item -ItemType File -Path runtime\navigator_triage.stop -Force"
} else {
    Write-Warning "navigator_triage_loop.ps1 not found; cadence/health gates may be stale."
}

# Energy Churn + CP9 Auto-Tuner loop — trend analysis and tuning recommendations (every 5 min).
$ec9StopFile = Join-Path $repoRoot "runtime\energy_churn_cp9.stop"
$ec9Script = Join-Path $repoRoot "Scripts\energy_churn_cp9_loop.ps1"
if (Test-Path $ec9Script) {
    New-Item -ItemType File -Path $ec9StopFile -Force | Out-Null; Start-Sleep -Seconds 1
    if (Test-Path $ec9StopFile) { Remove-Item $ec9StopFile -Force -ErrorAction SilentlyContinue }
    Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',$ec9Script -WindowStyle Hidden
    Write-Host "[Energy Churn + CP9 loop] Started (background). Stop: New-Item -ItemType File -Path runtime\energy_churn_cp9.stop -Force"
} else {
    Write-Warning "energy_churn_cp9_loop.ps1 not found; energy churn and CP9 tuning may be stale."
}

# CP6 Sociologist + CP7 Chronicler loop — Phase 3: harmony and drift (every 10 min).
$cp67StopFile = Join-Path $repoRoot "runtime\cp6_cp7.stop"
$cp67Script = Join-Path $repoRoot "Scripts\cp6_cp7_loop.ps1"
if (Test-Path $cp67Script) {
    New-Item -ItemType File -Path $cp67StopFile -Force | Out-Null; Start-Sleep -Seconds 1
    if (Test-Path $cp67StopFile) { Remove-Item $cp67StopFile -Force -ErrorAction SilentlyContinue }
    Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',$cp67Script -WindowStyle Hidden
    Write-Host "[CP6+CP7 loop] Started (background). Stop: New-Item -ItemType File -Path runtime\cp6_cp7.stop -Force"
} else {
    Write-Warning "cp6_cp7_loop.ps1 not found; harmony/drift signals may be stale."
}

# CBO Bridge Overseer — Reflect → Plan → Act → Critique loop (4-min heartbeat). Background.
$bridgeOverseerModule = "calyx.cbo.bridge_overseer"
Start-Process -FilePath $venvPython -ArgumentList "-B", "-m", $bridgeOverseerModule -WorkingDirectory $repoRoot -WindowStyle Hidden
Write-Host "[CBO Bridge Overseer] Started (background). Sunset will stop it."

# CLI Avatar — interactive terminal chat. Opens in new window for operator use.
# Changes to cli_avatar require sunset → sunrise to deploy (see docs/operations/CANONICAL_OPS_INDEX.md).
$cliAvatarModule = "cbo_hub.cli_avatar.main"
Start-Process -FilePath $venvPython -ArgumentList "-B", "-m", $cliAvatarModule -WorkingDirectory $repoRoot -WindowStyle Normal
Write-Host "[CLI Avatar] Started (new window). Close when done; sunset will stop it if still running."

# R1/R2: Start Discord Gateway (canonical boot path). No hardcoded IDs (governance hygiene).
$gatewayStarted = $false
$gatewayPid = $null
if (-not $SkipGateway) {
    function Get-DiscordIdsFromFile {
        param([string]$IdsPath)
        if (-not (Test-Path $IdsPath)) { return $null }
        $content = Get-Content $IdsPath -Raw -ErrorAction SilentlyContinue
        if (-not $content) { return $null }
        $channels = @(); $users = @()
        foreach ($line in ($content -split "`n")) {
            if ($line -match "Station Health Channel ID[^\d]*(\d{17,20})") { $channels += $matches[1] }
            if ($line -match "Authorized User ID[^\d]*(\d{17,20})") { $users += $matches[1] }
        }
        return @{ channels = $channels; users = $users }
    }
    $idsPath = Join-Path $repoRoot "DISCORD_IDS.md"
    $idsFromFile = Get-DiscordIdsFromFile -IdsPath $idsPath

    if (-not $env:DISCORD_BOT_TOKEN) {
        $env:DISCORD_BOT_TOKEN = [System.Environment]::GetEnvironmentVariable("DISCORD_BOT_TOKEN", "User")
    }
    if (-not $env:DISCORD_HEARTBEAT_USER_ID) {
        $env:DISCORD_HEARTBEAT_USER_ID = [System.Environment]::GetEnvironmentVariable("DISCORD_HEARTBEAT_USER_ID", "User")
    }
    if (-not $env:DISCORD_HEARTBEAT_USER_ID -and $idsFromFile -and $idsFromFile.users.Count -gt 0) {
        $env:DISCORD_HEARTBEAT_USER_ID = $idsFromFile.users[0]
    }
    if (-not $env:DISCORD_CHANNEL_ALLOWLIST) {
        $env:DISCORD_CHANNEL_ALLOWLIST = [System.Environment]::GetEnvironmentVariable("DISCORD_CHANNEL_ALLOWLIST", "User")
    }
    if (-not $env:DISCORD_CHANNEL_ALLOWLIST -and $idsFromFile -and $idsFromFile.channels.Count -gt 0) {
        $env:DISCORD_CHANNEL_ALLOWLIST = $idsFromFile.channels -join ","
    }
    if (-not $env:DISCORD_AUTHORIZED_USERS) {
        $env:DISCORD_AUTHORIZED_USERS = [System.Environment]::GetEnvironmentVariable("DISCORD_AUTHORIZED_USERS", "User")
    }
    if (-not $env:DISCORD_AUTHORIZED_USERS -and $idsFromFile -and $idsFromFile.users.Count -gt 0) {
        $env:DISCORD_AUTHORIZED_USERS = $idsFromFile.users -join ","
    }

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
        if (-not $env:DISCORD_CHANNEL_ALLOWLIST -or -not $env:DISCORD_AUTHORIZED_USERS) {
            Write-Error "Discord Gateway requires DISCORD_CHANNEL_ALLOWLIST and DISCORD_AUTHORIZED_USERS. Set env vars or create DISCORD_IDS.md with 'Station Health Channel ID' and 'Authorized User ID'."
            exit 1
        }
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
$checkResult = "unknown"
$checkExitCode = 1
if (Test-Path $checkScript) {
    $checkOutput = & $checkScript 2>&1
    $checkExitCode = $LASTEXITCODE
    $checkResult = $checkOutput | Select-Object -First 1
    Write-Host "Check result: $checkResult"
}
$healthFresh = Test-FreshStationHealth -HealthPath $healthPath -WaitSec 15
$validationPassed = ($checkExitCode -eq 0) -and $healthFresh
if (Test-Path $updateScript) {
    if ($validationPassed) {
        & $updateScript | Out-Null
        $sunriseValidatedReceipt = Write-RuntimeTruthTransition -RepoRoot $repoRoot -Transition "sunrise_validated" -Reason "post_start_validation_passed" -Surfaces @("STATE.md", "runtime/station_heartbeat.json", "runtime/service_runtime_snapshot.json", "runtime/runtime_topology_snapshot.json") -Extra @{ checks = $checkResult; health_fresh = $healthFresh }
        Write-Host "Runtime truth transition receipt: $sunriseValidatedReceipt"
    } else {
        & $updateScript -ForceStale -StaleReason "sunrise_validation_failed" | Out-Null
        $sunriseFailedReceipt = Write-RuntimeTruthTransition -RepoRoot $repoRoot -Transition "sunrise_validation_failed" -Reason "validation_failed" -Surfaces @("STATE.md", "runtime/station_heartbeat.json", "runtime/service_runtime_snapshot.json", "runtime/runtime_topology_snapshot.json") -Extra @{ checks = $checkResult; health_fresh = $healthFresh }
        Write-Host "Runtime truth transition receipt: $sunriseFailedReceipt"
    }
} else {
    Write-Warning "update_state_checks.ps1 not found; STATE.md not refreshed."
}
if (-not $validationPassed) {
    Write-Error "Sunrise validation failed. checks=$checkResult health_fresh=$healthFresh"
    exit 1
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
    services = @("dev_harness", "cbo_core", "avatar_web", "telemetry_gateway", "station_health_loop", "navigator_triage_loop", "energy_churn_cp9_loop", "cp6_cp7_loop", "bridge_overseer", "cli_avatar", "discord_gateway")
    discord_gateway_started = $gatewayStarted
    discord_gateway_pid = $gatewayPid
    external_emitter_gate = "passed"
    openclaw_gateway_task_state = $openclawTaskState
    audit_health_passed = $auditHealthPassed
    checks = $checkResult
    boot_context_missing_total = $bootContextTotal
    boot_context_missing_by_component = $bootBudget.boot_context_missing_by_component
    boot_context_budget_pass = $bootBudgetPass
    boot_context_budget_fail_reasons = $bootBudget.budget_fail_reasons
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
