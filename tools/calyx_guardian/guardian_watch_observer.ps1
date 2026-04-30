# Guardian watch observer (stub) — governance/plans/guardian_night_watch.json

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path } else { (Get-Location).Path }
$logDir = Join-Path $repoRoot "logs\calyx_guardian"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
Write-Host "Guardian watch observer (stub) — logs: $logDir"
