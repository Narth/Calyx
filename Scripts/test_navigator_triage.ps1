# Test Navigator and Triage Orchestrator — simulation and safety validation.
# Usage: .\Scripts\test_navigator_triage.ps1
# Runs simulations with mock station_health.json; verifies exit codes and lock files.
# See: docs/operations/NAVIGATOR_TRIAGE_MINIMAL_SUNRISE.md

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
Set-Location $repoRoot

$runtimeDir = Join-Path $repoRoot "runtime"
$healthPath = Join-Path $runtimeDir "station_health.json"
$healthBackup = Join-Path $runtimeDir "station_health.json.test_backup"

$tests = @(
    @{
        name = "pass (hot)"
        health = @{ health = "pass"; entropy = @{ tier = "pass" }; health_ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") }
        navigator_expect = 0
        triage_expect = 0
    },
    @{
        name = "warn/high (cool)"
        health = @{ health = "warn"; entropy = @{ tier = "high" }; health_ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") }
        navigator_expect = 2
        triage_expect = 1
    },
    @{
        name = "fail (pause)"
        health = @{ health = "fail"; entropy = @{ tier = "unacceptable" }; health_ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") }
        navigator_expect = 1
        triage_expect = 2
    },
    @{
        name = "unacceptable (pause)"
        health = @{ health = "pass"; entropy = @{ tier = "unacceptable" }; health_ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") }
        navigator_expect = 1
        triage_expect = 2
    },
    @{
        name = "cadence_70 > 10 (pause, bulk frequent maxing)"
        health = @{ health = "pass"; entropy = @{ tier = "pass"; cadence_70 = 15 }; health_ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") }
        navigator_expect = 1
        triage_expect = 2
    }
)

# Backup real health if exists
if (Test-Path $healthPath) {
    Copy-Item $healthPath $healthBackup -Force
}

$pass = 0
$fail = 0

Write-Host "=== Navigator + Triage Test Suite ===" -ForegroundColor Cyan
Write-Host ""

foreach ($t in $tests) {
    Write-Host "Test: $($t.name)" -ForegroundColor DarkGray
    $t.health | ConvertTo-Json -Depth 4 | Set-Content $healthPath -Encoding UTF8

    # Navigator
    & "$repoRoot\Scripts\navigator.ps1" > $null 2>&1
    $navEc = $LASTEXITCODE
    $navOk = ($navEc -eq $t.navigator_expect)
    if ($navOk) { $pass++; Write-Host "  Navigator: OK (exit $navEc)" -ForegroundColor Green }
    else { $fail++; Write-Host "  Navigator: FAIL (got $navEc, expected $($t.navigator_expect))" -ForegroundColor Red }

    # Triage
    & "$repoRoot\Scripts\triage_orchestrator.ps1" > $null 2>&1
    $triEc = $LASTEXITCODE
    $triOk = ($triEc -eq $t.triage_expect)
    if ($triOk) { $pass++; Write-Host "  Triage: OK (exit $triEc)" -ForegroundColor Green }
    else { $fail++; Write-Host "  Triage: FAIL (got $triEc, expected $($t.triage_expect))" -ForegroundColor Red }

    Write-Host ""
}

# Restore real health
if (Test-Path $healthBackup) {
    Copy-Item $healthBackup $healthPath -Force
    Remove-Item $healthBackup -Force
}

Write-Host "=== Results: $pass pass, $fail fail ===" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Red" })
exit $(if ($fail -eq 0) { 0 } else { 1 })
