function Invoke-GuardianProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [int]$TimeoutSeconds = 60,
        [int]$NoProgressSeconds = 0,
        [string]$StdoutPath,
        [string]$StderrPath,
        [string]$WorkingDirectory,
        [string]$RunLogPath = "logs\calyx_guardian\run_log.jsonl"
    )

    $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

    function Write-JsonLine {
        param([string]$Path, [string]$JsonLine)
        $writer = New-Object System.IO.StreamWriter($Path, $true, $Utf8NoBom)
        try {
            $writer.WriteLine($JsonLine)
        } finally {
            $writer.Dispose()
        }
    }

    $startUtc = [DateTime]::UtcNow
    $stdoutPath = if ($StdoutPath) { $StdoutPath } else { [System.IO.Path]::GetTempFileName() }
    $stderrPath = if ($StderrPath) { $StderrPath } else { [System.IO.Path]::GetTempFileName() }
    $workDir = if ($WorkingDirectory) { $WorkingDirectory } else { (Get-Location).Path }
    $commandLine = "$FilePath $($Arguments -join ' ')"

    $process = $null
    $outcome = "unknown"
    $exitCode = $null
    $lastOutputUtc = $startUtc

    try {
        $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $workDir -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru -NoNewWindow
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

        $lastSize = 0
        $process.Refresh()
        while (-not $process.HasExited) {
            Start-Sleep -Seconds 1
            $process.Refresh()
            $elapsed = $stopwatch.Elapsed.TotalSeconds

            if ($TimeoutSeconds -gt 0 -and $elapsed -ge $TimeoutSeconds) {
                $outcome = "timeout"
                break
            }

            if ($NoProgressSeconds -gt 0) {
                $currentSize = 0
                if (Test-Path $stdoutPath) { $currentSize += (Get-Item $stdoutPath).Length }
                if (Test-Path $stderrPath) { $currentSize += (Get-Item $stderrPath).Length }
                if ($currentSize -ne $lastSize) {
                    $lastOutputUtc = [DateTime]::UtcNow
                    $lastSize = $currentSize
                }
                $noProgressFor = ([DateTime]::UtcNow - $lastOutputUtc).TotalSeconds
                if ($noProgressFor -ge $NoProgressSeconds) {
                    $outcome = "no_progress"
                    break
                }
            }
        }

        if (-not $process.HasExited -and $outcome -in @("timeout", "no_progress")) {
            try {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                & cmd.exe /c "taskkill /PID $($process.Id) /T /F" | Out-Null
            } catch {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        }

        if ($process) {
            $process.WaitForExit() | Out-Null
            $process.Refresh()
        }

        if ($process -and $process.HasExited) {
            try {
                $exitCode = $process.ExitCode
            } catch {
                $exitCode = $null
            }
            if ($null -eq $exitCode) {
                $stderrSize = if (Test-Path $stderrPath) { (Get-Item $stderrPath).Length } else { 0 }
                $exitCode = if ($stderrSize -gt 0) { 1 } else { 0 }
            }
            if ($exitCode -eq 0) {
                $outcome = "success"
            } elseif ($outcome -eq "unknown") {
                $outcome = "failed"
            }
        } elseif ($outcome -eq "unknown") {
            $outcome = "cancelled"
        }
    } catch [System.Management.Automation.PipelineStoppedException] {
        $outcome = "cancelled"
    } catch {
        $outcome = "failed"
    }

    $endUtc = [DateTime]::UtcNow
    $tailLines = @()
    if (Test-Path $stderrPath) {
        $tailLines += Get-Content -Path $stderrPath -Tail 10 -ErrorAction SilentlyContinue
    }
    if (Test-Path $stdoutPath) {
        $tailLines += Get-Content -Path $stdoutPath -Tail 10 -ErrorAction SilentlyContinue
    }
    $tailText = ($tailLines | Out-String).Trim()

    if ($outcome -in @("timeout", "no_progress", "cancelled")) {
        $record = [ordered]@{
            ts_utc = $endUtc.ToString("o")
            outcome = $outcome
            command = $FilePath
            args = $Arguments
            start_utc = $startUtc.ToString("o")
            end_utc = $endUtc.ToString("o")
            exit_code = $exitCode
            last_output_tail = $tailText
        }
        Write-JsonLine -Path $RunLogPath -JsonLine ($record | ConvertTo-Json -Compress)
    }

    return [ordered]@{
        StartUtc = $startUtc.ToString("o")
        EndUtc = $endUtc.ToString("o")
        Outcome = $outcome
        ExitCode = $exitCode
        StdoutPath = $stdoutPath
        StderrPath = $stderrPath
        CommandLine = $commandLine
    }
}
