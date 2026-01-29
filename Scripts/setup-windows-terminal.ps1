<#
.SYNOPSIS
    Applies Tokyo Night theme to Windows Terminal for Station Calyx

.DESCRIPTION
    This script adds the Tokyo Night color scheme and a Station Calyx profile
    to your Windows Terminal settings.

.NOTES
    Station Calyx / AI-For-All Project
#>

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ╭──────────────────────────────────────╮" -ForegroundColor Cyan
Write-Host "  │    🌸 Station Calyx Theme Setup 🌸   │" -ForegroundColor Cyan
Write-Host "  │      Windows Terminal Configuration  │" -ForegroundColor Cyan
Write-Host "  ╰──────────────────────────────────────╯" -ForegroundColor Cyan
Write-Host ""

# Windows Terminal settings path
$wtSettingsPath = "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json"
$wtPreviewSettingsPath = "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe\LocalState\settings.json"

# Check which version exists
$settingsPath = $null
if (Test-Path $wtSettingsPath) {
    $settingsPath = $wtSettingsPath
    Write-Host "  [✓] Found Windows Terminal" -ForegroundColor Green
} elseif (Test-Path $wtPreviewSettingsPath) {
    $settingsPath = $wtPreviewSettingsPath
    Write-Host "  [✓] Found Windows Terminal Preview" -ForegroundColor Green
} else {
    Write-Host "  [✗] Windows Terminal not found!" -ForegroundColor Red
    Write-Host "      Please install Windows Terminal from the Microsoft Store" -ForegroundColor Yellow
    Write-Host "      or via: winget install Microsoft.WindowsTerminal" -ForegroundColor Yellow
    exit 1
}

# Backup current settings
$backupPath = "$settingsPath.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Copy-Item $settingsPath $backupPath
Write-Host "  [✓] Backed up current settings to:" -ForegroundColor Green
Write-Host "      $backupPath" -ForegroundColor Gray

# Load current settings
$settings = Get-Content $settingsPath -Raw | ConvertFrom-Json

# Tokyo Night color scheme
$tokyoNight = @{
    name = "Tokyo Night"
    background = "#1A1B26"
    foreground = "#A9B1D6"
    cursorColor = "#C0CAF5"
    selectionBackground = "#33467C"
    black = "#15161E"
    red = "#F7768E"
    green = "#9ECE6A"
    yellow = "#E0AF68"
    blue = "#7AA2F7"
    purple = "#BB9AF7"
    cyan = "#7DCFFF"
    white = "#A9B1D6"
    brightBlack = "#414868"
    brightRed = "#F7768E"
    brightGreen = "#9ECE6A"
    brightYellow = "#E0AF68"
    brightBlue = "#7AA2F7"
    brightPurple = "#BB9AF7"
    brightCyan = "#7DCFFF"
    brightWhite = "#C0CAF5"
}

# Station Calyx profile
$calyxProfile = @{
    name = "Station Calyx"
    guid = "{station-calyx-0000-0000-000000000001}"
    commandline = "powershell.exe -NoExit -Command `"cd $PSScriptRoot\..; python calyx.py`""
    startingDirectory = "$PSScriptRoot\.."
    colorScheme = "Tokyo Night"
    icon = "🌸"
    hidden = $false
}

# Ensure schemes array exists
if (-not $settings.schemes) {
    $settings | Add-Member -NotePropertyName "schemes" -NotePropertyValue @()
}

# Add or update Tokyo Night scheme
$existingScheme = $settings.schemes | Where-Object { $_.name -eq "Tokyo Night" }
if ($existingScheme) {
    Write-Host "  [~] Updating existing Tokyo Night scheme" -ForegroundColor Yellow
    $index = [array]::IndexOf($settings.schemes, $existingScheme)
    $settings.schemes[$index] = [PSCustomObject]$tokyoNight
} else {
    Write-Host "  [+] Adding Tokyo Night color scheme" -ForegroundColor Green
    $settings.schemes += [PSCustomObject]$tokyoNight
}

# Ensure profiles.list exists
if (-not $settings.profiles.list) {
    $settings.profiles | Add-Member -NotePropertyName "list" -NotePropertyValue @()
}

# Add or update Station Calyx profile
$existingProfile = $settings.profiles.list | Where-Object { $_.name -eq "Station Calyx" }
if ($existingProfile) {
    Write-Host "  [~] Updating existing Station Calyx profile" -ForegroundColor Yellow
    $index = [array]::IndexOf($settings.profiles.list, $existingProfile)
    $settings.profiles.list[$index] = [PSCustomObject]$calyxProfile
} else {
    Write-Host "  [+] Adding Station Calyx profile" -ForegroundColor Green
    $settings.profiles.list = @([PSCustomObject]$calyxProfile) + $settings.profiles.list
}

# Set defaults
if (-not $settings.profiles.defaults) {
    $settings.profiles | Add-Member -NotePropertyName "defaults" -NotePropertyValue @{}
}
$settings.profiles.defaults | Add-Member -NotePropertyName "colorScheme" -NotePropertyValue "Tokyo Night" -Force
$settings.profiles.defaults | Add-Member -NotePropertyName "font" -NotePropertyValue @{ face = "JetBrains Mono"; size = 11 } -Force

# Save settings
$settings | ConvertTo-Json -Depth 10 | Set-Content $settingsPath -Encoding UTF8
Write-Host "  [✓] Settings saved!" -ForegroundColor Green

Write-Host ""
Write-Host "  ╭──────────────────────────────────────╮" -ForegroundColor Green
Write-Host "  │           Setup Complete!            │" -ForegroundColor Green
Write-Host "  ╰──────────────────────────────────────╯" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Cyan
Write-Host "    1. Restart Windows Terminal" -ForegroundColor White
Write-Host "    2. Select 'Station Calyx' from the dropdown" -ForegroundColor White
Write-Host "    3. Or press Ctrl+Shift+1 to launch it" -ForegroundColor White
Write-Host ""
Write-Host "  Note: For best results, install JetBrains Mono font:" -ForegroundColor Yellow
Write-Host "    https://www.jetbrains.com/lp/mono/" -ForegroundColor Gray
Write-Host ""
