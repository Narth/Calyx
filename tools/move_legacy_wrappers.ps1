# Move legacy wrapper files (non-Calyx* _wrapper.bat) into a timestamped backup directory
$tools = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupDir = Join-Path $tools ("wrapper_backups_$ts")
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$legacy = Get-ChildItem -Path (Join-Path $tools "*_wrapper.bat") -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike 'Calyx*' }
if (-not $legacy -or $legacy.Count -eq 0) {
    Write-Host 'No legacy wrappers found to move.'
    Write-Host "Backup directory: $backupDir"
    exit 0
}
foreach ($f in $legacy) {
    $dest = Join-Path $backupDir $f.Name
    Move-Item -Path $f.FullName -Destination $dest -Force
    Write-Host "Moved: $($f.Name) -> $dest"
}
Write-Host "Backup directory: $backupDir"
