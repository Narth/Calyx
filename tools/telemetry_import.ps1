# telemetry_import.ps1
# Import a telemetry export bundle produced by telemetry_export.ps1 into the federated store.
# Output: telemetry/federated/<source_node_id>/<export_folder_name>/
# Index: telemetry/federated/.import_index.json (idempotent, blocks double-import)
#
# Usage: .\tools\telemetry_import.ps1 -ExportPath "E:\telemetry_exports\calyx_laptop_01\20260214_200252"
#
# Contract: Export folder contains manifest.json + *.jsonl chunks.
# Manifest: node_id, exported_at, timestamp, chunks [{ filename, sha256 }]

param(
    [Parameter(Mandatory = $true)]
    [string]$ExportPath,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$FederatedBase = Join-Path -Path $RepoRoot -ChildPath "telemetry\federated"
$IndexPath = Join-Path -Path $FederatedBase -ChildPath ".import_index.json"

# Ensure federated base exists
if (-not (Test-Path -LiteralPath $FederatedBase)) {
    New-Item -ItemType Directory -Path $FederatedBase -Force | Out-Null
}

# 1) Validate ExportPath is a directory
if (-not (Test-Path -LiteralPath $ExportPath)) {
    Write-Error "ExportPath not found: $ExportPath"
}
if (Test-Path -LiteralPath $ExportPath -PathType Leaf) {
    Write-Error "ExportPath must be a directory, not a file: $ExportPath"
}
$ExportPath = (Resolve-Path -LiteralPath $ExportPath).Path

# 2) Load manifest.json
$ManifestPath = Join-Path -Path $ExportPath -ChildPath "manifest.json"
if (-not (Test-Path -LiteralPath $ManifestPath)) {
    Write-Error "manifest.json not found. Expected: $ManifestPath"
}
if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    Write-Error "manifest.json must be a file, not a directory: $ManifestPath"
}
$Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

# Derive source_node_id: manifest.node_id or parent folder name (e.g. calyx_laptop_01)
$ExportPathTrimmed = $ExportPath.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
$ExportFolderName = Split-Path -Leaf -Path $ExportPathTrimmed
$SourceNodeId = $Manifest.node_id
if ([string]::IsNullOrWhiteSpace($SourceNodeId)) {
    $SourceNodeId = Split-Path -Leaf -Path (Split-Path -Parent -Path $ExportPathTrimmed)
    if ([string]::IsNullOrWhiteSpace($SourceNodeId)) { $SourceNodeId = "unknown" }
}

# Load import index
$ImportIndex = @{ imports = @() }
if (Test-Path -LiteralPath $IndexPath) {
    try {
        $ImportIndex = Get-Content -LiteralPath $IndexPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch { }
}

# Idempotency: block double-import
$Existing = $ImportIndex.imports | Where-Object {
    $_.source_node_id -eq $SourceNodeId -and $_.export_folder -eq $ExportFolderName
}
if ($Existing -and -not $Force) {
    Write-Host "[IMPORT] Already imported: $SourceNodeId / $ExportFolderName. Use -Force to re-import."
    exit 0
}

# 3) Verify sha256 for each chunk; fail fast if missing
if (-not $Manifest.chunks) {
    Write-Error "Manifest has no 'chunks' array or it is empty."
}
foreach ($c in $Manifest.chunks) {
    $FileName = if ($c.filename) { $c.filename } elseif ($c.file) { $c.file } else { $null }
    if ([string]::IsNullOrWhiteSpace($FileName)) {
        Write-Error "Manifest chunk has empty or missing 'filename'/'file' property."
    }
    $ChunkPath = Join-Path -Path $ExportPath -ChildPath $FileName
    if (-not (Test-Path -LiteralPath $ChunkPath)) {
        Write-Error "Chunk file not found: $FileName (resolved: $ChunkPath)"
    }
    if (Test-Path -LiteralPath $ChunkPath -PathType Container) {
        Write-Error "Chunk path must be a file, not a directory: $ChunkPath"
    }
    $ActualHash = (Get-FileHash -Path $ChunkPath -Algorithm SHA256).Hash
    $ExpectedHash = $c.sha256
    if ($ActualHash -ne $ExpectedHash) {
        Write-Error "SHA256 mismatch for $FileName`: expected $ExpectedHash, got $ActualHash"
    }
}
Write-Host "[IMPORT] Manifest verified for $SourceNodeId"

# 4) Copy chunks into telemetry/federated/<source_node_id>/<export_folder_name>/
$DestDir = Join-Path -Path (Join-Path -Path $FederatedBase -ChildPath $SourceNodeId) -ChildPath $ExportFolderName
New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
foreach ($c in $Manifest.chunks) {
    $FileName = if ($c.filename) { $c.filename } elseif ($c.file) { $c.file } else { $null }
    if ([string]::IsNullOrWhiteSpace($FileName)) { continue }
    $Src = Join-Path -Path $ExportPath -ChildPath $FileName
    $Dst = Join-Path -Path $DestDir -ChildPath $FileName
    if (Test-Path -LiteralPath $Src -PathType Leaf) {
        Copy-Item -LiteralPath $Src -Destination $Dst -Force
    }
}

# 5) Update import index
$ImportIndex.imports += @{
    source_node_id = $SourceNodeId
    export_folder  = $ExportFolderName
    path           = $DestDir
    imported_at    = (Get-Date -Format "o")
}
$ImportIndex | ConvertTo-Json -Depth 5 | Set-Content -Path $IndexPath -Encoding UTF8

Write-Host "[IMPORT] Imported $SourceNodeId -> $DestDir"
$DestDir
