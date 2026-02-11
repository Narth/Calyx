<#
Implementation sketch (design-only): Local Owner Confirmation CLI flow

Purpose:
- Verify eligibility for local_owner_confirmation.
- Display action list and safety notes.
- Require exact confirmation string: CONFIRM <proposal_id> <fingerprint>
- Record confirmation artifact at approvals/<proposal_id>.local_owner.json

Hard requirements satisfied:
- No JSON editing required by human.
- Shows action list (enable profile + create rule) and safety notes.
- Computes proposal fingerprint (SHA256) and uses first 8 chars.
- Records local_user and seat deterministically.

Seat derivation (deterministic, Windows):
- Username: $env:USERNAME
- Session ID: (Get-Process -Id $PID).SessionId
- Seat = "<USERNAME>-session-<SessionId>"

Elevation proof source (deterministic):
- logs/calyx_guardian/elevation_status.json (field: is_admin, user)

Usage:
pwsh -File tools\calyx_guardian\local_owner_confirm.ps1 -ProposalPath proposals\fw_context_preserving_enable_real.json

Note: Design-only. This script does NOT apply changes.
#>
param(
    [Parameter(Mandatory=$true)][string]$ProposalPath,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Fail([string]$msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $ProposalPath)) {
    Fail "Proposal path not found: $ProposalPath"
}

# Print exact proposal file path used for hashing (design-only)
Write-Host "Using proposal file for fingerprint: $ProposalPath" -ForegroundColor Cyan

# Compute SHA256 fingerprint (first 8 hex chars)
$hashObj = Get-FileHash -Algorithm SHA256 -Path $ProposalPath
$fingerprint = $hashObj.Hash.Substring(0,8).ToUpper()

# Load proposal
$proposalJson = Get-Content -Path $ProposalPath -Raw -Encoding UTF8 | ConvertFrom-Json
$proposalId = $proposalJson.proposal_id
if (-not $proposalId) { Fail "proposal_id missing in proposal" }

# Eligibility checks (preliminary)
#  - No Public profile changes
$enableProfiles = $proposalJson.proposed_firewall_state.enable_profiles.profiles
if ($enableProfiles -contains 'Public') {
    Fail "Proposal attempts to enable Public profile; local_owner_confirmation not allowed."
}

# Check proposed allow rules do not target Public
$rules = $proposalJson.proposed_firewall_state.proposed_allow_rules
foreach ($r in $rules) {
    if ($r.profiles -contains 'Public') { Fail "Proposed allow rule targets Public profile; local_owner_confirmation not allowed." }
}

# Validate elevation status
$elevPath = Join-Path "logs\calyx_guardian" "elevation_status.json"
if (-not (Test-Path $elevPath)) { Fail "Elevation status not found: $elevPath (elevation_achieved must be true)" }
$elev = $null
try { $elev = Get-Content -Path $elevPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { Fail "Failed to parse elevation_status.json" }
if (-not $elev.is_admin) { Fail "Elevation not achieved on this host (is_admin != true)" }

# Determine local user and seat
$localUserEnv = $env:USERNAME
$proc = Get-Process -Id $PID
$sessionId = $proc.SessionId
$seat = "${localUserEnv}-session-${sessionId}"

# Verify initiator matches elevation user (best-effort)
# elevation user may be DOMAIN\user; compare username portion
$elevUser = $elev.user -as [string]
$elevUserShort = $elevUser.Split('\')[-1]
if ($elevUserShort -ne $localUserEnv) {
    Write-Host "Warning: Current interactive user ($localUserEnv) does not match elevation user ($elevUser)." -ForegroundColor Yellow
    Write-Host "Local owner confirmation requires the operator to be the elevated local user." -ForegroundColor Yellow
}

# Display action list and safety notes
Write-Host "Proposal: $proposalId" -ForegroundColor Cyan
Write-Host "Proposal fingerprint (first 8 hex): $fingerprint" -ForegroundColor Cyan
Write-Host ""
Write-Host "Actions to be performed on THIS HOST:" -ForegroundColor Green
Write-Host "- Enable firewall profile(s): $($enableProfiles -join ', ')"
if ($rules) {
    foreach ($r in $rules) {
        Write-Host "- Create allow rule: $($r.id)  ($($r.protocol)/$($r.local_port)) program=$($r.program) profiles=$($r.profiles -join ', ') scope=$($r.scope)"
    }
} else {
    Write-Host "- No allow rules defined in proposal." }

Write-Host ""
Write-Host "Safety notes:" -ForegroundColor Green
Write-Host "- No Public profile changes are allowed in this approval path."
Write-Host "- Rollback requires a separate approved proposal. No automatic rollback will be performed."
Write-Host "- Apply will target only this host."
Write-Host ""

# Prepare confirmation string (proposal-specific)
$expectedString = "CONFIRM $proposalId $fingerprint"
Write-Host "To confirm, type EXACTLY the following confirmation string:" -ForegroundColor Yellow
Write-Host "$expectedString" -ForegroundColor Yellow

if ($DryRun) {
    Write-Host ""; Write-Host "DryRun mode: not prompting for confirmation. When ready, run this command and type the exact string shown above to record confirmation:" -ForegroundColor Yellow
    Write-Host "pwsh -File tools\calyx_guardian\local_owner_confirm.ps1 -ProposalPath $ProposalPath" -ForegroundColor Yellow
    exit 0
}

$userInput = Read-Host "Confirmation string"
if ($userInput -ne $expectedString) { Fail "Confirmation string did not match. Aborting." }

# Re-check eligibility immediately before recording (no apply in this script)
# Re-validate elevation and no Public targets
if (-not ((Get-Content -Path $elevPath -Raw | ConvertFrom-Json).is_admin)) { Fail "Elevation was lost during confirmation. Aborting." }
foreach ($r in $rules) { if ($r.profiles -contains 'Public') { Fail "Post-check: rule targets Public profile; aborting." } }

# Build approval artifact
$approval = [ordered]@{
    proposal_id = $proposalId
    policy_id = $proposalJson.policy_id
    correlation_id = $proposalJson.correlation_id
    approval_type = 'local_owner_confirmation'
    target_scope = 'single_host'
    elevation_achieved = $true
    action_category = 'network_control'
    initiated_by = 'local_user'
    local_user = [ordered]@{ name = $localUserEnv; seat = $seat }
    actions = $rules
    confirmed_utc = (Get-Date).ToUniversalTime().ToString('o')
    confirmation_string = $userInput
    evidence_refs = @($elevPath, $ProposalPath)
    notes = 'Local owner confirmation recorded by local_owner_confirm.ps1'
}

# Ensure approvals directory exists
$approvalDir = 'approvals'
New-Item -ItemType Directory -Force -Path $approvalDir | Out-Null

$outPath = Join-Path $approvalDir ("$proposalId.local_owner.json")
$approval | ConvertTo-Json -Depth 6 | Set-Content -Path $outPath -Encoding UTF8

Write-Host "Confirmation recorded to: $outPath" -ForegroundColor Green
Write-Host "Please provide an explicit approval message to the orchestrator to proceed with apply (out-of-band)."

# End (design-only)
