# request_calyx_sign.ps1 — Calyx Sign request method: create (or use) an approval receipt and invoke the sign flow.
# Use for any task or request that requires an Architect key signature.
# See docs/operations/CALYX_SIGN_REQUEST_METHOD.md

param(
    [Parameter(ParameterSetName = "ByTask")]
    [string] $TaskId,
    [Parameter(ParameterSetName = "ByTask")]
    [string] $Statement,
    [Parameter(ParameterSetName = "ByTask")]
    [string] $Action = "calyx_sign_approve",
    [Parameter(ParameterSetName = "ByTask")]
    [string] $Scope = "",
    [Parameter(ParameterSetName = "ByTask")]
    [string] $CommitHash = "",
    [Parameter(ParameterSetName = "ByTask")]
    [string] $PolicyPath = "",
    [Parameter(ParameterSetName = "ByTask")]
    [switch] $Force,
    [Parameter(ParameterSetName = "ByReceipt")]
    [string] $Receipt = "",
    [switch] $PromptOnly,
    [switch] $FromKeyDir
)

$ErrorActionPreference = "Stop"

$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
$approvalsDir = Join-Path $repoRoot "governance\approvals"
$signScript = Join-Path $repoRoot "tools\calyx_sign.ps1"
$promptScript = Join-Path $repoRoot "Scripts\prompt_calyx_sign.ps1"

function Get-FileSha256 {
    param([string]$Path)
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace("-", "")
}

# Resolve receipt path: either -Receipt (existing) or create from -TaskId
$receiptPath = $null

if ($Receipt) {
    $receiptPath = $Receipt
    if (-not [System.IO.Path]::IsPathRooted($receiptPath)) {
        $receiptPath = [System.IO.Path]::GetFullPath((Join-Path $repoRoot ($receiptPath -replace '^\.\\', '')))
    }
    if (-not (Test-Path -LiteralPath $receiptPath -PathType Leaf)) {
        Write-Error "Receipt not found: $receiptPath"
    }
} else {
    if (-not $TaskId -or -not $Statement) {
        Write-Error "Provide either -Receipt <path> for an existing receipt, or -TaskId and -Statement to create a new approval receipt."
    }
    if (-not $Scope) { $Scope = $TaskId }
    $receiptPath = Join-Path $approvalsDir "$TaskId.approval.json"
    if ((Test-Path -LiteralPath $receiptPath -PathType Leaf) -and -not $Force) {
        Write-Host "Receipt already exists: $receiptPath" -ForegroundColor Yellow
        $overwrite = Read-Host "Overwrite? (y/n)"
        if ($overwrite -ne "y" -and $overwrite -ne "Y") {
            Write-Host "Using existing receipt. Run with -Receipt to invoke sign for it." -ForegroundColor Gray
            & $promptScript -Receipt $receiptPath
            if (-not $PromptOnly) {
                $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $signScript, "-Receipt", $receiptPath)
                if ($FromKeyDir) { $args += "-FromKeyDir" }
                & powershell $args
            }
            return
        }
    }
    # Build approval object
    $createdUtc = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    $body = @{
        proposal_id = $TaskId
        action      = $Action
        scope       = $Scope
        statement   = $Statement
        created_utc = $createdUtc
        signature   = @{
            required = $true
            namespace = "calyx"
            status   = "unsigned"
            note     = "Sign this file with your Architect key. Produce $TaskId.approval.json.sig. Absence of a valid signature is explicit denial."
        }
    }
    if ($CommitHash) {
        $body["commit_hash"] = $CommitHash
    }
    if ($PolicyPath) {
        $policyAbs = if ([System.IO.Path]::IsPathRooted($PolicyPath)) { $PolicyPath } else { Join-Path $repoRoot $PolicyPath }
        if (Test-Path -LiteralPath $policyAbs -PathType Leaf) {
            $body["proposal"] = @{
                path  = ($policyAbs -replace [regex]::Escape($repoRoot + [IO.Path]::DirectorySeparatorChar), "").Replace("\", "/")
                sha256 = Get-FileSha256 -Path $policyAbs
            }
        }
    }
    $json = $body | ConvertTo-Json -Depth 5 -Compress:$false
    if (-not (Test-Path -LiteralPath $approvalsDir -PathType Container)) {
        New-Item -ItemType Directory -Path $approvalsDir -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($receiptPath, $json, [System.Text.UTF8Encoding]::new($false))
    Write-Host "Created: $receiptPath" -ForegroundColor Green
}

# Prompt (show commands)
& $promptScript -Receipt $receiptPath

# Optionally run the ceremony in this session
if (-not $PromptOnly) {
    Write-Host "Running Calyx Sign in this window..." -ForegroundColor Cyan
    $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $signScript, "-Receipt", $receiptPath)
    if ($FromKeyDir) { $args += "-FromKeyDir" }
    & powershell $args
}
