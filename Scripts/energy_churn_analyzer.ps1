# Energy Churn Analyzer — reads station health history, detects patterns, writes report.
# Usage: .\Scripts\energy_churn_analyzer.ps1 [-HistorySamples 60] [-NotifyDiscord]
# Writes: runtime/deployment/energy_churn_report.json, runtime/deployment/energy_churn_report.txt
# Env: DISCORD_CHURN_WEBHOOK_URL (optional, for -NotifyDiscord)
# See: docs/planning/ENERGY_CHURN_ANALYSIS_PLAN.md

param(
    [int]$HistorySamples = 60,
    [switch]$NotifyDiscord = $false
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) { $repoRoot = (Get-Location).Path }

$runtimeDir = Join-Path $repoRoot "runtime"
$deployDir = Join-Path $runtimeDir "deployment"
$historyPath = Join-Path $runtimeDir "station_health_history.jsonl"
$healthPath = Join-Path $runtimeDir "station_health.json"
$reportJsonPath = Join-Path $deployDir "energy_churn_report.json"
$reportTxtPath = Join-Path $deployDir "energy_churn_report.txt"

if (-not (Test-Path $deployDir)) { New-Item -ItemType Directory -Path $deployDir -Force | Out-Null }

# Load .env.cbo for DISCORD_CHURN_WEBHOOK_URL
$envFile = Join-Path $repoRoot ".env.cbo"
if (Test-Path -LiteralPath $envFile -PathType Leaf) {
    Get-Content $envFile -Encoding UTF8 | ForEach-Object {
        if ($_ -match '^\s*DISCORD_CHURN_WEBHOOK_URL\s*=\s*(.+)$') {
            $env:DISCORD_CHURN_WEBHOOK_URL = $matches[1].Trim().Trim('"').Trim("'")
        }
    }
}

$samples = @()
if (Test-Path -LiteralPath $historyPath -PathType Leaf) {
    $lines = Get-Content -LiteralPath $historyPath -Encoding UTF8
    $take = [Math]::Min($HistorySamples, $lines.Count)
    if ($take -gt 0) {
        $samples = $lines[-$take..-1] | ForEach-Object {
            try { $_ | ConvertFrom-Json } catch { $null }
        } | Where-Object { $null -ne $_ }
    }
}

