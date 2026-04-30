# Local Owner Confirmation — record Architect confirmation for a proposal.
# Usage: pwsh -File tools\calyx_guardian\local_owner_confirm.ps1 -ProposalPath proposals\<proposal>.json
# Then type: CONFIRM <proposal_id> <fingerprint>
# Writes: governance/approvals/<proposal_id>.local_owner.json

param(
    [Parameter(Mandatory=$true)]
    [string]$ProposalPath
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path } else { (Get-Location).Path }
$proposalFull = if ([System.IO.Path]::IsPathRooted($ProposalPath)) { $ProposalPath } else { Join-Path $repoRoot $ProposalPath }

if (-not (Test-Path $proposalFull)) {
    Write-Error "Proposal not found: $proposalFull"
}

$proposal = Get-Content $proposalFull -Raw | ConvertFrom-Json
$proposalId = $proposal.proposal_id
$contentHash = (Get-FileHash -Path $proposalFull -Algorithm SHA256).Hash
$fingerprint = $contentHash.Substring(0, [Math]::Min(8, $contentHash.Length))

Write-Host "Proposal: $proposalId"
Write-Host "Fingerprint (first 8): $fingerprint"
Write-Host "Type the following line exactly to confirm (include the word CONFIRM): CONFIRM $proposalId $fingerprint"
$input = Read-Host "Your input"
if ($input -match "CONFIRM\s+$proposalId\s+$fingerprint") {
    $approvalsDir = Join-Path $repoRoot "governance\approvals"
    if (-not (Test-Path $approvalsDir)) { New-Item -ItemType Directory -Path $approvalsDir -Force | Out-Null }
    $outPath = Join-Path $approvalsDir "$proposalId.local_owner.json"
    $artifact = @{
        proposal_id = $proposalId
        confirmation_type = "local_owner_confirmation"
        fingerprint = $fingerprint
        confirmed_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    } | ConvertTo-Json
    Set-Content -Path $outPath -Value $artifact -Encoding UTF8
    Write-Host "Confirmation recorded: $outPath"
} else {
    Write-Error "Confirmation string did not match. No artifact written."
}
