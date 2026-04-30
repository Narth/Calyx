# Phase 0 assessment (stub) — creates logs/calyx_guardian/ structure.
# Full implementation: governance/plans/guardian_assessment_bundle.json

param(
    [string]$OutDir = "logs/calyx_guardian",
    [switch]$Verify
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path } else { (Get-Location).Path }
$outFull = Join-Path $repoRoot $OutDir
New-Item -ItemType Directory -Path $outFull -Force | Out-Null

$ts = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
@{ timestamp = $ts; phase = "phase0"; status = "stub" } | ConvertTo-Json | Add-Content (Join-Path $outFull "evidence.jsonl")
@{} | ConvertTo-Json | Set-Content (Join-Path $outFull "findings.json") -Encoding UTF8
"# Phase 0 Assessment (stub)`n`nStatus: stub. Full implementation pending." | Set-Content (Join-Path $outFull "report.md") -Encoding UTF8
@{} | ConvertTo-Json | Add-Content (Join-Path $outFull "run_log.jsonl")

Write-Host "Phase 0 stub complete. Output: $outFull"
