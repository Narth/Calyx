param(
    [Parameter(Mandatory = $true)][string]$OutPath,
    [Parameter(Mandatory = $true)][string]$CorrelationId,
    [Parameter(Mandatory = $true)][string]$ParentCorrelationId,
    [Parameter(Mandatory = $true)][string]$Reason,
    [string]$NextIntendedPhase,
    [string]$OperatorNote
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

$sunset = [ordered]@{
    phase = 'sunset'
    timestamp_utc = $ts
    correlation_id = $CorrelationId
    parent_correlation_id = $ParentCorrelationId
    power_status = [ordered]@{
        power_line_status = $powerLineStatus
        battery_charge_status = $batteryChargeStatus
        battery_life_percent = $batteryLifePercent
    }
    battery = $batt
    reason = $Reason
    next_intended_phase = $NextIntendedPhase
    operator_note = $OperatorNote
    evidence_commands = @(
        'Get-CimInstance Win32_Battery | Select EstimatedChargeRemaining,BatteryStatus',
        '[System.Windows.Forms.SystemInformation]::PowerStatus'
    )
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutPath) | Out-Null
$sunset | ConvertTo-Json -Depth 6 | Set-Content -Path $OutPath -Encoding UTF8

Write-Output "WROTE=$OutPath"
