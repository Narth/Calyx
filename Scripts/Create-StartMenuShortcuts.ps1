<#
Creates Start Menu shortcuts for:
 - Calyx Terminal (runs Scripts\Calyx-Launch.bat)
 - Calyx Agent Watcher (runs Scripts\Launch-Agent-Watcher.bat)

Usage (PowerShell):
  powershell -NoProfile -ExecutionPolicy Bypass -File .\Scripts\Create-StartMenuShortcuts.ps1
#>

$ErrorActionPreference = 'Stop'

function New-Shortcut {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$TargetPath,
        [string]$Arguments,
        [string]$WorkingDirectory,
        [string]$IconLocation
    )
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($Path)
    $shortcut.TargetPath = $TargetPath
    if ($Arguments) { $shortcut.Arguments = $Arguments }
    if ($WorkingDirectory) { $shortcut.WorkingDirectory = $WorkingDirectory }
    if ($IconLocation) { $shortcut.IconLocation = $IconLocation }
    $shortcut.Save()
}

$root = "C:\Calyx_Terminal"
$scripts = Join-Path $root 'Scripts'
$startPrograms = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$calyxFolder = Join-Path $startPrograms 'Calyx'

if (-not (Test-Path $calyxFolder)) { New-Item -ItemType Directory -Path $calyxFolder | Out-Null }

# Calyx Terminal shortcut
$terminalBat = Join-Path $scripts 'Calyx-Launch.bat'
if (-not (Test-Path $terminalBat)) {
    throw "Missing $terminalBat. Please ensure the repository is at $root."
}
$terminalLnk = Join-Path $calyxFolder 'Calyx Terminal.lnk'
New-Shortcut -Path $terminalLnk -TargetPath $terminalBat -WorkingDirectory $root -IconLocation "$env:SystemRoot\System32\shell32.dll,167"

# Calyx Agent Watcher shortcut
$watcherBat = Join-Path $scripts 'Launch-Agent-Watcher.bat'
if (-not (Test-Path $watcherBat)) {
    throw "Missing $watcherBat. Please ensure Launch-Agent-Watcher.bat exists."
}
$watcherLnk = Join-Path $calyxFolder 'Calyx Agent Watcher.lnk'
New-Shortcut -Path $watcherLnk -TargetPath $watcherBat -WorkingDirectory $root -IconLocation "$env:SystemRoot\System32\shell32.dll,220"

# Calyx Agent Launcher shortcut (all-in-one control panel)
$launcherBat = Join-Path $scripts 'Launch-Agent-Launcher.bat'
if (-not (Test-Path $launcherBat)) {
    throw "Missing $launcherBat. Please ensure Launch-Agent-Launcher.bat exists."
}
$launcherLnk = Join-Path $calyxFolder 'Calyx Agent Launcher.lnk'
New-Shortcut -Path $launcherLnk -TargetPath $launcherBat -WorkingDirectory $root -IconLocation "$env:SystemRoot\System32\shell32.dll,44"

Write-Host "Shortcuts created:" -ForegroundColor Green
Write-Host " - $terminalLnk"
Write-Host " - $watcherLnk"
Write-Host " - $launcherLnk"
