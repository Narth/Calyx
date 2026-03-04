# Station Health Loop — 1-second schedule (default), writes to runtime/station_health.json.
# Lightweight check (CPU, RAM, GPU, top processes). Tied to HEARTBEAT and STATE via update_state_checks.ps1.
# History: appends compact snapshot to runtime/station_health_history.jsonl every HistoryIntervalSec (default 60).
# GPU: conservative thresholds — too much GPU = entropy, crash. Fail early.
# Usage: .\Scripts\station_health_loop.ps1 [-IntervalSec 1] [-HistoryIntervalSec 60] [-StopFile path]
# Note: 1s needed to detect when Station comes down after load; 4s+ too slow to catch cooldown.
# Run in background. Writes runtime/station_health.json. Stop by creating the StopFile (default: runtime/station_health.stop).
# See: docs/operations/STATION_HEALTH_BLOOMOS_AUDIT.md

param(
    [int]$IntervalSec = 1,
    [int]$HistoryIntervalSec = 60,
    [string]$StopFile = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) { $repoRoot = (Get-Location).Path }

if (-not $StopFile) { $StopFile = Join-Path $repoRoot "runtime\station_health.stop" }
$runtimeDir = Join-Path $repoRoot "runtime"
$outPath = Join-Path $runtimeDir "station_health.json"
$historyPath = Join-Path $runtimeDir "station_health_history.jsonl"
$MaxHistoryLines = 1440   # 24h at 1/min
if (-not (Test-Path $runtimeDir)) { New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null }

# CPU/RAM: match build_safety_check
$WarnCpuPct = 75
$FailCpuPct = 92
$WarnRamPct = 80
$FailRamPct = 92
# GPU: conservative — activity decision-making; too much = crash. Fail earlier than CPU.
$WarnGpuPct = 70
$FailGpuPct = 88
$WarnVramPct = 80
$FailVramPct = 95
$WarnGpuTempC = 80
$FailGpuTempC = 90

# Rolling buffer for entropy baseline and cadence (last 60 samples)
$script:cpuHistory = @()
$script:lastHistoryTs = $null   # UTC; write to history every HistoryIntervalSec

# Non-blocking CPU read. Get-Counter -SampleInterval 1 blocks ~1s and causes periodic CPU spikes on the cadence of the loop.
# WMI snapshot returns immediately; slightly less precise but avoids the spike.
function Get-LightCpuPct {
    try {
        $p = Get-CimInstance -ClassName Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'" -ErrorAction SilentlyContinue
        if ($p -and $null -ne $p.PercentProcessorTime) { [int]$p.PercentProcessorTime } else { $null }
    } catch { $null }
}

function Get-LightRamPct {
    try {
        $os = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction SilentlyContinue
        if ($os -and $os.TotalVisibleMemorySize -gt 0) {
            [int][Math]::Round((1 - $os.FreePhysicalMemory / $os.TotalVisibleMemorySize) * 100)
        } else { $null }
    } catch { $null }
}

function Get-TopProcesses {
    try {
        Get-Process | Where-Object { $_.CPU -ge 0 } | Sort-Object CPU -Descending | Select-Object -First 3 |
            ForEach-Object { @{ name = $_.ProcessName; pid = $_.Id; cpu_sec = [math]::Round($_.CPU, 1); mem_mb = [math]::Round($_.WorkingSet64 / 1MB, 1) } }
    } catch { @() }
}

# Top processes by current CPU % (entropy attribution). Uses WMI snapshot; non-blocking.
# Per-process CPU can exceed 100% on multi-core (e.g. Ollama 700% = 7 cores). Cap at 100% for
# decision-making: 100% = max allowed throughput; beyond = damaging. Raw kept for diagnostics.
function Get-TopProcessesByCurrentCpu {
    try {
        $procs = Get-CimInstance -ClassName Win32_PerfFormattedData_PerfProc_Process -ErrorAction SilentlyContinue
        $procs | Where-Object { $_.Name -and $_.Name -notmatch "^(Idle|_Total|Total)$" -and [int]$_.PercentProcessorTime -gt 0 } |
            Sort-Object { [int]$_.PercentProcessorTime } -Descending | Select-Object -First 5 |
            ForEach-Object {
                $raw = [int]$_.PercentProcessorTime
                $capped = [Math]::Min(100, $raw)
                $obj = @{ name = $_.Name; cpu_pct = $capped }
                if ($raw -gt 100) { $obj.cpu_pct_raw = $raw }
                $obj
            }
    } catch { @() }
}

# GPU via nvidia-smi (same source as Task Manager / build_safety_check). Lightweight; null if no NVIDIA.
function Get-LightGpuMetrics {
    $nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if (-not $nvidia) { return $null }
    try {
        $line = & nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits 2>$null | Select-Object -First 1
        if (-not $line) { return $null }
        $parts = ($line -split ",").Trim()
        $util = [int]($parts[0] -replace "[^0-9]", "")
        $memUsed = [long]($parts[1] -replace "[^0-9]", "")
        $memTotal = [long]($parts[2] -replace "[^0-9]", "")
        $temp = [int]($parts[3] -replace "[^0-9]", "")
        $vramPct = if ($memTotal -gt 0) { [int](($memUsed / $memTotal) * 100) } else { 0 }
        return @{ util_pct = $util; vram_pct = $vramPct; temp_c = $temp; mem_used_mb = [int]($memUsed); mem_total_mb = [int]($memTotal) }
    } catch { return $null }
}

