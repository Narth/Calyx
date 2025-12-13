param(
    [string]$TaskName = "Calyx Nightly Sanitizer"
)

$ErrorActionPreference = 'Stop'

try {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false | Out-Null
        Write-Host "Scheduled task '$TaskName' unregistered." -ForegroundColor Yellow
    }
    else {
        Write-Host "Scheduled task '$TaskName' not found." -ForegroundColor DarkYellow
    }
}
catch {
    Write-Error $_
    exit 1
}
