param(
    [switch]$SkipSunrise = $false
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
Set-Location $repoRoot

$sunriseScript = Join-Path $repoRoot "Scripts\sunrise_calyx.ps1"
$generatorScript = Join-Path $repoRoot "Scripts\generate_daily_24h_review.py"
$venvPython = Join-Path $repoRoot ".venv_cbohub311\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    $venvPython = "python"
}

if (-not $SkipSunrise) {
    Write-Host "Daily 24h review cycle: governed sunrise..."
    & powershell -NoProfile -ExecutionPolicy Bypass -File $sunriseScript
    if ($LASTEXITCODE -ne 0) {
        throw "Governed sunrise failed during daily 24h review cycle."
    }
}

Write-Host "Daily 24h review cycle: generating post-sunrise daily review..."
& $venvPython $generatorScript --automatic
if ($LASTEXITCODE -ne 0) {
    throw "Daily 24h review generation failed."
}
