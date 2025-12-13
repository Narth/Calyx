<#
.SYNOPSIS
  Launcher that runs a Calyx Python tool, captures stdout/stderr to a timestamped log,
  and returns the child's exit code.

.DESCRIPTION
  Designed for use by Scheduled Tasks running as SYSTEM. The launcher resolves an
  absolute Python path (or uses provided one), runs the target script with args,
  ensures working directory is the repo root, and writes a log under outgoing/tasks/.

  Example:
    powershell -NoProfile -ExecutionPolicy Bypass -File calyx_task_launcher.ps1 --script C:\Calyx_Terminal\tools\alerts_cron.py --script-args "--run-once" --task-name "Alerts Cleanup"
#>
param(
    [Parameter(Mandatory=$true)][string]$script,
    [string]$scriptArgs = "",
    [string]$taskName = "calyx_task",
    [string]$pythonPath = ""
)

Set-StrictMode -Version Latest

try {
    $root = (Resolve-Path "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)\..\").Path
} catch {
    $root = Get-Location
}

# Resolve python
if ([string]::IsNullOrWhiteSpace($pythonPath)) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $python = $cmd.Source } else { $python = "python" }
} else {
    if (Test-Path $pythonPath) { $python = (Resolve-Path $pythonPath).ProviderPath } else { $python = $pythonPath }
}

# Prepare logs
$outDir = Join-Path $root "outgoing\tasks"
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$safeName = ($taskName -replace '\\s+','_') -replace '[^A-Za-z0-9_\-]',''
$logFile = Join-Path $outDir ("{0}_{1}.log" -f $safeName, $ts)

Write-Host "[calyx_task_launcher] starting: $taskName -> $script $scriptArgs";
Write-Host "[calyx_task_launcher] working dir: $root";
Write-Host "[calyx_task_launcher] python: $python";
Write-Host "[calyx_task_launcher] logfile: $logFile";

Push-Location $root
try {
    # Build argument array: script plus split scriptArgs
    $argArray = @()
    $argArray += $script
    if (-not [string]::IsNullOrWhiteSpace($scriptArgs)) {
        $argArray += $scriptArgs -split '\s+'
    }
    "---- Calyx Task Log: $taskName ($ts) ----" | Out-File -FilePath $logFile -Encoding utf8
    # Execute python with arguments, capture output and append to log
    & $python @argArray 2>&1 | Tee-Object -FilePath $logFile -Append
    $exit = $LASTEXITCODE
} catch {
    "[calyx_task_launcher] exception: $_" | Out-File -FilePath $logFile -Append
    $exit = 2
} finally {
    Pop-Location
}

Write-Host "[calyx_task_launcher] finished: exit=$exit log=$logFile"
exit $exit
