param(
    [Parameter(Mandatory = $true)][string]$OutPath,
    [Parameter(Mandatory = $true)][string]$CorrelationId,
    [Parameter(Mandatory = $true)][string]$ParentCorrelationId,
    [Parameter(Mandatory = $true)][string]$PhaseMarker
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ts = (Get-Date).ToUniversalTime().ToString('o')

$batt = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue | Select-Object EstimatedChargeRemaining, BatteryStatus
$os = Get-CimInstance Win32_OperatingSystem | Select-Object LastBootUpTime
$cpu = (Get-Counter '\Processor(_Total)\% Processor Time').CounterSamples[0].CookedValue
$adapters = Get-NetAdapter | Select-Object Name, Status, InterfaceDescription

$powerSource = $null
$batteryPercent = $null
$estimatedRuntime = $null
$batteryHealth = $null

if ($batt) {
    $batteryPercent = $batt.EstimatedChargeRemaining
    # BatteryStatus is not a definitive AC/Battery indicator; include as evidence.
    $batteryHealth = [ordered]@{ BatteryStatus = $batt.BatteryStatus }
}

$snapshot = [ordered]@{
    phase = 'energy_telemetry_phase_e1'
    marker = $PhaseMarker
    timestamp_utc = $ts
    correlation_id = $CorrelationId
    parent_correlation_id = $ParentCorrelationId
    power_source = $powerSource
    battery_percent = $batteryPercent
    estimated_runtime = $estimatedRuntime
    cpu_percent = [math]::Round($cpu, 2)
    uptime_last_boot_utc = $os.LastBootUpTime
    network_context = @($adapters | ForEach-Object {
        [ordered]@{ Name = $_.Name; Status = "$($_.Status)"; InterfaceDescription = $_.InterfaceDescription }
    })
    evidence_commands = @(
        'Get-CimInstance Win32_Battery | Select EstimatedChargeRemaining,BatteryStatus',
        'Get-CimInstance Win32_OperatingSystem | Select LastBootUpTime',
        "Get-Counter '\\Processor(_Total)\\% Processor Time'",
        'Get-NetAdapter | Select Name,Status,InterfaceDescription'
    )
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutPath) | Out-Null
$snapshot | ConvertTo-Json -Depth 6 | Set-Content -Path $OutPath -Encoding UTF8

Write-Output "WROTE=$OutPath"
