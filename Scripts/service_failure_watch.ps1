param(
    [int]$IntervalSec = 15,
    [string]$StopFile = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) { $repoRoot = (Get-Location).Path }
Set-Location $repoRoot

if (-not $StopFile) { $StopFile = Join-Path $repoRoot "runtime\service_failure_watch.stop" }
$contractPath = Join-Path $repoRoot "Scripts\service_failure_contract.ps1"
. $contractPath

$updateScript = Join-Path $repoRoot "Scripts\update_state_checks.ps1"

while ($true) {
    if (Test-Path -LiteralPath $StopFile -PathType Leaf) {
        Remove-Item -LiteralPath $StopFile -Force -ErrorAction SilentlyContinue
        break
    }
    $result = Invoke-ServiceFailureScan -RepoRoot $repoRoot
    if ($result.state_changed -and (Test-Path $updateScript)) {
        try { & $updateScript | Out-Null } catch { }
    }
    Start-Sleep -Seconds $IntervalSec
}
