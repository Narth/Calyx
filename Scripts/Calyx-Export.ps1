<# Calyx-Export.ps1 (v2a)
   - Fix: Here-string closed at column 1 (no indent)
   - Fix: Balanced try/catch blocks
   - Simpler: Depth-limited Projects copy (0/1/2)
   - Better: Zip compression level + SHA256
#>

[CmdletBinding(SupportsShouldProcess=$true)]
param(
  [string] $Root = "C:\Calyx_Terminal",
  [string] $Label = "",
  [switch] $IncludeVenv,
  [switch] $IncludeCache,
  [int]    $MaxProjectDepth = 1,   # 0=just Projects folder marker; 1=top-level; 2=one level deeper
  [switch] $DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-Dir([string]$path) { if (-not (Test-Path $path)) { New-Item -ItemType Directory -Path $path | Out-Null } }
function Copy-Safe {
  param([string]$Source,[string]$Dest,[switch]$Recurse,[string[]]$Exclude=@("*.pyc","*.pyo","*.pdb",".git*","*.tmp","*.log","__pycache__"))
  if (-not (Test-Path $Source)) { return }
  if ($DryRun) {
    Write-Host "[DryRun] Copy $Source -> $Dest (Recurse=$($Recurse.IsPresent)) Exclude=$($Exclude -join ',')"
  } else {
    Copy-Item $Source $Dest -Recurse:$Recurse -Force -ErrorAction SilentlyContinue -Exclude $Exclude
  }
}

# --- Paths
$rootPath   = (Resolve-Path $Root).Path
$scriptsDir = Join-Path $rootPath "Scripts"
$codexDir   = Join-Path $rootPath "Codex"
$projDir    = Join-Path $rootPath "Projects"
$confFile   = Join-Path $rootPath "config.yaml"
$archives   = Join-Path $codexDir "Archives"
New-Dir $codexDir; New-Dir $archives

# --- Stamp & label
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$labelSan = if ($Label) { "_" + ($Label -replace '[^\w\-]+','-') } else { "" }

# --- Stage
$stage = Join-Path $env:TEMP "CalyxExport_$ts"
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Dir $stage
$stageScripts = Join-Path $stage "Scripts"
$stageCodex   = Join-Path $stage "Codex"
$stageProj    = Join-Path $stage "Projects"
$metaDir      = Join-Path $stage "_meta"
$null = ($stageScripts,$stageCodex,$stageProj,$metaDir | ForEach-Object { New-Dir $_ })

# --- Config
if (Test-Path $confFile) { Copy-Safe -Source $confFile -Dest (Join-Path $stage "config.yaml") }

# --- Scripts (+ optional .venv/.cache)
Copy-Safe -Source "$scriptsDir\*" -Dest $stageScripts -Recurse
if ($IncludeVenv) {
  $venv = Join-Path $scriptsDir ".venv"
  if (Test-Path $venv) { Write-Host "[Export] Including .venv..."; Copy-Safe -Source $venv -Dest (Join-Path $stageScripts ".venv") -Recurse }
}
if ($IncludeCache) {
  foreach ($cand in @(".cache","cache")) {
    $cpath = Join-Path $scriptsDir $cand
    if (Test-Path $cpath) { Write-Host "[Export] Including cache: $cand"; Copy-Safe -Source $cpath -Dest (Join-Path $stageScripts $cand) -Recurse }
  }
}

# --- Projects (depth-limited)
if (Test-Path $projDir) {
  switch ($MaxProjectDepth) {
    0 { New-Dir $stageProj }                                     # marker only
    1 {
      # top-level files + empty subdirs
      Get-ChildItem $projDir -File -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-Safe -Source $_.FullName -Dest $stageProj
      }
      Get-ChildItem $projDir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        New-Dir (Join-Path $stageProj $_.Name)
      }
    }
    default {
      # depth=2: include subdir files one level deeper (still lightweight)
      # base level
      Get-ChildItem $projDir -File -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-Safe -Source $_.FullName -Dest $stageProj
      }
      Get-ChildItem $projDir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $d1 = Join-Path $stageProj $_.Name
        New-Dir $d1
        # files in subdir
        Get-ChildItem $_.FullName -File -ErrorAction SilentlyContinue | ForEach-Object {
          Copy-Safe -Source $_.FullName -Dest $d1
        }
        # create names of sub-subdirs, but do not recurse contents
        Get-ChildItem $_.FullName -Directory -ErrorAction SilentlyContinue | ForEach-Object {
          New-Dir (Join-Path $d1 $_.Name)
        }
      }
    }
  }
}

