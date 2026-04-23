# Station Patch + Sunrise — automate sunset and sunrise after system-level changes.
# Run after applying patches to cbo_hub/, calyx/, Scripts/, or config.
# Delegates to calyx_sunset_sunrise.ps1 for explicit sunset → sunrise procedure.
#
# Usage: .\Scripts\station_patch_sunrise.ps1 [-SkipReadiness] [-CoreOnly]
# -SkipReadiness: Skip patch_readiness gate (use when entropy check not needed)
# -CoreOnly: Start only CBO Core services; do not start Discord Gateway

param(
    [switch]$SkipReadiness = $false,
    [switch]$CoreOnly = $false
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) { $repoRoot = (Get-Location).Path }
Set-Location $repoRoot

$orchestrator = Join-Path $repoRoot "Scripts\calyx_sunset_sunrise.ps1"
if (-not (Test-Path $orchestrator)) {
    Write-Error "calyx_sunset_sunrise.ps1 not found."
}

$args = @()
if ($SkipReadiness) { $args += "-SkipReadiness" }
if ($CoreOnly) { $args += "-CoreOnly" }
& $orchestrator @args
