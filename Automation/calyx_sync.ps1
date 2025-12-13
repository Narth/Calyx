# Station Calyx - Cloud Sync Helper
# Provides bounded-autonomy sync with audit logging, backup, and human gate for critical changes.
[CmdletBinding()]
param(
    [string]$ConfigPath = "config/sync-config.json",
    [switch]$DryRun,
    [switch]$SkipPush,
    [switch]$ForceAutoCommit
)

# Always run from repo root
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

$defaults = @{
    autoCommit        = $true
    autoCommitMessage = "chore(sync): routine Station Calyx sync"
    remote            = "origin"
    branch            = "main"
    backupEnabled     = $true
    backupDir         = "local_backups/sync"
    auditLog          = "local_backups/audit/governance_audit.log"
    # Allowed paths act as an allowlist for automation; omit sensitive dirs (logs, samples, backups).
    allowedPaths      = @("docs/*", "reports/*", "config/*", "Automation/*", "tools/*", "asr/*", "Scripts/*", "outgoing/*", "Codex/Sync/*")
    # Critical patterns halt automation unless explicitly forced and approved.
    criticalPatterns  = @(
        "Automation/*",
        "config.yaml",
        "docs/OPERATIONS.md",
        "docs/AGENT_ONBOARDING.md",
        "MCP/*",
        "logs/*",
        "samples/wake_word/*",
        "local_backups/*"
    )
    requireApproval   = $true
}

function Merge-Config {
    param($base, $override)
    $merged = @{}
    foreach ($k in $base.Keys) { $merged[$k] = $base[$k] }
    if ($override) {
        foreach ($prop in $override.PSObject.Properties) {
            $merged[$prop.Name] = $prop.Value
        }
    }
    return $merged
}

function Load-Config {
    if (Test-Path $ConfigPath) {
        try {
            return Merge-Config -base $defaults -override (Get-Content $ConfigPath -Raw | ConvertFrom-Json)
        } catch {
            Write-Warning "Config parse failed ($ConfigPath). Using defaults. $($_.Exception.Message)"
        }
    }
    return $defaults
}

function Write-Audit {
    param([string]$Message)
    $cfg = $script:cfg
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $targetDir = Split-Path $cfg.auditLog -Parent
    if ($targetDir -and -not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    }
    "$stamp`t$Message" | Out-File -FilePath $cfg.auditLog -Encoding UTF8 -Append
}

function Get-ChangedFiles {
    $raw = git status --porcelain=v1
    return $raw | ForEach-Object {
        if ($_ -match "^[ MADRCU?!]{2} (.+)$") { $matches[1].Trim() }
    }
}

function Match-Any {
    param([string]$Path, [string[]]$Patterns)
    foreach ($p in $Patterns) {
        if ($Path -like $p -or $Path.StartsWith($p.TrimEnd('/'), [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function New-BackupArchive {
    param([string[]]$Files)
    $cfg = $script:cfg
    if (-not $cfg.backupEnabled -or -not $Files -or $Files.Count -eq 0) { return }
    if (-not (Test-Path $cfg.backupDir)) { New-Item -ItemType Directory -Force -Path $cfg.backupDir | Out-Null }
    $name = "pre-sync-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".zip"
    $dest = Join-Path $cfg.backupDir $name
    try {
        Compress-Archive -Path $Files -DestinationPath $dest -Force -ErrorAction Stop
        Write-Audit "Backup created at $dest for $($Files.Count) file(s)"
    } catch {
        Write-Audit "Backup failed: $($_.Exception.Message)"
        Write-Warning "Backup failed: $($_.Exception.Message)"
    }
}

$cfg = Load-Config
$changes = Get-ChangedFiles

if (-not $changes -or $changes.Count -eq 0) {
    Write-Host "No changes detected. Nothing to sync."
    return
}

$boundaryViolations = @()
if ($cfg.allowedPaths -and $cfg.allowedPaths.Count -gt 0) {
    $boundaryViolations = $changes | Where-Object { -not (Match-Any -Path $_ -Patterns $cfg.allowedPaths) }
}

if ($boundaryViolations.Count -gt 0) {
    Write-Audit "Boundary block: $($boundaryViolations -join ', ')"
    Write-Warning "Boundary check failed. Human review required before syncing."
    return
}

$criticalHits = $changes | Where-Object { Match-Any -Path $_ -Patterns $cfg.criticalPatterns }
if ($criticalHits.Count -gt 0 -and $cfg.requireApproval -and -not $ForceAutoCommit) {
    Write-Audit "Critical change requires approval: $($criticalHits -join ', ')"
    Write-Host "Critical change detected. Capture approval before running with -ForceAutoCommit."
    return
}

Write-Host "Changes: $($changes -join ', ')" 
Write-Audit "Sync start (autoCommit=$($cfg.autoCommit) push=$(-not $SkipPush)) for $($changes.Count) file(s)"

if ($DryRun) {
    Write-Host "Dry run: no commit/push performed."
    return
}

New-BackupArchive -Files $changes

git add --all

if ($cfg.autoCommit -or $ForceAutoCommit) {
    git commit -m $cfg.autoCommitMessage
    Write-Audit "Commit created: $($cfg.autoCommitMessage)"
} else {
    Write-Host "Auto-commit disabled; staged changes left for manual commit."
    Write-Audit "Auto-commit skipped; changes staged only."
}

if (-not $SkipPush) {
    git push $cfg.remote $cfg.branch
    Write-Audit "Pushed to $($cfg.remote)/$($cfg.branch)"
} else {
    Write-Host "Push skipped by request."
    Write-Audit "Push skipped by request."
}
