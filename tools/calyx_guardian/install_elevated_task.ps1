param(
    [string]$OutDir = "logs\calyx_guardian"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$taskName = "CalyxGuardianPhase0Elevated"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runner = Join-Path $scriptDir "run_phase0_windows.ps1"

# Repo root (two levels up from tools/calyx_guardian)
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\.." )).Path

# Use absolute paths for OutDir and logs
$absOut = (Resolve-Path (Join-Path $repoRoot $OutDir)).Path
New-Item -ItemType Directory -Force -Path $absOut | Out-Null

$stdoutPath = Join-Path $absOut "elevated_task.stdout.log"
$stderrPath = Join-Path $absOut "elevated_task.stderr.log"
$elevationStatusPath = Join-Path $absOut "elevation_status.json"

$arguments = @(
    "-NoProfile",
    "-NonInteractive",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    ($runner -replace "\\", "/"),
    "-OutDir",
    $absOut,
    "-Verify",
    "-StdoutPath",
    $stdoutPath,
    "-StderrPath",
    $stderrPath,
    "-ElevationStatusPath",
    $elevationStatusPath
)

# Ensure RunLevel Highest and Interactive logon type
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ($arguments -join " ")
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
$task = New-ScheduledTask -Action $action -Principal $principal -Settings $settings

Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null

# Post-install snapshot for auditing
$snapshotPath = Join-Path $absOut "task_definition_snapshot.txt"
$installed = Get-ScheduledTask -TaskName $taskName
$principalInfo = $installed.Principal
$actions = $installed.Actions | ForEach-Object { $_.Execute + ' ' + ($_.Arguments) }
$snapshot = @()
$snapshot += "TaskName: $taskName"
$snapshot += "UserId: $($principalInfo.UserId)"
$snapshot += "RunLevel: $($principalInfo.RunLevel)"
$snapshot += "LogonType: Interactive"
$snapshot += "Actions:"
foreach ($a in $actions) { $snapshot += "  - $a" }
$snapshot += "WorkingDirectory: $repoRoot"
$snapshot | Out-File -FilePath $snapshotPath -Encoding utf8

Write-Host "Scheduled task '$taskName' installed or updated. Snapshot written to $snapshotPath"
