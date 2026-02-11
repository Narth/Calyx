param(
    [Parameter(Mandatory = $true)][string]$OutPath,
    [Parameter(Mandatory = $true)][string]$CorrelationId,
    [Parameter(Mandatory = $true)][string]$ParentCorrelationId,
    [Parameter(Mandatory = $true)][string]$LastSunsetPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ts = (Get-Date).ToUniversalTime().ToString('o')

$batt = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue | Select-Object EstimatedChargeRemaining, BatteryStatus
Add-Type -AssemblyName System.Windows.Forms
$powerStatus = [System.Windows.Forms.SystemInformation]::PowerStatus
$powerLineStatus = $powerStatus.PowerLineStatus.ToString()
$batteryChargeStatus = $powerStatus.BatteryChargeStatus.ToString()
$batteryLifePercent = $powerStatus.BatteryLifePercent

$lastSunset = Get-Content -Path $LastSunsetPath | ConvertFrom-Json
$lastBatteryPercent = $lastSunset.battery.EstimatedChargeRemaining
$lastPowerLineStatus = $lastSunset.power_status.power_line_status

$batteryDeltaPercent = $null
if ($null -ne $lastBatteryPercent -and $null -ne $batt.EstimatedChargeRemaining) {
    $batteryDeltaPercent = $batt.EstimatedChargeRemaining - $lastBatteryPercent
}

$powerSourceChange = $null
if ($null -ne $lastPowerLineStatus -and $null -ne $powerLineStatus) {
    $powerSourceChange = "$lastPowerLineStatus -> $powerLineStatus"
}

$sunrise = [ordered]@{
    phase = 'sunrise'
    timestamp_utc = $ts
    correlation_id = $CorrelationId
    parent_correlation_id = $ParentCorrelationId
    power_status = [ordered]@{
        power_line_status = $powerLineStatus
        battery_charge_status = $batteryChargeStatus
        battery_life_percent = $batteryLifePercent
    }
    battery = $batt
    last_sunset = [ordered]@{
        path = $LastSunsetPath
        sha256 = (Get-FileHash -Algorithm SHA256 -Path $LastSunsetPath).Hash
    }
    continuity_assessment = [ordered]@{
        battery_delta_percent = $batteryDeltaPercent
        power_source_change = $powerSourceChange
        anomalies = @()
    }
    evidence_commands = @(
        'Get-CimInstance Win32_Battery | Select EstimatedChargeRemaining,BatteryStatus',
        '[System.Windows.Forms.SystemInformation]::PowerStatus'
    )
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutPath) | Out-Null
$sunrise | ConvertTo-Json -Depth 6 | Set-Content -Path $OutPath -Encoding UTF8

Write-Output "WROTE=$OutPath"