# --- Codex (exclude Archives)
if (Test-Path $codexDir) {
  Get-ChildItem $codexDir -Force | Where-Object { $_.Name -ne "Archives" } | ForEach-Object {
    Copy-Safe -Source $_.FullName -Dest $stageCodex -Recurse
  }
}

# --- Metadata
$pyExe = Join-Path $scriptsDir ".venv\Scripts\python.exe"
if (Test-Path $pyExe) {
  try {
    if ($DryRun) { Write-Host "[DryRun] pip freeze -> _meta\pip_freeze.txt" }
    else { & $pyExe -m pip freeze | Out-File -Encoding UTF8 (Join-Path $metaDir "pip_freeze.txt") }
  } catch {
    if (-not $DryRun) { "[warn] pip freeze failed: $($_.Exception.Message)" | Out-File -Encoding UTF8 (Join-Path $metaDir "pip_freeze.txt") }
  }
  try {
    $devDump = Join-Path $metaDir "dump_devices.py"
    @'
import sounddevice as sd
lines=[]
for i,d in enumerate(sd.query_devices()):
    lines.append(f"{i:2}  {d['name']}  in={d['max_input_channels']} out={d['max_output_channels']}  default_sr={d['default_samplerate']}")
open(r"{OUT}", "w", encoding="utf-8").write("\n".join(lines))
'@ -replace '\{OUT\}', [Regex]::Escape((Join-Path $metaDir "audio_devices.txt")) |
      Out-File -Encoding UTF8 $devDump
    if (-not $DryRun) { & $pyExe $devDump | Out-Null }
  } catch {
    Write-Warning "audio device dump failed: $($_.Exception.Message)"
  }
  try {
    $probePy = Join-Path $scriptsDir "mic_probe.py"
    if (Test-Path $probePy -and -not $DryRun) {
      & $pyExe $probePy | Out-File -Encoding UTF8 (Join-Path $metaDir "mic_probe_output.txt")
    }
  } catch {
    Write-Warning "mic probe failed: $($_.Exception.Message)"
  }
}

# --- README (safe: no here-strings)
$readmePath = Join-Path $stage "README.md"
$readmeLines = @(
  "# Calyx Export ($ts$labelSan)"
  ""
  "This archive was created by Calyx-Export.ps1. It contains:"
  "- `config.yaml`"
  "- Scripts (minus cache files; `.venv` included only if you passed -IncludeVenv)"
  "- Projects (depth-limited; default = 1)"
  "- `"_meta`" (pip freeze, audio device list, mic probe output if available)"
  ""
  "## Suggested Restore"
  "1) Unzip to a clean folder (e.g., C:\Calyx_Terminal_Restore)."
  "2) If `.venv` wasn’t included:"
  "   - Install Python 3.11.x"
  "   - `py -3.11 -m venv .venv`"
  "   - `.venv\Scripts\Activate.ps1`"
  "   - `python -m pip install --upgrade pip`"
  "   - `pip install -r _meta\pip_freeze.txt`  (or reinstall your known packages)"
  "3) Confirm config at `config.yaml`."
  "4) Test:"
  "   - `python .\Scripts\calyx_console.py begin_session`"
  "   - `python .\Scripts\quick_check.py`"
  ""
  "## Chat Export"
  "If you have the HTML/JSON export from ChatGPT/OpenAI, drop it here:"
  "`Codex\Archives\Calyx_Terminal_Session_Archive_YYYYMMDD.html` (and .json)"
)
if ($DryRun) {
  Write-Host "[DryRun] Would write README.md"
} else {
  $readmeLines -join "`r`n" | Set-Content -Encoding UTF8 $readmePath
}


# --- Zip + SHA256 + cleanup
$zipName = "Calyx_Export_${ts}${labelSan}.zip"
$zipPath = Join-Path $archives $zipName

if ($DryRun) {
  Write-Host "`n[DryRun] Export simulated. No files written."
} else {
  if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
  Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -CompressionLevel Optimal
  $sha = (Get-FileHash -Algorithm SHA256 -Path $zipPath).Hash
  $shaFile = "$zipPath.sha256.txt"
  $sha | Out-File -Encoding ASCII $shaFile
  try {
    Remove-Item $stage -Recurse -Force
  } catch {
    Write-Warning "Could not remove staging folder: $stage — $($_.Exception.Message)"
  }
  Write-Host ""
  Write-Host "✅ Export complete:" -ForegroundColor Green
  Write-Host "   $zipPath"
  Write-Host "   SHA256: $sha"
  Write-Host ""
  Write-Host "Tip: When your OpenAI email export arrives, save the .html/.json into:"
  Write-Host "   $archives"
}
