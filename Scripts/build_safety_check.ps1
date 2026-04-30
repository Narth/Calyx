# Build Safety Check — hardware, safety, utility, efficiency.
# Run before/during crucial builds so we don't over-excite, burn out, or fry hardware,
# and avoid crash loops and long boot waits.
# Usage: .\Scripts\build_safety_check.ps1 [-RequireCoreServices]
# Exit: 0 = pass, 1 = warn (proceed with caution), 2 = fail (do not add load).
# See: docs/planning/BUILD_SAFETY_CHECK.md

param(
    [switch]$RequireCoreServices = $false
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) {
    $repoRoot = (Get-Location).Path
}

# Thresholds (match BUILD_SAFETY_CHECK.md)
$script:WarnCpuPct = 75
$script:FailCpuPct = 92
$script:WarnRamPct = 80
$script:FailRamPct = 92
$script:WarnGpuTempC = 80
$script:FailGpuTempC = 90
$script:WarnVramPct = 85

$script:Warnings = @()
$script:Failures = @()

function Write-Status { param($Name, $Value, $Ok) Write-Host "  $Name : $Value" $(if ($Ok) { "[OK]" } else { "[!]" }) }
function Add-Warn { param($Msg) $script:Warnings += $Msg }
function Add-Fail { param($Msg) $script:Failures += $Msg }

# --- CPU ---
function Get-CpuUsagePct {
    try {
        $c = Get-Counter -Counter "\Processor(_Total)\% Processor Time" -SampleInterval 1 -MaxSamples 2 -ErrorAction SilentlyContinue
        if ($c -and $c.CounterSamples) {
            [int][Math]::Round($c.CounterSamples.CookedValue)
        } else { $null }
    } catch { $null }
}

# --- RAM ---
function Get-RamUsagePct {
    try {
        $os = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction SilentlyContinue
        if ($os) {
            $total = $os.TotalVisibleMemorySize
            $free = $os.FreePhysicalMemory
            if ($total -gt 0) { [int][Math]::Round((1 - $free / $total) * 100) } else { $null }
        } else { $null }
    } catch { $null }
}

# --- GPU (nvidia-smi) ---
function Get-GpuMetrics {
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
        return @{ Utilization = $util; VramPct = $vramPct; TempC = $temp; MemUsedMB = [int]($memUsed); MemTotalMB = [int]($memTotal) }
    } catch { return $null }
}

# --- Ollama in use (safety) ---
function Test-OllamaInUse {
    try {
        $out = & ollama ps 2>$null
        if (-not $out) { return $false }
        # "NAME ID SIZE ..." header + at least one model line
        $lines = ($out | Where-Object { $_ -match "\S" })
        return $lines.Count -gt 1
    } catch { return $false }
}

# --- Core services (utility) ---
function Get-CoreServicesStatus {
    $checkScript = Join-Path $repoRoot "Scripts\check_calyx_core_services.ps1"
    if (-not (Test-Path $checkScript)) { return $null }
    try {
        $output = & $checkScript 2>&1 | Select-Object -First 1
        $allOk = $LASTEXITCODE -eq 0
        return @{ Line = ($output -replace "^\s+|\s+$", ""); AllOk = $allOk }
    } catch { return @{ Line = "error"; AllOk = $false } }
}

# --- Main ---
Write-Host "Build Safety Check (hardware, safety, utility, efficiency)" -ForegroundColor Cyan
Write-Host ""

# CPU
$cpu = Get-CpuUsagePct
if ($null -ne $cpu) {
    if ($cpu -ge $FailCpuPct) { Add-Fail ("CPU utilization " + $cpu + "% (>= " + $FailCpuPct + "%, do not add load)") }
    elseif ($cpu -ge $WarnCpuPct) { Add-Warn ("CPU utilization " + $cpu + "% (>= " + $WarnCpuPct + "%)") }
    Write-Host "  CPU utilization : ${cpu}%"
} else {
    Write-Host "  CPU utilization : (unable to sample)"
}

# RAM
$ram = Get-RamUsagePct
if ($null -ne $ram) {
    if ($ram -ge $FailRamPct) { Add-Fail ("RAM utilization " + $ram + "% (>= " + $FailRamPct + "%)") }
    elseif ($ram -ge $WarnRamPct) { Add-Warn ("RAM utilization " + $ram + "% (>= " + $WarnRamPct + "%)") }
    Write-Host "  RAM utilization : ${ram}%"
} else {
    Write-Host "  RAM utilization : (unable to read)"
}

# GPU
$gpu = Get-GpuMetrics
if ($gpu) {
    Write-Host "  GPU utilization : $($gpu.Utilization)%"
    Write-Host "  GPU VRAM        : $($gpu.VramPct)% ($($gpu.MemUsedMB) / $($gpu.MemTotalMB) MiB)"
    Write-Host "  GPU temperature : $($gpu.TempC) C"
    if ($gpu.TempC -ge $FailGpuTempC) { Add-Fail ("GPU temperature " + $gpu.TempC + "C >= " + $FailGpuTempC + "C") }
    elseif ($gpu.TempC -ge $WarnGpuTempC) { Add-Warn ("GPU temperature " + $gpu.TempC + "C >= " + $WarnGpuTempC + "C") }
    if ($gpu.VramPct -ge $WarnVramPct) { Add-Warn ("GPU VRAM " + $gpu.VramPct + "% >= " + $WarnVramPct + "%") }
} else {
    Write-Host "  GPU             : (nvidia-smi not available or no GPU)"
}

# Safety: Ollama in use
$ollamaInUse = Test-OllamaInUse
if ($ollamaInUse) {
    Add-Warn 'Ollama has a model loaded; avoid starting another heavy LLM run'
    Write-Host '  Ollama          : model in use (do not stack heavy runs)'
} else {
    Write-Host "  Ollama          : no model in use"
}

# Utility: Core services
$core = Get-CoreServicesStatus
if ($core) {
    Write-Host "  Core services   : $($core.Line)"
    if ($RequireCoreServices -and -not $core.AllOk) {
        Add-Fail 'Core services required but one or more failed. Run start_calyx_core_services.ps1 -StopFirst.'
    }
} else {
    Write-Host "  Core services   : (check script not found)"
    if ($RequireCoreServices) { Add-Fail 'Core services required but check script missing' }
}

# Utility: STATE.md
$statePath = Join-Path $repoRoot "STATE.md"
if (-not (Test-Path $statePath)) {
    if ($RequireCoreServices) { Add-Fail 'STATE.md missing' }
    Write-Host "  STATE.md        : missing"
} else {
    Write-Host "  STATE.md        : present"
}

# Summary
Write-Host ""
if ($script:Failures.Count -gt 0) {
    foreach ($f in $script:Failures) { Write-Host "FAIL: $f" -ForegroundColor Red }
    foreach ($w in $script:Warnings) { Write-Host "WARN: $w" -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "Result: FAIL - do not add load. Resolve cooling, memory, or services; then re-run." -ForegroundColor Red
    exit 2
}
if ($script:Warnings.Count -gt 0) {
    foreach ($w in $script:Warnings) { Write-Host "WARN: $w" -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "Result: WARN - proceed with caution; avoid stacking heavy LLM runs." -ForegroundColor Yellow
    exit 1
}
Write-Host "Result: PASS - safe to proceed with normal build load." -ForegroundColor Green
exit 0
