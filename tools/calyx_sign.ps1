# calyx_sign.ps1 — Human-invoked receipt signing ceremony (Windows)
# Reproducible implementation for Calyx_Terminal; compatible with C:\Calyx\tools\calyx_sign.ps1 behavior.
# Requires: receipt under governance/approvals/ (or -Force), USB key with VHDX containing Architect key.
# See docs/operations/calyx_sign.md

param(
    [Parameter(Mandatory = $true)]
    [string] $Receipt,
    [string] $Namespace = "calyx",
    [string] $Identity = "architect",
    [string] $KeyPath = "V:\calyx_identity\architect_ed25519",
    [string] $VhdxName = "architect_identity.vhdx",
    [string] $SearchDrives = "D,E,F,G,H,I,J,K,L,M",
    [string] $ParentCorrelationId = "",
    [switch] $Force,
    [switch] $NoConfirm
)

$ErrorActionPreference = "Stop"
$scriptVersion = "v1.2.0"

# Resolve receipt to full path
$receiptPath = $Receipt
if (-not [System.IO.Path]::IsPathRooted($receiptPath)) {
    $receiptPath = Join-Path (Get-Location) $receiptPath
}
$receiptPath = [System.IO.Path]::GetFullPath($receiptPath)
if (-not (Test-Path -LiteralPath $receiptPath -PathType Leaf)) {
    Write-Error "Receipt file not found: $receiptPath"
}

# Check governance/approvals
$normalized = $receiptPath -replace '\\', '/'
$underApprovals = $normalized -match 'governance/approvals/'
if (-not $underApprovals -and -not $Force) {
    Write-Error "Receipt is not under governance/approvals/. Use -Force to sign anyway (you will be prompted)."
}
if (-not $underApprovals -and $Force) {
    $confirm = Read-Host "Receipt is outside governance/approvals. Type YES to continue"
    if ($confirm -ne "YES") {
        Write-Host "Aborted."
        exit 1
    }
}

# Compute SHA256 of receipt (UTF-8 file content)
$receiptBytes = [System.IO.File]::ReadAllBytes($receiptPath)
$sha256 = [System.Security.Cryptography.SHA256]::Create()
$hashBytes = $sha256.ComputeHash($receiptBytes)
$receiptSha256 = [BitConverter]::ToString($hashBytes).Replace("-", "")
$first8 = $receiptSha256.Substring(0, 8)

# Parse receipt for summary and optional COMMIT
$receiptJson = $null
try {
    $receiptJson = Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch { }

Write-Host ""
Write-Host "--- Receipt summary ---"
Write-Host "Path: $receiptPath"
Write-Host "SHA256 (first 8): $first8"
if ($receiptJson) {
    if ($receiptJson.PSObject.Properties['proposal_id']) { Write-Host "proposal_id: $($receiptJson.proposal_id)" }
    if ($receiptJson.PSObject.Properties['action']) { Write-Host "action: $($receiptJson.action)" }
    if ($receiptJson.PSObject.Properties['scope']) { Write-Host "scope: $($receiptJson.scope)" }
    if ($receiptJson.PSObject.Properties['commit_hash']) { Write-Host "commit_hash: $($receiptJson.commit_hash)" }
}
Write-Host "------------------------"
Write-Host ""

$sigPath = $receiptPath + ".sig"
if (Test-Path -LiteralPath $sigPath -PathType Leaf) {
    $existingSigBytes = [System.IO.File]::ReadAllBytes($sigPath)
    $existingSigHash = [BitConverter]::ToString($sha256.ComputeHash($existingSigBytes)).Replace("-", "")
    Write-Host "Signature file already exists. SHA256(existing sig): $existingSigHash"
    $overwrite = Read-Host "Overwrite? (y/n)"
    if ($overwrite -ne "y" -and $overwrite -ne "Y") {
        Write-Host "Aborted (signature not overwritten)."
        exit 1
    }
}

# Human confirmation (captcha: you must type the full line including the word SIGN)
if (-not $NoConfirm) {
    $expectedCommit = ""
    if ($receiptJson -and $receiptJson.PSObject.Properties['commit_hash']) {
        $expectedCommit = " COMMIT $($receiptJson.commit_hash)"
    }
    $expectedLine = "SIGN $first8$expectedCommit"
    Write-Host "Type the following line exactly to confirm (include the word SIGN):"
    Write-Host ""
    Write-Host "  $expectedLine" -ForegroundColor Cyan
    Write-Host ""
    $typed = Read-Host "Your input"
    if ($typed -ne $expectedLine) {
        Write-Host "Confirmation did not match. Aborted."
        exit 1
    }
}

Write-Host ""
Write-Host "Insert USB key (VHDX with Architect identity), then press Enter."
$null = Read-Host

# Find VHDX on removable drives
$drives = $SearchDrives -split ',' | ForEach-Object { $_.Trim() }
$vhdxPath = $null
foreach ($d in $drives) {
    $candidate = "${d}:\calyx_identity\$VhdxName"
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
        $vhdxPath = $candidate
        break
    }
}
if (-not $vhdxPath) {
    Write-Error "VHDX not found. Looked for \calyx_identity\$VhdxName on drives: $($drives -join ', '). Insert key and ensure path exists."
}

