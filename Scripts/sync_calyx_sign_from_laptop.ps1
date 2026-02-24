# sync_calyx_sign_from_laptop.ps1 — Copy calyx_sign.ps1 from laptop (Z:) to desktop tools/
# Run when Z: is mapped to the laptop's Calyx share. The laptop script has worked reliably;
# the desktop has had V: visibility issues. Use this to adopt the laptop implementation.
# See docs/operations/CALYX_SIGN_LAPTOP_RUNBOOK.md

param(
    [string] $LaptopRoot = "Z:",
    [string] $DesktopRepoRoot = ""
)

$DesktopRepoRoot = if ($DesktopRepoRoot) { $DesktopRepoRoot } elseif ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }

$src = Join-Path $LaptopRoot "tools\calyx_sign.ps1"
$dst = Join-Path $DesktopRepoRoot "tools\calyx_sign.ps1"

if (-not (Test-Path -LiteralPath $src -PathType Leaf)) {
    Write-Error "Laptop script not found: $src. Ensure Z: is mapped to the laptop Calyx share and the script exists at Z:\tools\calyx_sign.ps1."
}

Copy-Item -LiteralPath $src -Destination $dst -Force
Write-Host "Copied $src -> $dst"
Write-Host "Laptop calyx_sign implementation is now in use on the desktop."
