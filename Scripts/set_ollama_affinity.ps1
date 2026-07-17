# Set Ollama process CPU affinity to cores 4-7 (half of 8-core system).
# Station Calyx + everything else uses cores 0-3. Prevents Ollama from maxing all cores.
# Usage: .\Scripts\set_ollama_affinity.ps1 [-OllamaCores 4-7]
# Run at sunrise; if Ollama not yet started, run manually after starting Ollama.
# See: docs/HARDWARE_OPTIMIZATION.md

param(
    [string]$OllamaCores = "4-7"  # Cores for Ollama; "4-7" = mask 0xF0 on 8-core
)

$ErrorActionPreference = "SilentlyContinue"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) { $repoRoot = (Get-Location).Path }

# Mask for cores 4-7 on 8-core: 0xF0 (binary 11110000)
$mask = 0xF0
if ($OllamaCores -eq "0-3") { $mask = 0x0F }

$procs = Get-Process -Name ollama -ErrorAction SilentlyContinue
if (-not $procs) {
    Write-Host "[Ollama affinity] Ollama not running. Run this script after starting Ollama, or start Ollama before sunrise." -ForegroundColor Yellow
    exit 0
}

$count = 0
foreach ($p in @($procs)) {
    try {
        $p.ProcessorAffinity = [IntPtr]$mask
        $count++
    } catch {
        Write-Host "[Ollama affinity] Failed to set PID $($p.Id): $($_.Exception.Message)" -ForegroundColor Red
    }
}

if ($count -gt 0) {
    Write-Host "[Ollama affinity] Set $count process(es) to cores $OllamaCores (mask 0x$($mask.ToString('X')))" -ForegroundColor Green
}

exit 0
