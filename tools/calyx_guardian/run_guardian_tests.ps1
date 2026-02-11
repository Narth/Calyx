param(
    [string]$OutDir = "logs\calyx_guardian",
    [int]$MaxRetries = 2,
    [switch]$Smoke,
    [switch]$Full
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logPath = Join-Path $OutDir "pytest_run.log"
$summaryPath = Join-Path $OutDir "pytest_run.json"
$runLogPath = Join-Path $OutDir "run_log.jsonl"
$libPath = Join-Path $scriptDir "lib\run_with_timeout.ps1"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

. $libPath

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
if (Test-Path $logPath) {
    Remove-Item -Force $logPath
}

function Write-LogLine {
    param([string]$Line)
    $writer = New-Object System.IO.StreamWriter($logPath, $true, $Utf8NoBom)
    try {
        $writer.WriteLine($Line)
    } finally {
        $writer.Dispose()
    }
}

function Format-ExitCode {
    param($ExitCode)
    if ($null -eq $ExitCode) { return "n/a" }
    return $ExitCode
}

function Get-ResultExitCode {
    param($Result)
    if ($null -eq $Result) { return "skipped" }
    return (Format-ExitCode $Result.ExitCode)
}

function Invoke-PytestRun {
    param(
        [string[]]$PytestArgs,
        [string]$Label,
        [int]$TimeoutSeconds
    )
    $stdoutPath = Join-Path $OutDir "$Label.stdout.log"
    $stderrPath = Join-Path $OutDir "$Label.stderr.log"

    Write-LogLine "START $Label Args=$($PytestArgs -join ' ')"

    $result = Invoke-GuardianProcess -FilePath "py" -Arguments (@("-3.11", "-m", "pytest") + $PytestArgs) -TimeoutSeconds $TimeoutSeconds -NoProgressSeconds 60 -StdoutPath $stdoutPath -StderrPath $stderrPath -RunLogPath $runLogPath

    $stdoutText = ""
    $stderrText = ""
    if (Test-Path $stdoutPath) { $stdoutText = Get-Content -Path $stdoutPath -Raw -ErrorAction SilentlyContinue }
    if (Test-Path $stderrPath) { $stderrText = Get-Content -Path $stderrPath -Raw -ErrorAction SilentlyContinue }
    $outputText = ($stdoutText + "`n" + $stderrText).Trim()

    foreach ($line in ($outputText -split "`r?`n")) {
        if ($line -ne "") { Write-LogLine $line }
    }

    $exitCode = $result.ExitCode
    if ($null -eq $exitCode) {
        if ($outputText -match "FAILED|ERROR|failed") {
            $exitCode = 1
        } else {
            $exitCode = 0
        }
        if ($exitCode -eq 0) {
            $result.Outcome = "success"
        } elseif ($result.Outcome -eq "unknown") {
            $result.Outcome = "failed"
        }
    }

    Write-LogLine "END $Label UTC=$($result.EndUtc) ExitCode=$exitCode Outcome=$($result.Outcome)"

    $lastTest = ""
    $testMatches = [regex]::Matches($outputText, "[A-Za-z0-9_\\/\\.-]+::[A-Za-z0-9_\\.]+")
    if ($testMatches.Count -gt 0) {
        $lastTest = $testMatches[$testMatches.Count - 1].Value
    }

    $interruption = "none"
    if ($result.Outcome -in @("timeout", "no_progress")) {
        $interruption = $result.Outcome
    } elseif ($outputText -match "KeyboardInterrupt") {
        $interruption = "KeyboardInterrupt"
    } elseif ($outputText -match "Interrupted") {
        $interruption = "Interrupted"
    } elseif ($outputText -match "ERROR collecting") {
        $interruption = "pytest collection error"
    } elseif ($result.Outcome -eq "failed") {
        $interruption = "pytest_failure"
    }

    return [ordered]@{
        StartUtc = $result.StartUtc
        EndUtc = $result.EndUtc
        WallSeconds = ([datetime]$result.EndUtc - [datetime]$result.StartUtc).TotalSeconds
        ExitCode = $exitCode
        Outcome = $result.Outcome
        LastTest = $lastTest
        Interruption = $interruption
        StdoutPath = $stdoutPath
        StderrPath = $stderrPath
    }
}

$runSmoke = $Smoke -or (-not $Smoke -and -not $Full)
$runFull = $Full -or (-not $Smoke -and -not $Full)

$smokeResult = $null
$fullResult = $null

if ($runSmoke) {
    $smokeArgs = @("tools\\calyx_guardian\\tests\\test_smoke_phase0.py", "-q")
    $smokeResult = Invoke-PytestRun -PytestArgs $smokeArgs -Label "guardian_smoke" -TimeoutSeconds 120
    if ($smokeResult.Outcome -ne "success") {
        $summary = "Guardian tests complete. SmokeExit=$(Format-ExitCode $smokeResult.ExitCode) FullExit=skipped Log=$logPath"
        Write-LogLine $summary
        Write-Host $summary
        Write-Host "FAIL"
        Write-Host "Artifacts:"
        Write-Host "- $logPath"
        Write-Host "- $summaryPath"
        Write-Host "next_required_action: fix smoke failures and rerun"
        $summaryData = [ordered]@{
            smoke = $smokeResult
            full = $fullResult
            status = "FAIL"
        }
        $summaryData | ConvertTo-Json -Depth 6 | Set-Content -Path $summaryPath -Encoding utf8
        exit $smokeResult.ExitCode
    }
}

if ($runFull) {
    $fullArgs = @("tools\\calyx_guardian\\tests", "-q")
    $attempt = 0
    while ($attempt -le $MaxRetries) {
        $fullResult = Invoke-PytestRun -PytestArgs $fullArgs -Label "guardian_full_attempt_$attempt" -TimeoutSeconds 600
        if ($fullResult.Outcome -eq "success") {
            break
        }
        if ($fullResult.Interruption -notin @("KeyboardInterrupt", "Interrupted", "timeout", "no_progress", "cancelled")) {
            break
        }
        if ($attempt -lt $MaxRetries) {
            Start-Sleep -Seconds 5
        }
        $attempt += 1
    }
}

$status = "PASS"
if ($smokeResult -and $smokeResult.Outcome -ne "success") {
    $status = "FAIL"
} elseif ($fullResult -and $fullResult.Outcome -ne "success") {
    $status = if ($fullResult.Outcome -in @("timeout", "no_progress")) { "TIMEOUT" } else { "FAIL" }
}

$summaryData = [ordered]@{
    smoke = $smokeResult
    full = $fullResult
    status = $status
}
$summaryData | ConvertTo-Json -Depth 6 | Set-Content -Path $summaryPath -Encoding utf8

$summary = "Guardian tests complete. SmokeExit=$(Get-ResultExitCode $smokeResult) FullExit=$(Get-ResultExitCode $fullResult) Status=$status Log=$logPath"
Write-LogLine $summary
Write-Host $summary
Write-Host $status
Write-Host "Artifacts:"
Write-Host "- $logPath"
Write-Host "- $summaryPath"
if ($status -ne "PASS") {
    Write-Host "next_required_action: review pytest_run.log and rerun"
    exit 1
}
Write-Host "next_required_action: none"
