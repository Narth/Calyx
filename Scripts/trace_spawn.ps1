param(
  [int]$Seconds = 30,
  [int]$IntervalMs = 50,
  [string]$LogPath = "state/spawn_trace.jsonl",
  [string]$FilterRegex = "",
  [switch]$UseCimSnapshot
)

$ErrorActionPreference = "SilentlyContinue"

try {
  $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} catch {
  $repoRoot = (Get-Location).Path
}

$logFullPath =
  if ([System.IO.Path]::IsPathRooted($LogPath)) { $LogPath }
  else { Join-Path $repoRoot $LogPath }

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $logFullPath) | Out-Null

$filter =
  if ([string]::IsNullOrWhiteSpace($FilterRegex)) { $null }
  else { [regex]::new($FilterRegex, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase) }

function _tryGetCimProcess([int]$pid) {
  try { Get-CimInstance Win32_Process -Filter "ProcessId=$pid" } catch { $null }
}

$seen = New-Object "System.Collections.Generic.HashSet[int]"
if ($UseCimSnapshot) {
  Get-CimInstance Win32_Process | ForEach-Object { [void]$seen.Add([int]$_.ProcessId) }
} else {
  Get-Process | ForEach-Object { [void]$seen.Add($_.Id) }
}

@{ ts = (Get-Date).ToString("o"); event = "start"; seconds = $Seconds; interval_ms = $IntervalMs } |
  ConvertTo-Json -Compress |
  Out-File -FilePath $logFullPath -Encoding utf8 -Append

$deadline = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $deadline) {
  $snap =
    if ($UseCimSnapshot) { Get-CimInstance Win32_Process }
    else { Get-Process }

  foreach ($p in $snap) {
    $pid =
      if ($UseCimSnapshot) { [int]$p.ProcessId }
      else { [int]$p.Id }

    if (-not $seen.Add($pid)) { continue }

    $title = ""
    if (-not $UseCimSnapshot) {
      try { $title = $p.MainWindowTitle } catch { $title = "" }
    }

    $cim =
      if ($UseCimSnapshot) { $p }
      else { _tryGetCimProcess -pid $pid }

    $name =
      if ($UseCimSnapshot) { [string]$p.Name }
      else { [string]$p.ProcessName }

    $cmd = if ($cim) { [string]$cim.CommandLine } else { "" }
    $ppid = if ($cim) { [int]$cim.ParentProcessId } else { 0 }

    $parent = if ($ppid -gt 0) { _tryGetCimProcess -pid $ppid } else { $null }
    $pname = if ($parent) { [string]$parent.Name } else { "" }
    $pcmd = if ($parent) { [string]$parent.CommandLine } else { "" }

    $haystack = ($name + "`n" + $title + "`n" + $cmd + "`n" + $pname + "`n" + $pcmd)
    if ($filter -and -not $filter.IsMatch($haystack)) { continue }

    $evt = [ordered]@{
      ts = (Get-Date).ToString("o")
      pid = $pid
      name = $name
      title = $title
      cmd = $cmd
      ppid = $ppid
      pname = $pname
      pcmd = $pcmd
    }

    $line = ($evt | ConvertTo-Json -Compress)
    $line | Out-File -FilePath $logFullPath -Encoding utf8 -Append
    Write-Host $line
  }

  Start-Sleep -Milliseconds $IntervalMs
}

@{ ts = (Get-Date).ToString("o"); event = "end" } |
  ConvertTo-Json -Compress |
  Out-File -FilePath $logFullPath -Encoding utf8 -Append
