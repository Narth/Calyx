param(
    [Parameter(Mandatory = $true)][string]$OutPath,
    [Parameter(Mandatory = $true)][string]$CorrelationId,
    [Parameter(Mandatory = $true)][string]$PhaseMarker
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ts = (Get-Date).ToUniversalTime().ToString('o')

$batt = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue | Select-Object EstimatedChargeRemaining, BatteryStatus, Status
$os = Get-CimInstance Win32_OperatingSystem | Select-Object LastBootUpTime
$cpu = (Get-Counter '\Processor(_Total)\% Processor Time').CounterSamples[0].CookedValue

Add-Type -AssemblyName System.Windows.Forms
$powerStatus = [System.Windows.Forms.SystemInformation]::PowerStatus
$powerLineStatus = $powerStatus.PowerLineStatus.ToString()
$batteryChargeStatus = $powerStatus.BatteryChargeStatus.ToString()
$batteryLifePercent = $powerStatus.BatteryLifePercent
$batteryLifeRemaining = $powerStatus.BatteryLifeRemaining

$snapshot = [ordered]@{
    phase = 'energy_telemetry_phase_e3'
    marker = $PhaseMarker
    timestamp_utc = $ts
    correlation_id = $CorrelationId
    power_status = [ordered]@{
        power_line_status = $powerLineStatus
        battery_charge_status = $batteryChargeStatus
        battery_life_percent = $batteryLifePercent
        battery_life_remaining = $batteryLifeRemaining
    }
    battery = $batt
    cpu_percent = [math]::Round($cpu, 2)
    uptime_last_boot_utc = $os.LastBootUpTime
    evidence_commands = @(
        'Get-CimInstance Win32_Battery | Select EstimatedChargeRemaining,BatteryStatus,Status',
        'Get-CimInstance Win32_OperatingSystem | Select LastBootUpTime',
        "Get-Counter '\\Processor(_Total)\\% Processor Time'",
        '[System.Windows.Forms.SystemInformation]::PowerStatus'
    )
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutPath) | Out-Null
$snapshot | ConvertTo-Json -Depth 6 | Set-Content -Path $OutPath -Encoding UTF8

Write-Output "WROTE=$OutPath"
