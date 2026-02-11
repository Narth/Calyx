param(
    [string]$OutDir = "logs\calyx_guardian"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runLogPath = Join-Path $OutDir "run_log.jsonl"
$collectorStdout = Join-Path $OutDir "collector.stdout.log"
$collectorStderr = Join-Path $OutDir "collector.stderr.log"
$normalizerStderr = Join-Path $OutDir "normalizer.stderr.log"
$rendererStderr = Join-Path $OutDir "renderer.stderr.log"
$summaryJsonPath = Join-Path $OutDir "last_run_summary.json"
$summaryMdPath = Join-Path $OutDir "last_run_summary.md"

function Read-JsonLines {
    param([string]$Path)
    $items = @()
    if (!(Test-Path $Path)) {
        return $items
    }
    foreach ($line in Get-Content -Path $Path) {
        $trimmed = $line.Trim()
        if ($trimmed -eq "") { continue }
        try {
            $items += ($trimmed | ConvertFrom-Json)
        } catch {
            continue
        }
    }
    return $items
}

function Read-LastLines {
    param([string]$Path, [int]$Count)
    if (!(Test-Path $Path)) { return @() }
    return Get-Content -Path $Path -Tail $Count -ErrorAction SilentlyContinue
}

function Classify-Failure {
    param([string]$Text, [string]$Outcome)
    $lower = $Text.ToLowerInvariant()
    if ($Outcome -in @("timeout", "no_progress")) { return "timeout" }
    if ($lower -match "is not recognized" -or $lower -match "not found") { return "missing_command" }
    if ($lower -match "access is denied" -or $lower -match "unauthorized") { return "access_denied" }
    if ($lower -match "no module named" -or $lower -match "could not load file or assembly") { return "module_not_found" }
    if ($lower -match "parameter cannot be found" -or $lower -match "invalid argument") { return "invalid_argument" }
    if ($lower -match "read-host" -or $lower -match "noninteractive") { return "non_interactive_prompt_detected" }
    if ($lower -eq "") { return "unexpected_exception" }
    return "unexpected_exception"
}

function Next-Action {
    param([string]$Classification)
    switch ($Classification) {
        "missing_command" { return "install the missing command or ensure it is on PATH" }
        "access_denied" { return "re-run with elevated privileges if policy permits" }
        "module_not_found" { return "install the missing module/package and rerun" }
        "invalid_argument" { return "verify arguments and rerun" }
        "non_interactive_prompt_detected" { return "remove prompts or use non-interactive flags" }
        "timeout" { return "rerun with available resources; consider increasing timeout" }
        default { return "review logs and rerun" }
    }
}

$runEntries = Read-JsonLines -Path $runLogPath
$latestFailure = $runEntries | Where-Object { $_.PSObject.Properties.Match('outcome').Count -gt 0 } | Select-Object -Last 1

$failingStep = "unknown"
$exitCode = $null
$outcome = "unknown"
$command = ""

if ($null -ne $latestFailure) {
    $command = $latestFailure.command
    $exitCode = $latestFailure.exit_code
    $outcome = $latestFailure.outcome
    if ($command -match "guardian_assess_windows") { $failingStep = "collector" }
    elseif ($command -match "guardian_assess_windows.py") { $failingStep = "normalizer" }
    elseif ($command -match "render_report.py") { $failingStep = "renderer" }
}

$stderrLines = @()
if (Test-Path $collectorStderr) { $stderrLines = Read-LastLines -Path $collectorStderr -Count 50 }
if ($failingStep -eq "normalizer" -and (Test-Path $normalizerStderr)) { $stderrLines = Read-LastLines -Path $normalizerStderr -Count 50 }
if ($failingStep -eq "renderer" -and (Test-Path $rendererStderr)) { $stderrLines = Read-LastLines -Path $rendererStderr -Count 50 }

$stderrExcerpt = ($stderrLines | Out-String).Trim()
$classification = Classify-Failure -Text $stderrExcerpt -Outcome $outcome
$nextAction = Next-Action -Classification $classification

if ($latestFailure -eq $null -and $stderrExcerpt -eq "") {
    $failingStep = "none"
    $outcome = "success"
    $classification = "none"
    $nextAction = "none"
}

$summary = [ordered]@{
    failing_step = $failingStep
    outcome = $outcome
    exit_code = $exitCode
    command = $command
    stderr_excerpt = $stderrExcerpt
    classification = $classification
    next_required_action = $nextAction
}

$summary | ConvertTo-Json -Depth 6 | Set-Content -Path $summaryJsonPath -Encoding utf8

$mdLines = @(
    "# Calyx Guardian Last Run Summary",
    "",
    "- Failing step: $failingStep",
    "- Outcome: $outcome",
    "- Exit code: $exitCode",
    "- Classification: $classification",
    "- Next required action: $nextAction",
    "",
    "## Stderr excerpt (last 50 lines)",
    "",
    '```',
    $stderrExcerpt,
    '```'
)
$mdLines -join "`n" | Set-Content -Path $summaryMdPath -Encoding utf8
