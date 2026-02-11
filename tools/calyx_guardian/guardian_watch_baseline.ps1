param(
    [string]$OutDir = "logs\calyx_guardian",
    [string]$CorrelationId
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($CorrelationId)) {
    throw "CorrelationId is required"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runner = Join-Path $scriptDir "run_phase0_windows.ps1"
$manifest = Join-Path $scriptDir "render\guardian_manifest.py"
$libPath = Join-Path $scriptDir "lib\run_with_timeout.ps1"
$runLogPath = Join-Path $OutDir "run_log.jsonl"

. $libPath

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$runnerOut = Join-Path $OutDir "watch_baseline.stdout.log"
$runnerErr = Join-Path $OutDir "watch_baseline.stderr.log"
$manifestOut = Join-Path $OutDir "watch_manifest.stdout.log"
$manifestErr = Join-Path $OutDir "watch_manifest.stderr.log"

$runnerResult = Invoke-GuardianProcess -FilePath "powershell" -Arguments @(
    "-NoLogo",
    "-NoProfile",
    "-NonInteractive",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $runner,
    "-OutDir",
    $OutDir,
    "-Verify"
) -TimeoutSeconds 600 -NoProgressSeconds 0 -StdoutPath $runnerOut -StderrPath $runnerErr -RunLogPath $runLogPath

if ($runnerResult.Outcome -ne "success") {
    throw "watch_baseline failed: $($runnerResult.Outcome)"
}

$manifestResult = Invoke-GuardianProcess -FilePath "py" -Arguments @(
    "-3.11",
    $manifest,
    "--outdir",
    $OutDir,
    "--correlation-id",
    $CorrelationId
) -TimeoutSeconds 60 -NoProgressSeconds 30 -StdoutPath $manifestOut -StderrPath $manifestErr -RunLogPath $runLogPath

if ($manifestResult.Outcome -ne "success") {
    throw "watch_manifest failed: $($manifestResult.Outcome)"
}

Write-Host "Night watch baseline complete."
Write-Host "Artifacts:"
Write-Host "- $OutDir\evidence.jsonl"
Write-Host "- $OutDir\findings.json"
Write-Host "- $OutDir\report.md"
Write-Host "- $OutDir\manifest.json"
