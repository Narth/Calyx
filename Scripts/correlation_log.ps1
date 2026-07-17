# Append one line to runtime/correlation_activity.jsonl for correlation with CPU/utilization.
# Correlation does not imply causation. See docs/CORRELATION_LOGGING.md.
# Usage: .\Scripts\correlation_log.ps1 -Component "station_health" -Event "history_write" [-DurationMs 0]

param(
    [Parameter(Mandatory=$true)][string]$Component,
    [Parameter(Mandatory=$true)][string]$Event,
    [int]$DurationMs = -1
)

$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
$logPath = Join-Path $repoRoot "runtime\correlation_activity.jsonl"
$disablePath = Join-Path $repoRoot "runtime\correlation_log.disabled"
if (Test-Path $disablePath) { exit 0 }
if ($env:CALYX_CORRELATION_LOG_DISABLED -eq "1") { exit 0 }

$ts = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
$obj = @{ ts_utc = $ts; component = $Component.Substring(0, [Math]::Min(32, $Component.Length)); event = $Event.Substring(0, [Math]::Min(64, $Event.Length)) }
if ($DurationMs -ge 0) { $obj.duration_ms = $DurationMs }
$line = ($obj | ConvertTo-Json -Compress) + "`n"
$dir = Split-Path $logPath
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
