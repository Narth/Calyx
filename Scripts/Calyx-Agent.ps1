# Calyx-Agent.ps1 (ASCII-safe minimal)
# Core workflow: init -> stage -> bundle -> apply patch

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-CAPath {
  param([string]$Root = "C:\Calyx_Terminal")
  $root = (Resolve-Path $Root).Path
  $sync     = Join-Path $root "Codex\Sync"
  $inbox    = Join-Path $sync "Inbox"
  $outbox   = Join-Path $sync "Outbox"
  $backups  = Join-Path $sync "Backups"
  $archives = Join-Path $root "Codex\Archives"
  [pscustomobject]@{ Root=$root; Sync=$sync; Inbox=$inbox; Outbox=$outbox; Backups=$backups; Archives=$archives }
}

function Ensure-Dir { param([string]$Path) if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Path $Path | Out-Null } }

function Start-CalyxAgent {
  [CmdletBinding()] param([string]$Root = "C:\Calyx_Terminal")
  $p = Get-CAPath -Root $Root
  Ensure-Dir $p.Sync
  Ensure-Dir $p.Inbox
  Ensure-Dir $p.Outbox
  Ensure-Dir $p.Backups
  Ensure-Dir $p.Archives
  Write-Host "Agent ready:"
  Write-Host "  Sync:     $($p.Sync)"
  Write-Host "  Inbox:    $($p.Inbox)"
  Write-Host "  Outbox:   $($p.Outbox)"
  Write-Host "  Backups:  $($p.Backups)"
  Write-Host "  Archives: $($p.Archives)"
}

function Stage-CalyxFiles {
  [CmdletBinding()]
  param(
    [string]$Root = "C:\Calyx_Terminal",
    [string[]]$Paths
  )
  $p = Get-CAPath -Root $Root
  $ex = @("*.pyc","*.pyo","*.pdb",".git*","*.tmp","*.log","__pycache__")
  foreach($rel in $Paths){
    $src = Join-Path $p.Root $rel
    if (-not (Test-Path $src)) { Write-Warning "Missing: $rel"; continue }
    $dest = Join-Path $p.Sync $rel
    $destDir = Split-Path $dest
    Ensure-Dir $destDir
    Copy-Item -LiteralPath $src -Destination $dest -Recurse -Force -ErrorAction SilentlyContinue -Exclude $ex
    Write-Host "[Staged] $rel"
  }
}

function Make-ChatBundle {
  [CmdletBinding()]
  param(
    [string]$Root = "C:\Calyx_Terminal",
    [string]$Label = ""
  )
  $p = Get-CAPath -Root $Root
  Ensure-Dir $p.Outbox
  $ts = Get-Date -Format "yyyyMMdd_HHmmss"
  $label = if($Label){ "_"+($Label -replace '[^\w\-]+','-') } else { "" }

  $snapshot = Join-Path $p.Outbox ("chat_current_" + $ts + $label + ".txt")
  $files = Get-ChildItem -LiteralPath $p.Sync -Recurse -File | Sort-Object FullName
  $nl = "`r`n"
  $sb = New-Object System.Text.StringBuilder
  [void]$sb.Append("# Calyx Sync Snapshot (" + $ts + $label + ")" + $nl + $nl)
  foreach($f in $files){
    $rel = $f.FullName.Substring($p.Sync.Length + 1)
    [void]$sb.Append("===== BEGIN " + $rel + " =====" + $nl)
    try {
      $content = Get-Content -LiteralPath $f.FullName -Raw
    } catch {
      $content = "[[unreadable]]"
    }
    [void]$sb.Append($content + $nl)
    [void]$sb.Append("===== END " + $rel + " =====" + $nl + $nl)
  }
  $sb.ToString() | Set-Content -LiteralPath $snapshot -Encoding UTF8

  $zip = Join-Path $p.Outbox ("chat_bundle_" + $ts + $label + ".zip")
  if (Test-Path $zip) { Remove-Item -LiteralPath $zip -Force }
  Compress-Archive -Path (Join-Path $p.Sync "*") -DestinationPath $zip -CompressionLevel Optimal

  Write-Host "Bundle ready:"
  Write-Host "  TXT: $snapshot"
  Write-Host "  ZIP: $zip"
}

function Apply-ChatPatch {
  [CmdletBinding()]
  param(
    [string]$Root = "C:\Calyx_Terminal",
    [string]$Patch
  )
  $p = Get-CAPath -Root $Root
  $patchPath = if (Test-Path $Patch) { (Resolve-Path $Patch).Path } else { (Resolve-Path (Join-Path $p.Root $Patch)).Path }
  if (-not (Test-Path $patchPath)) { throw "Patch not found: $Patch" }

  $git = (Get-Command git -ErrorAction SilentlyContinue)
  if ($git) {
    Push-Location $p.Root
    try {
      if (-not (Test-Path (Join-Path $p.Root ".git"))) {
        git init | Out-Null
        git add . | Out-Null
        git commit -m "Calyx-Agent baseline" | Out-Null
      }
      git apply --reject --whitespace=fix "$patchPath"
      Write-Host "Patch applied with git. Check *.rej for any conflicts."
    } finally {
      Pop-Location
    }
    return
  }

  $dest = Join-Path $p.Inbox ("APPLY_MANUALLY_" + (Split-Path $patchPath -Leaf))
  Copy-Item -LiteralPath $patchPath -Destination $dest -Force
  Write-Warning "Git not found. Saved patch for manual apply:"
  Write-Host "  $dest"
}
