# Carbon Intensity — Electricity Maps API integration.
# Fetches real-time carbon intensity (gCO2eq/kWh) for load-shifting decisions.
# Usage: .\Scripts\carbon_intensity.ps1 [-Zone US-SW-AZPS]
# Writes: runtime/carbon_intensity.json
# Env: ELECTRICITY_MAPS_API_KEY (required). Get key at https://app.electricitymaps.com/settings/api-access
# See: docs/operations/CARBON_INTENSITY_INTEGRATION.md

param(
    [string]$Zone = $env:CARBON_INTENSITY_ZONE
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path "$repoRoot\cbo_hub")) {
    $repoRoot = (Get-Location).Path
}

# Load .env.cbo if present (PowerShell doesn't inherit Python's load_dotenv)
$envFile = Join-Path $repoRoot ".env.cbo"
if (Test-Path -LiteralPath $envFile -PathType Leaf) {
    Get-Content $envFile -Encoding UTF8 | ForEach-Object {
        if ($_ -match '^\s*ELECTRICITY_MAPS_API_KEY\s*=\s*(.+)$') {
            $env:ELECTRICITY_MAPS_API_KEY = $matches[1].Trim().Trim('"').Trim("'")
        }
        if ($_ -match '^\s*CARBON_INTENSITY_ZONE\s*=\s*(.+)$') {
            $env:CARBON_INTENSITY_ZONE = $matches[1].Trim().Trim('"').Trim("'")
        }
    }
}

if (-not $Zone) { $Zone = $env:CARBON_INTENSITY_ZONE }
if (-not $Zone) { $Zone = "US" }

$runtimeDir = Join-Path $repoRoot "runtime"
$outPath = Join-Path $runtimeDir "carbon_intensity.json"
if (-not (Test-Path $runtimeDir)) { New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null }

$apiKey = $env:ELECTRICITY_MAPS_API_KEY
if (-not $apiKey) {
    $apiKey = [System.Environment]::GetEnvironmentVariable("ELECTRICITY_MAPS_API_KEY", "User")
}
if (-not $apiKey -or $apiKey.Length -lt 10) {
    $obj = @{
        carbon_intensity_g_co2eq_per_kwh = $null
        zone = $Zone
        status = "no_api_key"
        ts = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
        recommendation = "Set ELECTRICITY_MAPS_API_KEY. Get key at https://app.electricitymaps.com/settings/api-access"
    } | ConvertTo-Json
    [System.IO.File]::WriteAllText($outPath, $obj, [System.Text.UTF8Encoding]::new($false))
    Write-Host "CarbonIntensity> no_api_key (set ELECTRICITY_MAPS_API_KEY)" -ForegroundColor Yellow
    exit 0
}

$uri = "https://api.electricitymaps.com/v3/carbon-intensity/latest?zone=$Zone"
try {
    $headers = @{ "auth-token" = $apiKey }
    $r = Invoke-RestMethod -Uri $uri -Headers $headers -Method Get -TimeoutSec 10
    $carbon = $r.carbonIntensity
    $zoneName = $r.zone
    $datetime = $r.datetime
    $obj = @{
        carbon_intensity_g_co2eq_per_kwh = $carbon
        zone = $zoneName
        datetime = $datetime
        status = "ok"
        ts = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
        power_window = "clean"
    }
    if ($carbon -le 200) { $obj.power_window = "clean" }
    elseif ($carbon -le 400) { $obj.power_window = "mixed" }
    else { $obj.power_window = "dirty" }
    $json = $obj | ConvertTo-Json
    [System.IO.File]::WriteAllText($outPath, $json, [System.Text.UTF8Encoding]::new($false))
    Write-Host "CarbonIntensity> $carbon gCO2eq/kWh ($($obj.power_window)) zone=$zoneName" -ForegroundColor Green
    exit 0
} catch {
    $obj = @{
        carbon_intensity_g_co2eq_per_kwh = $null
        zone = $Zone
        status = "error"
        error = $_.Exception.Message.Substring(0, [Math]::Min(200, $_.Exception.Message.Length))
        ts = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
        recommendation = "Check API key and zone. Retry later."
    } | ConvertTo-Json
    [System.IO.File]::WriteAllText($outPath, $obj, [System.Text.UTF8Encoding]::new($false))
    Write-Host "CarbonIntensity> error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
