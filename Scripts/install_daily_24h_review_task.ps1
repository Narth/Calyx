param(
    [string]$ReviewTaskName = "Calyx Daily 24H Review",
    [string]$SunriseTaskName = "Calyx Daily Governed Sunrise",
    [switch]$InstallSunriseTask = $true
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
Set-Location $repoRoot

$cycleScript = Join-Path $repoRoot "Scripts\run_daily_24h_review_cycle.ps1"
$sunriseScript = Join-Path $repoRoot "Scripts\sunrise_calyx.ps1"

$reviewLocalTime = [datetime]::Today.AddHours(17).AddMinutes(0).AddSeconds(30)
$sunriseLocalTime = [datetime]::Today.AddHours(16).AddMinutes(57).AddSeconds(0)
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
$reviewAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$cycleScript`" -SkipSunrise"
$reviewTrigger = New-ScheduledTaskTrigger -Daily -At $reviewLocalTime
$reviewPrincipal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $ReviewTaskName -Action $reviewAction -Trigger $reviewTrigger -Settings $settings -Principal $reviewPrincipal -Force | Out-Null

if ($InstallSunriseTask) {
    $sunriseAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$sunriseScript`""
    $sunriseTrigger = New-ScheduledTaskTrigger -Daily -At $sunriseLocalTime
    $sunrisePrincipal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $SunriseTaskName -Action $sunriseAction -Trigger $sunriseTrigger -Settings $settings -Principal $sunrisePrincipal -Force | Out-Null
}

$receiptDir = Join-Path $repoRoot "runtime\receipts\audit"
$receiptPath = Join-Path $receiptDir ("daily_24h_review_schedule__{0}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
if (-not (Test-Path $receiptDir)) {
    New-Item -ItemType Directory -Path $receiptDir -Force | Out-Null
}

$receipt = [ordered]@{
    schema = "station.daily_24h_review.schedule.v1"
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    review_task = @{
        task_name = $ReviewTaskName
        local_time = $reviewLocalTime.ToString("HH:mm:ss")
        utc_target = "00:00:30"
        script = "Scripts\\run_daily_24h_review_cycle.ps1 -SkipSunrise"
    }
    sunrise_task = @{
        installed = [bool]$InstallSunriseTask
        task_name = $SunriseTaskName
        local_time = $sunriseLocalTime.ToString("HH:mm:ss")
        utc_target = "23:57:00"
        script = "Scripts\\sunrise_calyx.ps1"
    }
    timezone = (Get-TimeZone).Id
    notes = @(
        "Daily review remains an audit-class memory artifact, not a live authority surface.",
        "Separate sunrise scheduling provides a post-sunrise buffer before the 00:00:30 UTC review target."
    )
}
$receipt | ConvertTo-Json -Depth 6 | Set-Content -Path $receiptPath -Encoding UTF8
Write-Host $receiptPath
