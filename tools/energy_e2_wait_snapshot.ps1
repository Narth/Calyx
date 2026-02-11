param(
    [Parameter(Mandatory = $true)][string]$OutPath,
    [Parameter(Mandatory = $true)][string]$CorrelationId
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ts = (Get-Date).ToUniversalTime().ToString('o')

Add-Type -AssemblyName System.Windows.Forms
$powerStatus = [System.Windows.Forms.SystemInformation]::PowerStatus
$powerLineStatus = $powerStatus.PowerLineStatus.ToString()
$batteryChargeStatus = $powerStatus.BatteryChargeStatus.ToString()
$batteryLifePercent = $powerStatus.BatteryLifePercent

$snapshot = [ordered]@{
    phase = 'energy_telemetry_phase_e2_wait'
    timestamp_utc = $ts
    correlation_id = $CorrelationId
    power_status = [ordered]@{
        power_line_status = $powerLineStatus
        battery_charge_status = $batteryChargeStatus
        battery_life_percent = $batteryLifePercent
    }
    reason = 'ac_power_unavailable_or_unstable'
    statement = "Charge-window telemetry deferred due to unavailable or unsafe AC power. No actions taken."
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutPath) | Out-Null
$snapshot | ConvertTo-Json -Depth 6 | Set-Content -Path $OutPath -Encoding UTF8

Write-Output "WROTE=$OutPath"
