# Setup OpenClaw with Station Calyx workspace
# Prerequisites: Node >= 22, npm/pnpm
# Use -UseOllama for local model (default), -UseOpenAI for GPT 5.1 (key from .env.cbo), -StartGateway to auto-start
# Run: .\Scripts\setup_openclaw_calyx.ps1 -UseOpenAI -StartGateway

param(
    [switch]$InstallOnly = $false,
    [switch]$SkipOnboard = $false,
    [switch]$UseOllama = $true,
    [switch]$UseOpenAI = $false,
    [switch]$StartGateway = $false,
    [string]$OllamaModel = "qwen2.5-coder:7b",
    [string]$OpenAIModel = "gpt-5.1"
)

$ErrorActionPreference = "Stop"
if ($env:CALYX_ALLOW_QUARANTINED_OPENCLAW -ne "1") {
    Write-Error "Refusing OpenClaw setup: OpenClaw is quarantined noncanonical and this setup path must not present as Station Calyx authority. Set CALYX_ALLOW_QUARANTINED_OPENCLAW=1 only for explicit historical/diagnostic use."
    exit 1
}
$repoRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = (Resolve-Path $repoRoot).Path
$approvedMemoryRoot = Join-Path $repoRoot "memory"

Write-Host "Station Calyx workspace: $repoRoot"
Write-Host "Approved memory root: $approvedMemoryRoot"

# Check Node
$nodeVersion = (node --version 2>$null) -replace 'v', ''
if (-not $nodeVersion) {
    Write-Error "Node not found. Install Node.js >= 22: https://nodejs.org/"
}
$major = [int]($nodeVersion -split '\.')[0]
if ($major -lt 22) {
    Write-Error "Node 22+ required. Current: $nodeVersion"
}
Write-Host "Node: $nodeVersion"

# Install OpenClaw
Write-Host "Installing OpenClaw..."
npm install -g openclaw@latest
if ($LASTEXITCODE -ne 0) {
    Write-Error "npm install failed"
}

# Ensure ~/.openclaw exists
$openclawHome = if ($env:OPENCLAW_HOME) { $env:OPENCLAW_HOME } else { Join-Path $env:USERPROFILE ".openclaw" }
$configPath = Join-Path $openclawHome "openclaw.json"
New-Item -ItemType Directory -Force -Path $openclawHome | Out-Null

# Build config - OpenClaw expects model as { primary: "provider/model" }, gateway.mode=local
if ($UseOpenAI) { $UseOllama = $false }
$modelRef = if ($UseOllama) { "ollama/$OllamaModel" } elseif ($UseOpenAI) { "openai/$OpenAIModel" } else { "anthropic/claude-sonnet-4-20250514" }
$modelVal = @{ primary = $modelRef }
# Subagent allowlist: CBO can spawn subagents; allow agent ids that can be targeted via sessions_spawn(agentId)
$subagentAllowList = @("cbo")
$configObj = @{
    gateway = @{ mode = "local" }
    agents = @{
        defaults = @{
            workspace = $repoRoot
            model = $modelVal
            subagents = @{
                allowAgents = $subagentAllowList
                maxSpawnDepth = 2
            }
        }
        list = @(
            @{
                id = "cbo"
                name = "CBO"
                workspace = $repoRoot
                model = $modelVal
                subagents = @{ allowAgents = $subagentAllowList }
            }
        )
    }
    channels = @{
        discord = @{}
    }
}

# Ollama: use implicit discovery (no models.providers.ollama) - set OLLAMA_API_KEY in .env

# WO_GOVERNANCE: Do NOT persist DISCORD_BOT_TOKEN to openclaw.json (reduce leak surface).
# Token must be sourced from env at runtime. OpenClaw reads from env when token not in config.
# Canonical Discord path is Calyx Gateway (Scripts\sunrise_calyx.ps1), not OpenClaw.

# Merge with existing if present (preserve agents.list, subagents)
if (Test-Path $configPath) {
    try {
        $existing = Get-Content $configPath -Raw | ConvertFrom-Json
        if (-not $UseOllama -and -not $UseOpenAI -and $existing.agents.defaults.model) {
            $configObj.agents.defaults.model = $existing.agents.defaults.model
        }
        if ($existing.agents.list -and $existing.agents.list.Count -gt 0) {
            $configObj.agents.list = $existing.agents.list
        }
        if ($existing.agents.defaults.subagents) {
            $configObj.agents.defaults.subagents = $existing.agents.defaults.subagents
        }
    } catch { }
}

# Ensure model is always object format for OpenClaw schema
if ($configObj.agents.defaults.model -is [string]) {
    $configObj.agents.defaults.model = @{ primary = $configObj.agents.defaults.model }
}