Write-Host "Station health loop started (interval ${IntervalSec}s, history every ${HistoryIntervalSec}s). Stop file: $StopFile" -ForegroundColor Cyan

while ($true) {
    if (Test-Path -LiteralPath $StopFile -PathType Leaf) {
        Write-Host "Stop file detected. Exiting." -ForegroundColor Gray
        Remove-Item -LiteralPath $StopFile -Force -ErrorAction SilentlyContinue
        break
    }

    $cpu = Get-LightCpuPct
    $ram = Get-LightRamPct
    $gpu = Get-LightGpuMetrics
    $top = Get-TopProcesses
    $entropySources = Get-TopProcessesByCurrentCpu

    # Rolling baseline and cadence (entropy)
    if ($null -ne $cpu) {
        $script:cpuHistory += $cpu
        if ($script:cpuHistory.Count -gt 60) { $script:cpuHistory = $script:cpuHistory[-60..-1] }
    }
    $sorted = $script:cpuHistory | Sort-Object
    $n = $sorted.Count
    $baselineCpu = if ($n -gt 0) { [int]$sorted[[Math]::Floor($n / 2)] } else { $null }
    $cadence70 = ($script:cpuHistory | Where-Object { $_ -ge 70 }).Count
    $entropyTier = if ($null -eq $cpu) { "unknown" } elseif ($cpu -ge 70) { "unacceptable" } elseif ($cpu -ge 50) { "high" } else { "pass" }

    $health = "pass"
    if ($null -ne $cpu -and $cpu -ge $FailCpuPct) { $health = "fail" }
    elseif ($null -ne $ram -and $ram -ge $FailRamPct) { $health = "fail" }
    elseif ($gpu) {
        if ($gpu.temp_c -ge $FailGpuTempC -or $gpu.util_pct -ge $FailGpuPct -or $gpu.vram_pct -ge $FailVramPct) { $health = "fail" }
        elseif ($gpu.temp_c -ge $WarnGpuTempC -or $gpu.util_pct -ge $WarnGpuPct -or $gpu.vram_pct -ge $WarnVramPct) { $health = "warn" }
    }
    if ($health -eq "pass") {
        if ($null -ne $cpu -and $cpu -ge $WarnCpuPct) { $health = "warn" }
        elseif ($null -ne $ram -and $ram -ge $WarnRamPct) { $health = "warn" }
    }

    $ts = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    $obj = @{
        health     = $health
        health_ts  = $ts
        cpu_pct    = $cpu
        ram_pct    = $ram
        gpu        = if ($gpu) { @{ util_pct = $gpu.util_pct; vram_pct = $gpu.vram_pct; temp_c = $gpu.temp_c } } else { $null }
        top        = $top
        entropy    = @{
            tier         = $entropyTier
            baseline_cpu = $baselineCpu
            cadence_70   = $cadence70
            entropy_sources = $entropySources
        }
        interval_s = $IntervalSec
    } | ConvertTo-Json -Compress:$false -Depth 4
    [System.IO.File]::WriteAllText($outPath, $obj, [System.Text.UTF8Encoding]::new($false))

    # Append to history every HistoryIntervalSec (compact snapshot for trend analysis)
    $nowUtc = [DateTime]::UtcNow
    $shouldWriteHistory = $false
    if ($null -eq $script:lastHistoryTs) {
        $script:lastHistoryTs = $nowUtc
        $shouldWriteHistory = $true
    } elseif (($nowUtc - $script:lastHistoryTs).TotalSeconds -ge $HistoryIntervalSec) {
        $script:lastHistoryTs = $nowUtc
        $shouldWriteHistory = $true
    }
    if ($shouldWriteHistory) {
        try {
            $snap = @{
                ts = $ts
                health = $health
                cpu_pct = $cpu
                ram_pct = $ram
                entropy_tier = $entropyTier
                cadence_70 = $cadence70
                baseline_cpu = $baselineCpu
            }
            if ($gpu) { $snap.gpu_util_pct = $gpu.util_pct; $snap.gpu_vram_pct = $gpu.vram_pct; $snap.gpu_temp_c = $gpu.temp_c }
            $line = $snap | ConvertTo-Json -Compress
            Add-Content -LiteralPath $historyPath -Value $line -Encoding UTF8
            # Trim if over limit (keep last MaxHistoryLines)
            if (Test-Path -LiteralPath $historyPath -PathType Leaf) {
                $lines = Get-Content -LiteralPath $historyPath -Encoding UTF8
                if ($lines.Count -gt $MaxHistoryLines) {
                    $lines[-$MaxHistoryLines..-1] | Set-Content -LiteralPath $historyPath -Encoding UTF8
                }
            }
        } catch { }
    }

    $sleepSec = [Math]::Max(0, $IntervalSec - 2)
    if ($sleepSec -gt 0) { Start-Sleep -Seconds $sleepSec }
}
