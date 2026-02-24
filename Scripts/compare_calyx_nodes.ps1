# compare_calyx_nodes.ps1 — Two-node assessment: laptop Calyx (Z:) vs desktop Calyx_Terminal
# Run from a session where Z: is mapped to the laptop's Calyx share (e.g. \\LAPTOP\Calyx).
# Output: structured comparison of implementation paths and key artifacts.

param(
    [string] $LaptopRoot = "Z:\",
    [string] $DesktopRoot = "C:\Calyx_Terminal",
    [switch] $Json
)

$ErrorActionPreference = "SilentlyContinue"

$report = @{
    ts_utc        = [DateTime]::UtcNow.ToString("o")
    laptop_root   = $LaptopRoot
    desktop_root  = $DesktopRoot
    laptop_ok     = $false
    desktop_ok    = $false
    paths         = @{}
    comparison    = @()
    summary       = $null
}

# Key paths to check on both nodes (relative to repo root)
$keyPaths = @(
    "tools\calyx_sign.ps1",
    "governance\approvals",
    "governance\contracts\architect_approval.md",
    "governance\receipts\signing",
    "governance\identities\allowed_signers",
    "docs\operations\calyx_sign.md",
    "STATE.md",
    "README.md",
    "cbo_hub",
    "Scripts\start_calyx_core_services.ps1",
    "Scripts\check_calyx_core_services.ps1"
)

function Test-NodePath {
    param([string]$Root, [string]$RelPath)
    $full = Join-Path $Root $RelPath
    if (Test-Path $full) {
        $item = Get-Item -LiteralPath $full -ErrorAction SilentlyContinue
        return @{ exists = $true; path = $full; mode = if ($item) { $item.Mode.ToString() } else { "?" } }
    }
    return @{ exists = $false; path = $full; mode = $null }
}

# Check laptop (Z:)
if (Test-Path $LaptopRoot) {
    $report.laptop_ok = $true
    $report.paths.laptop = @{}
    foreach ($p in $keyPaths) {
        $report.paths.laptop[$p] = Test-NodePath -Root $LaptopRoot -RelPath $p
    }
    # Laptop script version if present
    $lapScript = Join-Path $LaptopRoot "tools\calyx_sign.ps1"
    if (Test-Path $lapScript) {
        $v = Select-String -Path $lapScript -Pattern "scriptVersion\s*=\s*[\`"']([^'\`"]+)" -AllMatches | ForEach-Object { $_.Matches.Groups[1].Value }
        $report.paths.laptop["tools/calyx_sign.ps1_version"] = if ($v) { $v } else { "?" }
    }
} else {
    $report.summary = "Laptop root not accessible (Z: not mapped or path wrong). Map Z: to \\LAPTOP\Calyx and re-run."
}

# Check desktop
if (Test-Path $DesktopRoot) {
    $report.desktop_ok = $true
    $report.paths.desktop = @{}
    foreach ($p in $keyPaths) {
        $report.paths.desktop[$p] = Test-NodePath -Root $DesktopRoot -RelPath $p
    }
    $deskScript = Join-Path $DesktopRoot "tools\calyx_sign.ps1"
    if (Test-Path $deskScript) {
        $v = Select-String -Path $deskScript -Pattern "scriptVersion\s*=\s*[\`"']([^'\`"]+)" -AllMatches | ForEach-Object { $_.Matches.Groups[1].Value }
        $report.paths.desktop["tools/calyx_sign.ps1_version"] = if ($v) { $v } else { "?" }
    }
} else {
    if (-not $report.summary) { $report.summary = "Desktop root not found: $DesktopRoot" }
}

# Build comparison rows
if ($report.laptop_ok -and $report.desktop_ok) {
    $report.comparison = foreach ($p in $keyPaths) {
        $lap = $report.paths.laptop[$p]
        $desk = $report.paths.desktop[$p]
        [PSCustomObject]@{
            path    = $p
            laptop  = if ($lap.exists) { "OK" } else { "missing" }
            desktop = if ($desk.exists) { "OK" } else { "missing" }
            same    = ($lap.exists -eq $desk.exists)
        }
    }
    $lapVer = $report.paths.laptop["tools/calyx_sign.ps1_version"]
    $deskVer = $report.paths.desktop["tools/calyx_sign.ps1_version"]
    $report.calyx_sign_versions = @{ laptop = $lapVer; desktop = $deskVer }
    $report.summary = "Laptop (Z:) and Desktop (Calyx_Terminal) both accessible. calyx_sign laptop=$lapVer desktop=$deskVer."
}

if ($Json) {
    $report | ConvertTo-Json -Depth 5 -Compress:$false
} else {
    Write-Host "=== Calyx two-node assessment ==="
    Write-Host "Laptop root:  $LaptopRoot  (OK: $($report.laptop_ok))"
    Write-Host "Desktop root: $DesktopRoot (OK: $($report.desktop_ok))"
    Write-Host ""
    if ($report.comparison) {
        Write-Host "Path comparison (laptop vs desktop):"
        $report.comparison | Format-Table -AutoSize
        Write-Host "calyx_sign.ps1 versions: laptop=$($report.calyx_sign_versions.laptop)  desktop=$($report.calyx_sign_versions.desktop)"
    }
    Write-Host ""
    Write-Host "Summary: $($report.summary)"
}
