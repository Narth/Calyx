# prompt_calyx_sign.ps1 — Display a Calyx Sign prompt in the terminal (e.g. Cursor PowerShell).
# Run this to get a clear reminder and the exact command(s) to run in this window.
# Usage: .\Scripts\prompt_calyx_sign.ps1 [ -Receipt path\to\receipt.approval.json ]

param(
    [string] $Receipt = ".\governance\approvals\cbo_sponsorship_research_test_improve.approval.json"
)

$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
$receiptRaw = $Receipt -replace '^\.\\', ''
if ([System.IO.Path]::IsPathRooted($receiptRaw)) {
    $receiptPath = $receiptRaw
} else {
    $receiptPath = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $receiptRaw))
}
$receiptExists = Test-Path -LiteralPath $receiptPath -PathType Leaf

$sep = '========================================'
Write-Host ""
Write-Host $sep -ForegroundColor Cyan
Write-Host '  Calyx Sign - Submit in this window' -ForegroundColor Cyan
Write-Host $sep -ForegroundColor Cyan
Write-Host ""

if (-not $receiptExists) {
    Write-Host "Receipt not found: $receiptPath" -ForegroundColor Yellow
    Write-Host "Pass -Receipt with a path to prompt for a different receipt." -ForegroundColor Gray
    Write-Host ""
    return
}

Write-Host "Receipt: $receiptPath" -ForegroundColor Gray
Write-Host ""

Write-Host "1. Have USB key with Architect VHD ready (mount in Explorer if you use -FromKeyDir)." -ForegroundColor White
Write-Host "2. Run ONE of the following in this Cursor PowerShell window:" -ForegroundColor White
Write-Host ""

# From repo root (default path)
$scriptPath = Join-Path $repoRoot "tools\calyx_sign.ps1"
Write-Host '   Default (script attaches or uses existing mount):' -ForegroundColor DarkGray
Write-Host '   ' -NoNewline
$cmdDefault = 'powershell -NoProfile -ExecutionPolicy Bypass -File "' + $scriptPath + '" -Receipt "' + $receiptPath + '"'
Write-Host $cmdDefault -ForegroundColor Green
Write-Host ""

# FromKeyDir (when child cannot see V:)
Write-Host '   If ssh-keygen cannot see the key (use after mounting VHD in Explorer):' -ForegroundColor DarkGray
Write-Host '   ' -NoNewline
$cmdFromKeyDir = 'cd V:\calyx_identity; powershell -NoProfile -ExecutionPolicy Bypass -File "' + $scriptPath + '" -Receipt "' + $receiptPath + '" -FromKeyDir'
Write-Host $cmdFromKeyDir -ForegroundColor Green
Write-Host ""

$step3 = '3. Type the SIGN line when prompted; enter passphrase at ssh-keygen. .sig will be written next to the receipt.'
Write-Host $step3 -ForegroundColor White
Write-Host ""
Write-Host $sep -ForegroundColor Cyan
Write-Host ""
