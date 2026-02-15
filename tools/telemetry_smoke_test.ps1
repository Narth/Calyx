# telemetry_smoke_test.ps1
# Emit one test telemetry event, verify it lands in outbox, run export.

param(
    [string]$RepoRoot = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

Write-Host "=== Telemetry Smoke Test ===" -ForegroundColor Cyan

# 1) Emit test event via Python
Write-Host "`n1. Emitting test telemetry event..."
$emitScript = @"
import sys
from pathlib import Path
repo = Path(r'$RepoRoot').resolve()
sys.path.insert(0, str(repo))
from telemetry.outbox_mirror import mirror_event
event = {'_smoke_test': True, 'message': 'telemetry_smoke_test', 'label': 'TEST'}
ok = mirror_event(event, 'bench_harness', runtime_root=repo / 'runtime', repo_root=repo)
sys.exit(0 if ok else 1)
"@
$emitScript | py - 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to emit test event"
}

# 2) Verify outbox
$nodeId = (Get-Content (Join-Path -Path $RepoRoot -ChildPath "runtime\node_id.txt") -Raw).Trim()
$outboxDir = Join-Path -Path $RepoRoot -ChildPath "telemetry\outbox\$nodeId"
$chunks = Get-ChildItem -Path $outboxDir -Filter "*.jsonl" -File -ErrorAction SilentlyContinue
if (-not $chunks) {
    Write-Error "No chunks in outbox: $outboxDir"
}
$found = $false
foreach ($c in $chunks) {
    $lines = Get-Content $c.FullName -Tail 5
    foreach ($line in $lines) {
        if ($line -match "node_id" -and $line -match "ts_utc" -and $line -match "event_id" -and $line -match "source" -and $line -match "_smoke_test") {
            Write-Host "2. Verified: event in $($c.Name) with node_id, ts_utc, event_id, source" -ForegroundColor Green
            $found = $true
            break
        }
    }
    if ($found) { break }
}
if (-not $found) {
    Write-Error "Test event not found with required fields (node_id, ts_utc, event_id, source)"
}

# 3) Run export
Write-Host "`n3. Running telemetry_export.ps1..."
& (Join-Path -Path $RepoRoot -ChildPath "tools\telemetry_export.ps1") -RepoRoot $RepoRoot
if ($LASTEXITCODE -ne 0) {
    Write-Error "Export failed"
}

# 4) Show export folder + manifest + sha256
$exportsBase = Join-Path -Path $RepoRoot -ChildPath "exports\telemetry_exports\$nodeId"
$latestExport = Get-ChildItem -Path $exportsBase -Directory | Sort-Object Name -Descending | Select-Object -First 1
if ($latestExport) {
    Write-Host "`n4. Export folder: $($latestExport.FullName)" -ForegroundColor Cyan
    $manifestPath = Join-Path -Path $latestExport.FullName -ChildPath "manifest.json"
    if (Test-Path $manifestPath) {
        Write-Host "Manifest:"
        Get-Content $manifestPath
        $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
        Write-Host "`nSHA256 list:"
        foreach ($chunk in $manifest.chunks) {
            Write-Host "  $($chunk.filename): $($chunk.sha256)"
        }
    }
}

Write-Host "`n=== Smoke test PASSED ===" -ForegroundColor Green
