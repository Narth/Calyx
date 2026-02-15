# telemetry_export.ps1
# Package only outbox chunks not yet exported for transfer to another node.
# Output: exports/telemetry_exports/<node_id>/<YYYYMMDD_HHMMSS>/
# Manifest: manifest.json with chunk filenames + sha256
# Marker: telemetry/outbox/<node_id>/.exported_index.json

param(
    [string]$RepoRoot = (Split-Path -Parent (Split-Path -Parent $PSCommandPath)),
    [string]$RuntimeDir = "runtime"
)

$ErrorActionPreference = "Stop"
$nodePath = Join-Path -Path $RepoRoot -ChildPath "$RuntimeDir\node_id.txt"
if (-not (Test-Path $nodePath)) {
    Write-Error "Node ID file not found: $nodePath"
}
$nodeId = (Get-Content $nodePath -Raw).Trim()
if (-not $nodeId) {
    Write-Error "Empty node_id in $nodePath"
}

$outboxDir = Join-Path -Path $RepoRoot -ChildPath "telemetry\outbox\$nodeId"
if (-not (Test-Path $outboxDir)) {
    Write-Host "Outbox empty or missing: $outboxDir"
    exit 0
}

$indexPath = Join-Path -Path $outboxDir -ChildPath ".exported_index.json"
$exported = @{}
if (Test-Path $indexPath) {
    $index = Get-Content $indexPath -Raw | ConvertFrom-Json
    foreach ($e in $index.exported) { $exported[$e] = $true }
}

$chunks = Get-ChildItem -Path $outboxDir -Filter "*.jsonl" -File | Where-Object { $_.Name -notlike ".*" }
$toExport = @()
foreach ($c in $chunks) {
    if (-not $exported.ContainsKey($c.Name)) {
        $toExport += $c
    }
}

if ($toExport.Count -eq 0) {
    Write-Host "No new chunks to export."
    exit 0
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$exportDir = Join-Path -Path $RepoRoot -ChildPath "exports\telemetry_exports\$nodeId\$timestamp"
New-Item -ItemType Directory -Force -Path $exportDir | Out-Null

$manifestChunks = @()
$newExported = @()

foreach ($chunk in $toExport) {
    $destPath = Join-Path -Path $exportDir -ChildPath $chunk.Name
    Copy-Item $chunk.FullName -Destination $destPath -Force
    $hash = (Get-FileHash -Path $destPath -Algorithm SHA256).Hash
    $manifestChunks += @{ filename = $chunk.Name; sha256 = $hash }
    $newExported += $chunk.Name
}

$manifest = @{
    node_id = $nodeId
    exported_at = (Get-Date -Format "o")
    timestamp = $timestamp
    chunks = $manifestChunks
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content (Join-Path -Path $exportDir -ChildPath "manifest.json") -Encoding UTF8

$allExported = @($exported.Keys) + $newExported
$indexContent = @{ exported = @($allExported | Sort-Object -Unique) }
$indexContent | ConvertTo-Json | Set-Content $indexPath -Encoding UTF8

Write-Host "Exported $($toExport.Count) chunk(s) to $exportDir"
Write-Host "Manifest: $exportDir\manifest.json"
