# Setup OpenClaw with Station Calyx workspace
# Prerequisites: Node >= 22, npm/pnpm
# Use -UseOllama for local 7B code model (Ollama); -StartGateway to auto-start
# Run: .\scripts\setup_openclaw_calyx.ps1 -UseOllama -StartGateway

param(
    [switch]$InstallOnly = $false,
    [switch]$SkipOnboard = $false,
    [switch]$UseOllama = $true,
    [switch]$StartGateway = $false,
    [string]$OllamaModel = "qwen2.5-coder:7b"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = (Resolve-Path $repoRoot).Path

Write-Host "Station Calyx workspace: $repoRoot"

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
$modelRef = if ($UseOllama) { "ollama/$OllamaModel" } else { "anthropic/claude-sonnet-4-20250514" }
$modelVal = if ($UseOllama) { @{ primary = $modelRef } } else { $modelRef }
$configObj = @{
    gateway = @{ mode = "local" }
    agents = @{
        defaults = @{
            workspace = $repoRoot
            model = $modelVal
        }
    }
    channels = @{
        discord = @{}
    }
}

# Ollama: use implicit discovery (no models.providers.ollama) - set OLLAMA_API_KEY in .env

# Discord token from env
$token = $env:DISCORD_BOT_TOKEN
if (-not $token) {
    $token = [System.Environment]::GetEnvironmentVariable("DISCORD_BOT_TOKEN", "User")
}
if ($token) {
    $configObj.channels.discord.token = $token
}

# Merge with existing if present (preserve token if not in env)
if (Test-Path $configPath) {
    try {
        $existing = Get-Content $configPath -Raw | ConvertFrom-Json
        if (-not $UseOllama -and $existing.agents.defaults.model) {
            $configObj.agents.defaults.model = $existing.agents.defaults.model
        }
        if ($existing.channels.discord.token -and -not $token) {
            $configObj.channels.discord.token = $existing.channels.discord.token
        }
    } catch { }
}

# Ensure model is always object format for OpenClaw schema
if ($configObj.agents.defaults.model -is [string]) {
    $configObj.agents.defaults.model = @{ primary = $configObj.agents.defaults.model }
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
} else {
    Write-Host "Add model API key to $envPath (ANTHROPIC_API_KEY or OPENAI_API_KEY)"
}
Write-Host "Stop Station Calyx discord_intake before starting OpenClaw (one Discord bot only)"
Write-Host "Docs: docs/OPENCLAW_CALYX_INTEGRATION.md"
Write-Host ""

if ($StartGateway) {
    Write-Host "Starting OpenClaw Gateway..."
    & $repoRoot\scripts\start_station_calyx.ps1 -UseOpenClaw
}
