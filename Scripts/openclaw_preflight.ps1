# OpenClaw + Station Calyx pre-flight checks.
# Run before starting the OpenClaw gateway to verify workspace, identity files, and Discord token.
# Usage: .\Scripts\openclaw_preflight.ps1 [-SkipCbo]

param(
    [switch]$SkipCbo = $false  # Skip CBO Core reachability check (e.g. when Calyx services are not started)
)

$ErrorActionPreference = "Stop"
if ($env:CALYX_ALLOW_QUARANTINED_OPENCLAW -ne "1") {
    Write-Error "Refusing OpenClaw preflight: OpenClaw is quarantined noncanonical and must not present as Station Calyx authority. Set CALYX_ALLOW_QUARANTINED_OPENCLAW=1 only for explicit historical/diagnostic use."
    exit 1
}
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) {
    $repoRoot = (Get-Location).Path
}

$openclawHome = if ($env:OPENCLAW_HOME) { $env:OPENCLAW_HOME } else { Join-Path $env:USERPROFILE ".openclaw" }
$configPath = Join-Path $openclawHome "openclaw.json"
$approvedMemoryRoot = Join-Path $repoRoot "memory"
$prohibitedMemoryRoots = @(
    (Join-Path $env:USERPROFILE ".openclaw\workspace-main\memory")
    (Join-Path $repoRoot "station_calyx\data\clawdbot\workspace\memory")
)

$fail = 0
$warn = 0

Write-Host "OpenClaw + Calyx pre-flight" -ForegroundColor Cyan
Write-Host ""

# 1. Node >= 22
$nodeVersion = (node --version 2>$null) -replace 'v', ''
if (-not $nodeVersion) {
    Write-Host "[FAIL] Node not found. Install Node.js >= 22." -ForegroundColor Red
    $fail++
} else {
    $major = [int]($nodeVersion -split '\.')[0]
    if ($major -lt 22) {
        Write-Host "[FAIL] Node 22+ required. Current: $nodeVersion" -ForegroundColor Red
        $fail++
    } else {
        Write-Host "[OK] Node $nodeVersion" -ForegroundColor Green
    }
}

# 2. OpenClaw config exists and workspace points at this repo
if (-not (Test-Path $configPath)) {
    Write-Host "[FAIL] OpenClaw config not found: $configPath. Run Scripts\setup_openclaw_calyx.ps1 first." -ForegroundColor Red
    $fail++
} else {
    try {
        $config = Get-Content $configPath -Raw | ConvertFrom-Json
        $ws = $config.agents.defaults.workspace
        if (-not $ws -or $ws -ne $repoRoot) {
            Write-Host "[FAIL] agents.defaults.workspace should be: $repoRoot. Current: $ws" -ForegroundColor Red
            $fail++
        } else {
            Write-Host "[OK] Workspace: $repoRoot" -ForegroundColor Green
        }
    } catch {
        Write-Host "[FAIL] Could not parse openclaw.json: $_" -ForegroundColor Red
        $fail++
    }
}

# 3. Identity and continuity files in workspace
foreach ($f in @("SOUL.md", "USER.md", "AGENTS.md")) {
    $p = Join-Path $repoRoot $f
    if (-not (Test-Path $p)) {
        Write-Host "[WARN] Missing $f in workspace." -ForegroundColor Yellow
        $warn++
    }
}
if ($warn -eq 0) {
    Write-Host "[OK] SOUL.md, USER.md, AGENTS.md present" -ForegroundColor Green
}

$memoryDir = $approvedMemoryRoot
if (-not (Test-Path $memoryDir)) {
    Write-Host "[FAIL] Approved memory root missing: $memoryDir. Missing roots must not be recreated implicitly." -ForegroundColor Red
    $fail++
} else {
    Write-Host "[OK] Approved memory root present: $memoryDir" -ForegroundColor Green
}

if (Test-Path (Join-Path $repoRoot "STATE.md")) {
    Write-Host "[OK] STATE.md present" -ForegroundColor Green
} else {
    Write-Host "[WARN] STATE.md missing. Run Scripts\update_state_checks.ps1 after starting Calyx Core." -ForegroundColor Yellow
    $warn++
}

