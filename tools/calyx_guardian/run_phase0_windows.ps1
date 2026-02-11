param(
    [string]$OutDir = "logs\calyx_guardian",
    [switch]$Verify,
    [string]$StdoutPath,
    [string]$StderrPath,
    [string]$ElevationStatusPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$collector = Join-Path $scriptDir "guardian_assess_windows.ps1"
$normalizer = Join-Path $scriptDir "guardian_assess_windows.py"
$renderer = Join-Path $scriptDir "render\render_report.py"
$libPath = Join-Path $scriptDir "lib\run_with_timeout.ps1"
$runLogPath = Join-Path $OutDir "run_log.jsonl"

. $libPath

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$stdoutLog = if ($StdoutPath) { $StdoutPath } else { Join-Path $OutDir "phase0.stdout.log" }
$stderrLog = if ($StderrPath) { $StderrPath } else { Join-Path $OutDir "phase0.stderr.log" }
$elevationLog = if ($ElevationStatusPath) { $ElevationStatusPath } else { Join-Path $OutDir "elevation_status.json" }

Start-Transcript -Path $stdoutLog -Append | Out-Null

function Write-ErrorLog {
    param([string]$Message)
    $Message | Out-File -FilePath $stderrLog -Append -Encoding utf8
}

function Invoke-Stage {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$Arguments,
        [int]$TimeoutSeconds,
        [int]$NoProgressSeconds,
        [string]$StdoutPath,
        [string]$StderrPath,
        [switch]$AllowNonSuccess
    )
    $result = Invoke-GuardianProcess -FilePath $FilePath -Arguments $Arguments -TimeoutSeconds $TimeoutSeconds -NoProgressSeconds $NoProgressSeconds -StdoutPath $StdoutPath -StderrPath $StderrPath -RunLogPath $runLogPath
    if (-not $AllowNonSuccess -and $result.Outcome -ne "success") {
        throw "$Name $($result.Outcome)"
    }
    return $result
}

function Assert-NonEmptyFile {
    param([string]$Path)
    if (!(Test-Path $Path)) {
        throw "Missing artifact: $Path"
    }
    if ((Get-Item $Path).Length -eq 0) {
        throw "Empty artifact: $Path"
    }
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

$elevationStatus = [ordered]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    is_admin = $isAdmin
    user = $identity.Name
}
$elevationStatus | ConvertTo-Json -Depth 4 | Set-Content -Path $elevationLog -Encoding utf8
if (-not $isAdmin) {
    Write-Warning "Not running elevated. Blind spots: BitLocker status, PhysicalDisk health, and some Windows Update events may be limited."
}

$collectorOut = Join-Path $OutDir "collector.stdout.log"
$collectorErr = Join-Path $OutDir "collector.stderr.log"
$normalizerOut = Join-Path $OutDir "normalizer.stdout.log"
$normalizerErr = Join-Path $OutDir "normalizer.stderr.log"
$rendererOut = Join-Path $OutDir "renderer.stdout.log"
$rendererErr = Join-Path $OutDir "renderer.stderr.log"

$collectorResult = Invoke-Stage -Name "collector" -FilePath "powershell" -Arguments @(
    "-NoLogo",
    "-NoProfile",
    "-NonInteractive",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $collector,
    "-OutDir",
    $OutDir
) -TimeoutSeconds 600 -NoProgressSeconds 0 -StdoutPath $collectorOut -StderrPath $collectorErr -AllowNonSuccess

Invoke-Stage -Name "normalizer" -FilePath "py" -Arguments @(
    "-3.11",
    $normalizer,
    "--outdir",
    $OutDir
) -TimeoutSeconds 60 -NoProgressSeconds 30 -StdoutPath $normalizerOut -StderrPath $normalizerErr

Invoke-Stage -Name "renderer" -FilePath "py" -Arguments @(
    "-3.11",
    $renderer,
    "--outdir",
    $OutDir
) -TimeoutSeconds 60 -NoProgressSeconds 30 -StdoutPath $rendererOut -StderrPath $rendererErr

$evidencePath = Join-Path $OutDir "evidence.jsonl"
$findingsPath = Join-Path $OutDir "findings.json"
$reportPath = Join-Path $OutDir "report.md"

if (!(Test-Path $evidencePath) -or (Get-Item $evidencePath).Length -eq 0) {
    throw "collector fatal: evidence.jsonl missing or empty"
}

try {
    if ($Verify) {
        Assert-NonEmptyFile -Path $evidencePath
        Assert-NonEmptyFile -Path $findingsPath
        Assert-NonEmptyFile -Path $reportPath

        $firstByte = Get-Content -Path $evidencePath -Encoding Byte -TotalCount 1
        if ($firstByte[0] -ne 123) {
            throw "evidence.jsonl begins with BOM or unexpected byte"
        }

        $findingsHash1 = (Get-FileHash $findingsPath -Algorithm SHA256).Hash
        $reportHash1 = (Get-FileHash $reportPath -Algorithm SHA256).Hash

        Invoke-Stage -Name "normalizer" -FilePath "py" -Arguments @(
            "-3.11",
            $normalizer,
            "--outdir",
            $OutDir
        ) -TimeoutSeconds 60 -NoProgressSeconds 30 -StdoutPath $normalizerOut -StderrPath $normalizerErr

        Invoke-Stage -Name "renderer" -FilePath "py" -Arguments @(
            "-3.11",
            $renderer,
            "--outdir",
            $OutDir
        ) -TimeoutSeconds 60 -NoProgressSeconds 30 -StdoutPath $rendererOut -StderrPath $rendererErr

        $findingsHash2 = (Get-FileHash $findingsPath -Algorithm SHA256).Hash
        $reportHash2 = (Get-FileHash $reportPath -Algorithm SHA256).Hash

        if ($findingsHash1 -ne $findingsHash2) {
            throw "Determinism check failed for findings.json"
        }
        if ($reportHash1 -ne $reportHash2) {
            throw "Determinism check failed for report.md"
        }
    }

    $summaryStatus = "PASS"
    if ($collectorResult.Outcome -ne "success") {
        $summaryStatus = "PASS_WITH_BLIND_SPOTS"
    }
    Write-Host "Phase 0 $summaryStatus"
    Write-Host "Artifacts:"
    Write-Host "- $evidencePath"
    Write-Host "- $findingsPath"
    Write-Host "- $reportPath"
    Write-Host "next_required_action: none"
} catch {
    $summaryStatus = "FAIL"
    Write-Host "Phase 0 $summaryStatus"
    Write-Host "Artifacts:"
    Write-Host "- $evidencePath"
    Write-Host "- $findingsPath"
    Write-Host "- $reportPath"
    Write-Host "next_required_action: review logs and rerun Phase 0"
    Write-ErrorLog $_.Exception.Message
    Stop-Transcript | Out-Null
    throw
}
Stop-Transcript | Out-Null
