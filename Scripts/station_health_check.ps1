# Station Health Check - system-wide hardware, safety, utility.
# Run before heavy work (LLM, tool loops, builds) to avoid CPU overload and thermal stress.
# Shows top CPU consumers, then runs build_safety_check.ps1.
# Usage: .\Scripts\station_health_check.ps1 [-RequireCoreServices]
# Exit: 0 = pass, 1 = warn (proceed with caution), 2 = fail (do not add load).
# See: docs/planning/BUILD_SAFETY_CHECK.md, docs/HARDWARE_OPTIMIZATION.md

param(
    [switch]$RequireCoreServices = $false
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) {
    $repoRoot = (Get-Location).Path
}

Write-Host "Station Calyx - System-wide health check" -ForegroundColor Cyan
Write-Host ""

# --- Top CPU processes (identify high-load station processes) ---
Write-Host "Top CPU consumers:" -ForegroundColor DarkGray
try {
    $top = Get-Process | Where-Object { $_.CPU -ge 0 } | Sort-Object CPU -Descending | Select-Object -First 5
    foreach ($p in $top) {
        $cpuSec = [math]::Round($p.CPU, 1)
        $memMB = [math]::Round($p.WorkingSet64 / 1MB, 1)
        Write-Host "  $($p.ProcessName) (PID $($p.Id)) : CPU ${cpuSec}s cumul, ${memMB} MB"
    }
    if ($top.Count -eq 0) { Write-Host "  (no processes with CPU time)" }
} catch {
    Write-Host "  (unable to read processes)"
}
Write-Host ""

# --- Run build safety check ---
$buildCheck = Join-Path $repoRoot "Scripts\build_safety_check.ps1"
if (-not (Test-Path $buildCheck)) {
    Write-Host "Build safety check not found: $buildCheck" -ForegroundColor Yellow
    exit 1
}

$buildArgs = @()
if ($RequireCoreServices) { $buildArgs += '-RequireCoreServices' }
& $buildCheck @buildArgs
exit $LASTEXITCODE