$vhdxDrive = [System.IO.Path]::GetPathRoot($vhdxPath).TrimEnd('\').TrimEnd(':')
Write-Host "Found VHDX on drive ${vhdxDrive}: $vhdxPath"
Write-Host "(Script uses this path only; no other drive letter is expected.)"

# Diskpart: attach and assign V (or use existing mount if already attached)
$assignLetter = "V"
$weAttached = $false
$attachScript = [System.IO.Path]::GetTempFileName()
$attachLines = @(
    "select vdisk file=$vhdxPath",
    "attach vdisk",
    "select partition 1",
    "assign letter=$assignLetter",
    "exit"
)
[System.IO.File]::WriteAllLines($attachScript, $attachLines, [System.Text.Encoding]::ASCII)
try {
    $attachResult = & diskpart /s $attachScript 2>&1
    $attachResultText = $attachResult | Out-String
    if ($LASTEXITCODE -ne 0) {
        if ($attachResultText -match "already attached") {
            Write-Host "VHDX is already attached (e.g. you mounted it manually). Looking for key on drives..."
            $weAttached = $false
            $mountedKeyPath = $null
            $driveLetters = 67..90 | ForEach-Object { [char]$_ }  # C through Z
            foreach ($letter in $driveLetters) {
                $candidate = "${letter}:\calyx_identity\architect_ed25519"
                if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                    $mountedKeyPath = $candidate
                    Write-Host "Using key at $mountedKeyPath"
                    break
                }
            }
            if (-not $mountedKeyPath) {
                Remove-Item -LiteralPath $attachScript -Force -ErrorAction SilentlyContinue
                Write-Error "VHDX is already attached but key file \calyx_identity\architect_ed25519 was not found on any drive (C-Z). Mount the VHD and ensure the key is at that path, or detach it and run the script again."
            }
        } else {
            Write-Host $attachResultText
            $code = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } else { "unknown (e.g. elevated subprocess)" }
            throw "diskpart attach failed with exit code $code. If you see an elevation prompt, diskpart may run in a different session; try running PowerShell as Administrator from the start, or pre-mount the VHD in Explorer and run the script again."
        }
    } else {
        $weAttached = $true
        $mountedKeyPath = "${assignLetter}:\calyx_identity\architect_ed25519"
    }
} finally {
    Remove-Item -LiteralPath $attachScript -Force -ErrorAction SilentlyContinue
}

# If we attached, wait for mounted volume to be readable (V: can lag for child processes)
if ($weAttached) {
    $maxWaitSeconds = 15
    $waited = 0
    $keyReady = $false
    while ($waited -lt $maxWaitSeconds) {
        if (Test-Path -LiteralPath $mountedKeyPath -PathType Leaf) {
            try {
                $null = [System.IO.File]::OpenRead($mountedKeyPath).ReadByte()
                $keyReady = $true
                break
            } catch {
                # File exists but not yet readable (e.g. volume still mounting)
            }
        }
        Start-Sleep -Seconds 2
        $waited += 2
    }
    if (-not $keyReady) {
        $detachScript = [System.IO.Path]::GetTempFileName()
        $detachLines = @("select vdisk file=$vhdxPath", "detach vdisk", "exit")
        [System.IO.File]::WriteAllLines($detachScript, $detachLines, [System.Text.Encoding]::ASCII)
        & diskpart /s $detachScript 2>&1 | Out-Null
        Remove-Item -LiteralPath $detachScript -Force -ErrorAction SilentlyContinue
        Write-Error "Key file at $mountedKeyPath was not readable after ${maxWaitSeconds}s (V: may not have mounted). Detached VHDX."
    }
}

