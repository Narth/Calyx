param(
    [Parameter(Mandatory = $true)][string]$OutPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ts = (Get-Date).ToUniversalTime().ToString('o')

# Load policy
$policyPath = "governance/policies/energy_viability_policy.json"
if (-not (Test-Path $policyPath)) {
    Write-Error "Policy file not found: $policyPath"
    exit 1
}
$policy = Get-Content -Path $policyPath | ConvertFrom-Json

# Read latest sunset and sunrise
$sunsetPath = Get-ChildItem -Path "telemetry/sun_cycle/sunsets" -Filter "sunset_*.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
if (-not $sunsetPath) {
    Write-Error "No sunset record found. Cannot evaluate boot guard."
    exit 1
}
$sunset = Get-Content -Path $sunsetPath | ConvertFrom-Json

$sunrisePath = Get-ChildItem -Path "telemetry/sun_cycle/sunrises" -Filter "sunrise_*.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
$sunrise = $null
if ($sunrisePath) {
    $sunrise = Get-Content -Path $sunrisePath | ConvertFrom-Json
}

# Evaluate energy viability gate
$energyViabilityGate = $true
$reasons = @()

if ($policy.ac_required -and $sunset.power_status.power_line_status -ne 'Online') {
    $energyViabilityGate = $false
    $reasons += "AC power is required but not available."
}

# Update policy references to match new field names
if ($sunset.battery.EstimatedChargeRemaining -le $policy.sunset_threshold_percent) {
    $energyViabilityGate = $false
    $reasons += "Battery percent below sunset threshold ($($policy.sunset_threshold_percent)%)."
}

if ($sunset.battery.EstimatedChargeRemaining -lt $policy.sunrise_min_battery_percent) {
    $energyViabilityGate = $false
    $reasons += "Battery percent below sunrise minimum threshold ($($policy.sunrise_min_battery_percent)%)."
}

if (-not $energyViabilityGate) {
    Write-Host "FAIL: Energy viability gate not passed." -ForegroundColor Red
    Write-Host "Reasons: $($reasons -join ', ')" -ForegroundColor Yellow
} else {
    Write-Host "PASS: Energy viability gate passed." -ForegroundColor Green
}

# Write report
$report = [ordered]@{
    phase = 'bloomos_boot_guard'
    timestamp_utc = $ts
    energy_viability_gate = if ($energyViabilityGate) { 'pass' } else { 'fail' }
    reasons = $reasons
    last_sunset = [ordered]@{
        path = $sunsetPath
        sha256 = (Get-FileHash -Algorithm SHA256 -Path $sunsetPath).Hash
    }
    last_sunrise = if ($sunrise) {
        [ordered]@{
            path = $sunrisePath
            sha256 = (Get-FileHash -Algorithm SHA256 -Path $sunrisePath).Hash
        }
    } else {
        $null
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutPath) | Out-Null
$report | ConvertTo-Json -Depth 6 | Set-Content -Path $OutPath -Encoding UTF8

Write-Output "WROTE=$OutPath"