# Governed memory binding: all agent workspaces must resolve memory to the approved root.
$normalizedAgents = @()
foreach ($agent in $configObj.agents.list) {
    $agentObj = @{}
    foreach ($prop in $agent.PSObject.Properties) {
        $agentObj[$prop.Name] = $prop.Value
    }
    $agentObj.workspace = $repoRoot
    $normalizedAgents += $agentObj
}
$configObj.agents.list = $normalizedAgents
$configObj.agents.defaults.workspace = $repoRoot

if (-not (Test-Path $approvedMemoryRoot)) {
    Write-Warning "Approved memory root missing at $approvedMemoryRoot. Setup does not create memory roots implicitly."
}

# Ensure Ollama is running and model exists
if ($UseOllama) {
    $ollamaOk = $false
    try {
        $null = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 3
        $ollamaOk = $true
    } catch { }
    if (-not $ollamaOk) {
        Write-Warning "Ollama not responding at 127.0.0.1:11434. Start Ollama first (run Ollama app or: ollama serve)."
    } else {
        $list = ollama list 2>$null
        if ($list -notmatch $OllamaModel) {
            Write-Host "Pulling Ollama model $OllamaModel..."
            ollama pull $OllamaModel
        } else {
            Write-Host "Ollama model $OllamaModel ready."
        }
    }
}

# Save config
$configObj | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8
Write-Host "Config written: $configPath"

# .env for model keys
$envPath = Join-Path $openclawHome ".env"
$envCbo = Join-Path $repoRoot ".env.cbo"
if ($UseOllama) {
    $envContent = @"
# OpenClaw .env - Ollama local model
OLLAMA_API_KEY=ollama-local
"@
    if (Test-Path $envPath) {
        $existing = Get-Content $envPath -Raw
        if ($existing -notmatch "OLLAMA_API_KEY") {
            Add-Content $envPath "`nOLLAMA_API_KEY=ollama-local"
        }
    } else {
        $envContent | Set-Content $envPath -Encoding UTF8
    }
    Write-Host "OLLAMA_API_KEY set for local model discovery"
} elseif ($UseOpenAI) {
    # Use GPT 5.1 key from .env.cbo if present so OpenClaw shares the same key as CBO Core
    $openaiKey = $null
    if (Test-Path $envCbo) {
        $lines = Get-Content $envCbo -Encoding UTF8
        foreach ($line in $lines) {
            if ($line -match "^\s*OPENAI_API_KEY\s*=\s*(.+)$") {
                $openaiKey = $matches[1].Trim()
                break
            }
        }
    }
    if ($openaiKey) {
        $line = "OPENAI_API_KEY=$openaiKey"
        if (Test-Path $envPath) {
            $content = Get-Content $envPath -Raw -Encoding UTF8
            if ($content -match "OPENAI_API_KEY\s*=") {
                $content = $content -replace "OPENAI_API_KEY\s*=.*", $line
                Set-Content $envPath -Value $content -Encoding UTF8 -NoNewline
            } else {
                Add-Content $envPath "`n$line"
            }
        } else {
            Set-Content $envPath -Value "# OpenClaw .env - OpenAI (GPT 5.1)`n$line" -Encoding UTF8
        }
        Write-Host "OPENAI_API_KEY set in OpenClaw .env from .env.cbo (GPT $OpenAIModel)"
    } else {
        if (-not (Test-Path $envPath)) {
            Set-Content $envPath -Value "# OpenClaw .env - add OPENAI_API_KEY for GPT 5.1" -Encoding UTF8
        }
        Write-Host "Add OPENAI_API_KEY to $envPath (or set it in .env.cbo and re-run with -UseOpenAI)"
    }
} elseif (-not (Test-Path $envPath)) {
    @"
# OpenClaw .env - add your model API keys
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
"@ | Set-Content $envPath -Encoding UTF8
    Write-Host "Created $envPath - add ANTHROPIC_API_KEY or OPENAI_API_KEY"
}

if (-not $SkipOnboard -and -not $InstallOnly) {
    Write-Host "Running openclaw onboard..."
    & openclaw onboard
}

Write-Host ""
if ($UseOllama) {
    Write-Host "Model: ollama/$OllamaModel (local)"
} elseif ($UseOpenAI) {
    Write-Host "Model: openai/$OpenAIModel (key from .env.cbo or $envPath)"
} else {
    Write-Host "Add model API key to $envPath (ANTHROPIC_API_KEY or OPENAI_API_KEY)"
}
Write-Host "GOVERNED DISCORD: For Discord DM -> CBO routing, use Scripts\start_station_governed.ps1 (not OpenClaw)"
Write-Host "Stop Station Calyx discord_intake before starting OpenClaw (one Discord bot only)"
Write-Host "Before starting gateway, run pre-flight: Scripts\openclaw_preflight.ps1"
Write-Host "Bridge skill: skills\calyx-cbo-bridge\ (get_state, send_to_cbo). Docs: docs/OPENCLAW_CALYX_INTEGRATION.md"
Write-Host ""

if ($StartGateway) {
    Write-Host "Starting OpenClaw Gateway..."
    & $repoRoot\scripts\start_station_calyx.ps1 -UseOpenClaw
}
