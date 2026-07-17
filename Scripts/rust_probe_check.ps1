# Build and run the local-only Rust station probe when Cargo is available.
#
# This script is advisory. Missing Rust tooling is a skip, not a Station failure.

param(
    [switch]$Json = $false
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
Set-Location $repoRoot

function New-Result {
    param(
        [string]$Status,
        [string]$Reason,
        [string]$ProbePath = "",
        [int]$ExitCode = 0
    )
    return [ordered]@{
        schema = "station.rust_probe_check.v1"
        emitted_ts_utc = [datetime]::UtcNow.ToString("o")
        status = $Status
        reason = $Reason
        probe = "rust/station_probe"
        probe_output = $ProbePath
        exit_code = $ExitCode
    }
}

function Write-Result {
    param([Parameter(Mandatory = $true)][object]$Result)
    $runtimeDir = Join-Path $repoRoot "runtime\rust"
    if (-not (Test-Path -LiteralPath $runtimeDir)) {
        New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
    }
    $resultPath = Join-Path $runtimeDir "station_probe_check.json"
    $Result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultPath -Encoding UTF8
    if ($Json) {
        $Result | ConvertTo-Json -Depth 8
    } else {
        Write-Host ("RUST_PROBE_CHECK status={0} reason={1}" -f $Result.status, $Result.reason)
        Write-Host "Receipt: runtime\rust\station_probe_check.json"
        if ($Result.probe_output) {
            Write-Host ("Probe output: {0}" -f $Result.probe_output)
        }
    }
}

$cargo = Get-Command cargo -ErrorAction SilentlyContinue
if (-not $cargo) {
    Write-Result -Result (New-Result -Status "skipped" -Reason "cargo_not_found")
    exit 0
}

$probeDir = Join-Path $repoRoot "rust\station_probe"
if (-not (Test-Path -LiteralPath (Join-Path $probeDir "Cargo.toml") -PathType Leaf)) {
    Write-Result -Result (New-Result -Status "failed" -Reason "probe_manifest_missing" -ExitCode 1)
    exit 1
}

& cargo build --manifest-path (Join-Path $probeDir "Cargo.toml")
if ($LASTEXITCODE -ne 0) {
    Write-Result -Result (New-Result -Status "failed" -Reason "cargo_build_failed" -ExitCode $LASTEXITCODE)
    exit $LASTEXITCODE
}

$runtimeDir = Join-Path $repoRoot "runtime\rust"
if (-not (Test-Path -LiteralPath $runtimeDir)) {
    New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
}
$probeOutputPath = Join-Path $runtimeDir "station_probe.json"
& cargo run --quiet --manifest-path (Join-Path $probeDir "Cargo.toml") -- --repo-root $repoRoot | Set-Content -LiteralPath $probeOutputPath -Encoding UTF8
if ($LASTEXITCODE -ne 0) {
    Write-Result -Result (New-Result -Status "failed" -Reason "probe_run_failed" -ProbePath "runtime\rust\station_probe.json" -ExitCode $LASTEXITCODE)
    exit $LASTEXITCODE
}

try {
    Get-Content -LiteralPath $probeOutputPath -Raw -Encoding UTF8 | ConvertFrom-Json | Out-Null
} catch {
    Write-Result -Result (New-Result -Status "failed" -Reason "probe_json_invalid" -ProbePath "runtime\rust\station_probe.json" -ExitCode 1)
    exit 1
}

Write-Result -Result (New-Result -Status "ok" -Reason "probe_built_and_ran" -ProbePath "runtime\rust\station_probe.json")
exit 0