# 3b. Governed memory binding
if (Test-Path $configPath) {
    try {
        $config = Get-Content $configPath -Raw | ConvertFrom-Json
        $defaultWorkspace = $config.agents.defaults.workspace
        if (-not $defaultWorkspace -or ((Join-Path $defaultWorkspace "memory") -ne $approvedMemoryRoot)) {
            Write-Host "[FAIL] agents.defaults.workspace must resolve memory to approved root: $approvedMemoryRoot. Current workspace: $defaultWorkspace" -ForegroundColor Red
            $fail++
        } else {
            Write-Host "[OK] Default agent memory root resolves to approved root" -ForegroundColor Green
        }

        if ($config.agents.list) {
            foreach ($agent in $config.agents.list) {
                $agentWorkspace = $agent.workspace
                if (-not $agentWorkspace) {
                    $agentWorkspace = $defaultWorkspace
                }
                if (-not $agentWorkspace) {
                    Write-Host "[FAIL] Agent '$($agent.id)' has no workspace and cannot be validated against the approved memory root." -ForegroundColor Red
                    $fail++
                    continue
                }
                $effectiveMemoryRoot = Join-Path $agentWorkspace "memory"
                if ($effectiveMemoryRoot -ne $approvedMemoryRoot) {
                    Write-Host "[FAIL] Agent '$($agent.id)' resolves memory outside approved root. Effective root: $effectiveMemoryRoot" -ForegroundColor Red
                    $fail++
                }
            }
        }

        foreach ($blockedRoot in $prohibitedMemoryRoots) {
            if (Test-Path $blockedRoot) {
                Write-Host "[WARN] Legacy or prohibited memory path present: $blockedRoot. Do not use it for OpenClaw memory binding." -ForegroundColor Yellow
                $warn++
            }
        }

        if ($config.plugins.entries.'memory-lancedb' -and $config.plugins.entries.'memory-lancedb'.enabled) {
            Write-Host "[FAIL] memory-lancedb must remain disabled until separately approved and receipted." -ForegroundColor Red
            $fail++
        }
    } catch {
        Write-Host "[FAIL] Could not validate governed memory binding: $_" -ForegroundColor Red
        $fail++
    }
}

# 4. Discord token
$token = $env:DISCORD_BOT_TOKEN
if (-not $token) {
    $token = [System.Environment]::GetEnvironmentVariable("DISCORD_BOT_TOKEN", "User")
}
if (-not $token -or $token.Length -lt 10) {
    Write-Host "[FAIL] DISCORD_BOT_TOKEN not set or too short. Set it (User env or session)." -ForegroundColor Red
    $fail++
} else {
    Write-Host "[OK] DISCORD_BOT_TOKEN set" -ForegroundColor Green
}

# 5. CBO Core reachable (optional)
if (-not $SkipCbo) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:7778/state" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) {
            Write-Host "[OK] CBO Core reachable (GET /state)" -ForegroundColor Green
        } else {
            Write-Host "[WARN] CBO Core returned $($r.StatusCode)" -ForegroundColor Yellow
            $warn++
        }
    } catch {
        Write-Host "[WARN] CBO Core not reachable. Start Calyx Core for bridge skill (Scripts\start_calyx_core_services.ps1)." -ForegroundColor Yellow
        $warn++
    }
} else {
    Write-Host "[SKIP] CBO Core check skipped" -ForegroundColor Gray
}

Write-Host ""
if ($fail -gt 0) {
    Write-Host "Pre-flight failed with $fail error(s). Fix and re-run." -ForegroundColor Red
    exit 1
}
if ($warn -gt 0) {
    Write-Host "Pre-flight passed with $warn warning(s). You can start the gateway." -ForegroundColor Yellow
} else {
    Write-Host "Pre-flight passed. Start gateway: Scripts\start_station_calyx.ps1 -UseOpenClaw" -ForegroundColor Green
}
exit 0
