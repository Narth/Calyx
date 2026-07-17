# Install IDE toolbox to .vscode/ (works for Cursor and VS Code)
$ErrorActionPreference = "Stop"
$scriptDir = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
$dst = Join-Path $repoRoot ".vscode"

if (-not (Test-Path $dst)) {
    New-Item -ItemType Directory -Path $dst -Force | Out-Null
}

$files = @("tasks.json", "launch.json", "settings.json", "extensions.json")
foreach ($f in $files) {
    $srcPath = Join-Path $scriptDir $f
    if (Test-Path $srcPath) {
        Copy-Item $srcPath $dst -Force
        Write-Host "Installed $f"
    }
}

Write-Host "IDE toolbox installed to .vscode/ (Cursor and VS Code)"