$currentHealth = $null
if (Test-Path -LiteralPath $healthPath -PathType Leaf) {
    try {
        $currentHealth = Get-Content -LiteralPath $healthPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch { }
}

# --- Pattern detection ---
$patterns = @()
$avgCpu = 0
$maxCadence70 = 0
$avgBaseline = 0
$unacceptableCount = 0
$restOpportunityCount = 0
$thermalHeadroom = $false
$cooldownNeeded = $false

if ($samples.Count -gt 0) {
    $cpuSum = 0
    $baselineSum = 0
    foreach ($s in $samples) {
        if ($null -ne $s.cpu_pct) { $cpuSum += $s.cpu_pct }
        if ($null -ne $s.baseline_cpu) { $baselineSum += $s.baseline_cpu }
        if ($null -ne $s.cadence_70 -and $s.cadence_70 -gt $maxCadence70) { $maxCadence70 = $s.cadence_70 }
        if ($s.entropy_tier -eq "unacceptable") { $unacceptableCount++ }
        $base = if ($null -ne $s.baseline_cpu) { $s.baseline_cpu } else { 0 }
        if ($null -ne $s.cpu_pct -and $s.cpu_pct -lt $base + 10) { $restOpportunityCount++ }
    }
    $avgCpu = if ($samples.Count -gt 0) { [Math]::Round($cpuSum / $samples.Count, 1) } else { 0 }
    $avgBaseline = if ($samples.Count -gt 0) { [Math]::Round($baselineSum / $samples.Count, 1) } else { 0 }

    # Sustained high entropy: cadence_70 > 10 for 5+ consecutive
    $consecutiveHigh = 0
    foreach ($s in $samples) {
        $c70 = if ($null -ne $s.cadence_70) { $s.cadence_70 } else { 0 }
        if ($c70 -gt 10) {
            $consecutiveHigh++
        } else {
            $consecutiveHigh = 0
        }
        if ($consecutiveHigh -ge 5) {
            $patterns += @{ id = "sustained_high"; message = "Repeatedly maxing; cooldown recommended"; severity = "high" }
            break
        }
    }

    # Baseline drift: compare first third to last third
    $n = $samples.Count
    if ($n -ge 6) {
        $firstThird = $samples[0..([Math]::Max(0, [Math]::Floor($n / 3) - 1))]
        $lastThird = $samples[([Math]::Max(0, $n - [Math]::Floor($n / 3)))..($n - 1)]
        $avgFirst = ($firstThird | ForEach-Object { $_.baseline_cpu } | Where-Object { $null -ne $_ } | Measure-Object -Average).Average
        $avgLast = ($lastThird | ForEach-Object { $_.baseline_cpu } | Where-Object { $null -ne $_ } | Measure-Object -Average).Average
        if ($null -ne $avgFirst -and $null -ne $avgLast -and $avgLast -gt $avgFirst + 15) {
            $patterns += @{ id = "baseline_drift"; message = "Idle load creeping up; investigate entropy_sources"; severity = "medium" }
        }
    }

    # Spike clusters: cpu_pct jumps 30+ then drops (simplified: variance)
    $cpuValues = $samples | ForEach-Object { $_.cpu_pct } | Where-Object { $null -ne $_ }
    if ($cpuValues.Count -ge 5) {
        $avg = ($cpuValues | Measure-Object -Average).Average
        $variance = ($cpuValues | ForEach-Object { ($_ - $avg) * ($_ - $avg) } | Measure-Object -Sum).Sum / $cpuValues.Count
        if ($variance -gt 400) {  # std dev ~20
            $patterns += @{ id = "spike_clusters"; message = "Periodic spikes; possible polling or scheduled task"; severity = "medium" }
        }
    }

    # Life signals
    $lastSample = $samples[-1]
    $gpuTemp = if ($null -ne $lastSample.gpu_temp_c) { $lastSample.gpu_temp_c } else { 0 }
    $thermalHeadroom = $gpuTemp -lt 70
    $cooldownNeeded = $maxCadence70 -gt 10 -or $unacceptableCount -gt ($samples.Count / 2)
    if ($restOpportunityCount -ge 5) {
        $patterns += @{ id = "rest_opportunity"; message = "Machine can cool; rest opportunity"; severity = "info" }
    }
    if ($cooldownNeeded) {
        $patterns += @{ id = "cooldown_needed"; message = "Cadence high or entropy unacceptable; defer heavy work"; severity = "high" }
    }
}

# Current entropy_sources (from station_health.json)
$entropySources = @()
if ($currentHealth -and $currentHealth.entropy -and $currentHealth.entropy.entropy_sources) {
    $entropySources = $currentHealth.entropy.entropy_sources | ForEach-Object {
        @{ name = $_.name; cpu_pct = $_.cpu_pct; cpu_pct_raw = $_.cpu_pct_raw }
    }
}

# Build report
$ts = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
$report = @{
    ts_utc = $ts
    tool = "energy_churn_analyzer"
    samples_analyzed = $samples.Count
    metrics = @{
        avg_cpu_pct = $avgCpu
        max_cadence_70 = $maxCadence70
        avg_baseline_cpu = $avgBaseline
        unacceptable_count = $unacceptableCount
        rest_opportunity_count = $restOpportunityCount
        thermal_headroom = $thermalHeadroom
        cooldown_needed = $cooldownNeeded
    }
    patterns = $patterns
    entropy_sources_now = $entropySources
    summary = ""
}

# Human-readable summary
$summaryLines = @()
$summaryLines += "Energy Churn Report - $ts"
$summaryLines += "Samples: $($samples.Count) | Avg CPU: $avgCpu% | Max cadence_70: $maxCadence70"
$summaryLines += "Thermal headroom: $thermalHeadroom | Cooldown needed: $cooldownNeeded"
if ($patterns.Count -gt 0) {
    $summaryLines += ""
    $summaryLines += "Patterns:"
    foreach ($p in $patterns) {
        $summaryLines += "  [$($p.severity)] $($p.message)"
    }
}
if ($entropySources.Count -gt 0) {
    $summaryLines += ""
    $summaryLines += "Current entropy sources:"
    foreach ($e in $entropySources) {
        $raw = if ($e.cpu_pct_raw) { " (raw $($e.cpu_pct_raw))" } else { "" }
        $summaryLines += "  $($e.name): $($e.cpu_pct)%$raw"
    }
}
$report.summary = $summaryLines -join "`n"

# Write outputs
$reportJson = $report | ConvertTo-Json -Depth 5 -Compress:$false
[System.IO.File]::WriteAllText($reportJsonPath, $reportJson, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText($reportTxtPath, $report.summary, [System.Text.UTF8Encoding]::new($false))

Write-Host $report.summary -ForegroundColor Cyan

# Optional Discord notification
if ($NotifyDiscord) {
    $webhookUrl = $env:DISCORD_CHURN_WEBHOOK_URL
    if (-not $webhookUrl -or $webhookUrl.Length -lt 20) {
        Write-Host "DISCORD_CHURN_WEBHOOK_URL not set; skipping Discord notification." -ForegroundColor Yellow
    } else {
        try {
            $payload = @{
                content = "**Energy churn analysis build ready for testing.**`nRun ``Scripts\energy_churn_analyzer.ps1`` or see runtime/deployment/energy_churn_report.json"
            } | ConvertTo-Json
            Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $payload -ContentType "application/json" -TimeoutSec 10
            Write-Host "Discord notification sent." -ForegroundColor Green
        } catch {
            Write-Host "Discord notification failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

exit 0
