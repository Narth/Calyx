param(
    [Parameter(Position = 0)]
    [string]$Receipt,

    [string]$Namespace = "calyx",
    [string]$Identity = "architect",

    [string]$KeyPath = "V:\calyx_identity\architect_ed25519",
    [string]$VhdxName = "architect_identity.vhdx",

    [string[]]$SearchDrives = @("D","E","F","G","H","I","J"),

    [string]$ParentCorrelationId,

    [switch]$Force,
    [switch]$NoConfirm
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# This script is human-invoked by design. It MUST remain interactive.
# It must not cache, echo, or persist secrets. It only logs safe evidence.

function Fail([string]$Message, [int]$Code = 1) {
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit $Code
}

function WarnHigh([string]$Message) {
    Write-Host "WARNING: $Message" -ForegroundColor Yellow
}

function Sha256File([string]$Path) {
    (Get-FileHash -Algorithm SHA256 -Path $Path).Hash
}

function SafeJsonSummary([string]$ReceiptPath) {
    try {
        $text = Get-Content -Path $ReceiptPath -Raw -Encoding UTF8
        $obj = $text | ConvertFrom-Json -ErrorAction Stop

        $summary = [ordered]@{}
        foreach ($k in @("proposal_id","action","scope","repo_url","branch","commit_hash")) {
            if ($null -ne $obj.$k -and "$($obj.$k)".Length -gt 0) {
                $summary[$k] = $obj.$k
            }
        }
        return $summary
    } catch {
        return $null
    }
}

function FindVhdxPath([string[]]$Drives, [string]$Name) {
    foreach ($d in $Drives) {
        $candidate = "${d}:\calyx_identity\$Name"
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    return $null
}

function RunDiskpart([string[]]$Lines, [string]$Label) {
    $tmp = [System.IO.Path]::GetTempFileName()
    try {
        $Lines | Set-Content -Path $tmp -Encoding ASCII
        $p = Start-Process -FilePath "diskpart.exe" -ArgumentList @("/s", $tmp) -PassThru -Wait -NoNewWindow
        return [ordered]@{ label = $Label; exit_code = $p.ExitCode }
    } finally {
        Remove-Item -Force -ErrorAction SilentlyContinue $tmp | Out-Null
    }
}

if ([string]::IsNullOrWhiteSpace($Receipt)) {
    Fail "Receipt path is required. Usage: powershell -File tools\\calyx_sign.ps1 -Receipt <path>"
}

if (-not (Test-Path $Receipt)) {
    Fail "Receipt not found: $Receipt" 2
}

$receiptFull = (Resolve-Path $Receipt).Path
$receiptDir = Split-Path -Parent $receiptFull
$receiptName = Split-Path -Leaf $receiptFull

# Receipt path governance: default allow only under governance/approvals
$repoRoot = Split-Path -Parent $PSScriptRoot
$defaultAllowedDir = Join-Path $repoRoot "governance\approvals"
try {
    $allowedRoot = (Resolve-Path $defaultAllowedDir).Path
} catch {
    $allowedRoot = $defaultAllowedDir
}

if (-not ($receiptFull.ToLower().StartsWith(($allowedRoot.ToLower().TrimEnd('\')) + '\'))) {
    if (-not $Force) {
        Fail "Receipt is outside default allowed directory ($allowedRoot). Re-run with -Force to sign external paths." 9
    }
    WarnHigh "Receipt is outside default allowed directory ($allowedRoot). You are using -Force."
    Write-Host "External receipt path: $receiptFull" -ForegroundColor Yellow
    Write-Host "To continue signing an external receipt, type EXACTLY: SIGN-EXTERNAL $($receiptName)" -ForegroundColor Yellow
    $typedExternal = Read-Host "External receipt confirmation"
    if ($typedExternal -ne "SIGN-EXTERNAL $receiptName") {
        Fail "External confirmation mismatch. Aborting." 10
    }
}

$receiptHash = Sha256File $receiptFull
$fingerprint = $receiptHash.Substring(0, 8).ToUpper()

Write-Host "Receipt: $receiptName" -ForegroundColor Cyan
Write-Host "Directory: $receiptDir" -ForegroundColor Cyan
Write-Host "SHA256(receipt): $receiptHash" -ForegroundColor Cyan

$summary = SafeJsonSummary $receiptFull
if ($null -ne $summary) {
    Write-Host "Receipt summary (safe fields only):" -ForegroundColor Cyan
    $summary.GetEnumerator() | ForEach-Object { Write-Host "- $($_.Key): $($_.Value)" }
}

$commitHash = $null
if ($null -ne $summary -and $summary.Contains("commit_hash")) {
    $commitHash = "$($summary["commit_hash"])"
}

if (-not $NoConfirm) {
    $expected = if ($commitHash) { "SIGN $fingerprint COMMIT $commitHash" } else { "SIGN $fingerprint" }
    Write-Host "" 
    Write-Host "To proceed, type exactly: $expected" -ForegroundColor Yellow
    if ($commitHash) {
        Write-Host "Commit hash detected in receipt: $commitHash" -ForegroundColor Yellow
    }
    $typed = Read-Host "Signing confirmation"
    if ($typed -ne $expected) {
        Fail "Confirmation mismatch. Aborting." 3
    }
}

Write-Host "" 
Write-Host "Insert USB key and press Enter." -ForegroundColor Yellow
[void](Read-Host " ")

$vhdxPath = FindVhdxPath -Drives $SearchDrives -Name $VhdxName
if (-not $vhdxPath) {
    Write-Host "VHDX not found on default drives. Enter full VHDX path:" -ForegroundColor Yellow
    $vhdxPath = Read-Host "VHDX path"
}

if (-not (Test-Path $vhdxPath)) {
    Fail "VHDX path not found: $vhdxPath" 4
}

$attachResult = $null
$detachResult = $null
$sigPath = "$receiptFull.sig"

# Signing receipt output dir
$signingDir = Join-Path $repoRoot "governance\receipts\signing"
New-Item -ItemType Directory -Force -Path $signingDir | Out-Null
$correlationId = [Guid]::NewGuid().ToString("N").Substring(0, 12)
$signingReceiptPath = Join-Path $signingDir ("$receiptName.signing_receipt.json")

try {
    $attachResult = RunDiskpart -Label "attach" -Lines @(
        "select vdisk file=""$vhdxPath""",
        "attach vdisk"
    )

    if ($attachResult.exit_code -ne 0) {
        Fail "diskpart attach failed (exit_code=$($attachResult.exit_code))" 5
    }

    # Verify that key exists (either on V: or user-specified KeyPath)
    if (-not (Test-Path $KeyPath)) {
        Fail "KeyPath not found after attach: $KeyPath" 6
    }

    # Optional volume label check (best-effort): do not fail if unavailable
    try {
        $drive = Split-Path -Qualifier $KeyPath
        $vol = Get-Volume -DriveLetter $drive.TrimEnd(':') -ErrorAction Stop
        if ($vol.FileSystemLabel -ne "CalyxArchitect") {
            Write-Host "Warning: mounted volume label is '$($vol.FileSystemLabel)' (expected CalyxArchitect). Continuing because KeyPath exists." -ForegroundColor Yellow
        }
    } catch {
        # ignore
    }

    # If a signature already exists, require explicit overwrite confirmation.
    if (Test-Path $sigPath) {
        $existingSigHash = Sha256File $sigPath
        Write-Host "Existing signature detected: $sigPath" -ForegroundColor Yellow
        Write-Host "SHA256(existing sig): $existingSigHash" -ForegroundColor Yellow
        $overwrite = Read-Host "Signature already exists. Overwrite? (y/n)"
        if ($overwrite -ne 'y') {
            Fail "Signing aborted by operator (existing .sig not overwritten)." 11
        }
        Remove-Item -Force $sigPath
    }

    # Sign (passphrase prompt remains interactive)
    Write-Host "" 
    Write-Host "Signing... (passphrase prompt may appear)" -ForegroundColor Yellow
    & ssh-keygen -Y sign -f $KeyPath -n $Namespace $receiptFull
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Fail "ssh-keygen sign failed (exit_code=$exitCode)" 7
    }

    if (-not (Test-Path $sigPath)) {
        Fail "Signature file not found after signing: $sigPath" 8
    }

    $sigHash = Sha256File $sigPath

    Write-Host "" 
    Write-Host "Success." -ForegroundColor Green
    Write-Host "SHA256(receipt): $receiptHash" -ForegroundColor Green
    Write-Host "SHA256(sig):     $sigHash" -ForegroundColor Green
    Write-Host "Signature path:  $sigPath" -ForegroundColor Green

    # Write local signing receipt (safe metadata only)
    $safeVhdxRef = $vhdxPath
    try {
        # optionally redact drive letter
        $safeVhdxRef = $vhdxPath -replace "^[A-Z]:", "X:"
    } catch { }

    $signingReceipt = [ordered]@{
        correlation_id = $correlationId
        parent_correlation_id = $ParentCorrelationId
        ts_utc = (Get-Date).ToUniversalTime().ToString('o')
        identity = $Identity
        namespace = $Namespace
        receipt = [ordered]@{ path = $receiptFull; sha256 = $receiptHash }
        signature = [ordered]@{ path = $sigPath; sha256 = $sigHash }
        vhdx = [ordered]@{ path = $safeVhdxRef }
        tool = [ordered]@{ name = "tools/calyx_sign.ps1"; version = "v1.1.1" }
        statement = "No secrets were stored or logged. Passphrase was entered by a human at the ssh-keygen prompt."
    }

    $signingReceipt | ConvertTo-Json -Depth 6 | Set-Content -Path $signingReceiptPath -Encoding UTF8
} finally {
    # Always detach vhdx
    try {
        $detachResult = RunDiskpart -Label "detach" -Lines @(
            "select vdisk file=""$vhdxPath""",
            "detach vdisk"
        )
        if ($detachResult.exit_code -ne 0) {
            WarnHigh "diskpart detach failed (exit_code=$($detachResult.exit_code))."
            WarnHigh "Remediation: open an elevated PowerShell and run Disk Management/Hyper-V to detach the VHD, or reboot if necessary."
        }
    } catch {
        WarnHigh "diskpart detach threw an exception: $($_.Exception.Message)"
        WarnHigh "Remediation: manually detach the VHD (Disk Management) or reboot if necessary."
    }
}

# Final note
Write-Host "Signing receipt written: $signingReceiptPath" -ForegroundColor Cyan