# Run ssh-keygen from cmd; start cmd with WorkingDirectory = key dir so it (and the pipeline) see the key drive
$keyDir = (Get-Item -LiteralPath $mountedKeyPath).DirectoryName
$sigPathAbs = [System.IO.Path]::GetFullPath($sigPath)
$keyFileName = (Get-Item -LiteralPath $mountedKeyPath).Name

# Pre-check: ensure this process can read the key (if you mounted VHD in Explorer, run script from non-Admin PowerShell)
try {
    $null = [System.IO.File]::OpenRead($mountedKeyPath).ReadByte()
} catch {
    Write-Error "Cannot read key at $mountedKeyPath from this process. If you mounted the VHD manually, run this script from a normal (non-Administrator) PowerShell window so the drive is visible."
}

try {
    # Start cmd with -WorkingDirectory $keyDir so the key drive is current; then run pipeline
    $pipeCmd = "type `"$receiptPath`" | ssh-keygen -Y sign -f `"$keyFileName`" -n $Namespace -I $Identity -s `"$sigPathAbs`""
    $p = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $pipeCmd -WorkingDirectory $keyDir -Wait -NoNewWindow -PassThru
    if ($p.ExitCode -ne 0) {
        throw "ssh-keygen -Y sign failed with exit code $($p.ExitCode). If you pre-mounted the VHD, try running this script from a non-Administrator PowerShell so the key drive is visible."
    }

    if (-not (Test-Path -LiteralPath $sigPath -PathType Leaf)) {
        throw "Signature file was not created: $sigPath"
    }
    $sigBytes = [System.IO.File]::ReadAllBytes($sigPath)
    $sigSha256 = [BitConverter]::ToString($sha256.ComputeHash($sigBytes)).Replace("-", "")
    Write-Host "Signature written. SHA256(sig): $sigSha256"
} finally {
    # Detach VHDX only if we attached it (skip if user had already mounted it)
    if ($weAttached) {
        $detachScript = [System.IO.Path]::GetTempFileName()
        $detachLines = @("select vdisk file=$vhdxPath", "detach vdisk", "exit")
        [System.IO.File]::WriteAllLines($detachScript, $detachLines, [System.Text.Encoding]::ASCII)
        $detachResult = & diskpart /s $detachScript 2>&1
        Remove-Item -LiteralPath $detachScript -Force -ErrorAction SilentlyContinue
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "*** WARNING: VHDX detachment may have failed (exit code $LASTEXITCODE). ***"
            Write-Host "Manually detach the VHD in Disk Management or reboot if necessary."
            Write-Host $detachResult
        } else {
            Write-Host "VHDX detached."
        }
    } else {
        Write-Host "(VHDX was already attached; leaving it mounted. Detach manually if desired.)"
    }
}

# Writing signing receipt (safe metadata only)
$receiptDir = Split-Path -Parent $receiptPath
$governanceDir = Split-Path -Parent $receiptDir
$signingReceiptsDir = Join-Path $governanceDir "receipts\signing"
$receiptBasename = [System.IO.Path]::GetFileName($receiptPath)
$signingReceiptPath = Join-Path $signingReceiptsDir ($receiptBasename + ".signing_receipt.json")

if (-not (Test-Path -LiteralPath $signingReceiptsDir -PathType Container)) {
    New-Item -ItemType Directory -Path $signingReceiptsDir -Force | Out-Null
}

$hex = "0123456789abcdef"
$correlationId = -join ((1..12) | ForEach-Object { $hex[(Get-Random -Maximum 16)] })

$tsUtc = [DateTime]::UtcNow.ToString("o")
$signingReceipt = @{
    correlation_id     = $correlationId
    parent_correlation_id = $ParentCorrelationId
    ts_utc             = $tsUtc
    identity           = $Identity
    namespace          = $Namespace
    receipt            = @{ path = $receiptPath; sha256 = $receiptSha256 }
    signature          = @{ path = $sigPath; sha256 = $sigSha256 }
    vhdx               = @{ path = $vhdxPath }
    tool               = @{ name = "tools/calyx_sign.ps1"; version = $scriptVersion }
    statement          = "No secrets were stored or logged. Passphrase was entered by a human at the ssh-keygen prompt."
} | ConvertTo-Json -Depth 4 -Compress:$false
[System.IO.File]::WriteAllText($signingReceiptPath, $signingReceipt, [System.Text.UTF8Encoding]::new($false))
Write-Host "Signing receipt written: $signingReceiptPath"
Write-Host "Done."
