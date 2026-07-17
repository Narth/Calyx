# Baseline Parity Check - classify Git worktree state without mutating it.
#
# Purpose:
#   Keep canonical repo baseline, local node state, curated continuity, and audit
#   evidence from silently impersonating one another.
#
# Outputs:
#   runtime/baseline_parity_report.json
#   runtime/node_manifest.json
#
# Exit:
#   0 = report written
#   1 = git unavailable or report could not be written

param(
    [switch]$Json = $false,
    [switch]$FailOnLocalStateVisible = $false
)

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path (Join-Path $repoRoot ".git"))) {
    $repoRoot = (Get-Location).Path
}
Set-Location $repoRoot

function ConvertTo-RepoPath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return "" }
    $normalized = ($Path -replace "\\", "/").Trim()
    if ($normalized.Length -ge 2 -and $normalized.StartsWith('"') -and $normalized.EndsWith('"')) {
        $normalized = $normalized.Substring(1, $normalized.Length - 2)
    }
    return $normalized
}

function Test-PathPrefix {
    param(
        [string]$Path,
        [string[]]$Prefixes
    )
    foreach ($prefix in $Prefixes) {
        if ($Path -eq $prefix.TrimEnd("/")) { return $true }
        if ($Path.StartsWith($prefix)) { return $true }
    }
    return $false
}

function Get-BaselineClass {
    param(
        [string]$Path,
        [string]$Status
    )
    $p = ConvertTo-RepoPath $Path

    $localPrefixes = @(
        "runtime/",
        "logs/",
        "outgoing/",
        "incoming/",
        "responses/",
        "staging/",
        "memory/",
        "state/",
        "telemetry/",
        "exports/",
        "reports/",
        "private/",
        "keys/",
        "cbo_hub/data/",
        ".openclaw/",
        "openclaw/credentials/",
        "openclaw/devices/",
        "openclaw/identity/",
        "openclaw/agents/main/sessions/",
        "openclaw/media/inbound/"
    )
    if (Test-PathPrefix -Path $p -Prefixes $localPrefixes) {
        return "local_node_state"
    }

    $localExact = @(
        ".env",
        "DISCORD_IDS.md",
        "HEALTH.md",
        "MEMORY.md",
        "openclaw/exec-approvals.json",
        "openclaw/workspace-state.json",
        "skills/user_contexts.json"
    )
    if ($p -in $localExact -or $p -like ".env.*") {
        return "local_node_state"
    }

    $scratchPrefixes = @(
        ".pytest_",
        ".cbo_pytest_min_probe/",
        ".pytest_cache/",
        ".mypy_cache/",
        ".ruff_cache/",
        "__pycache__/",
        "analysis/",
        "tmp_lifecycle_case",
        "tools/_rg_tmp/",
        "benchmarks/results/"
    )
    if (Test-PathPrefix -Path $p -Prefixes $scratchPrefixes) {
        return "scratch_or_generated"
    }
    if ($p -like "temp_*" -or $p -like "*.tmp" -or $p -like "*.log" -or $p -like "*.sqlite" -or $p -like "*.db") {
        return "scratch_or_generated"
    }

    if ($p -eq "STATE.md") {
        return "runtime_digest"
    }

    $openClawFunctionalityPrefixes = @(
        "openclaw/",
        "skills/"
    )
    if (Test-PathPrefix -Path $p -Prefixes $openClawFunctionalityPrefixes) {
        return "openclaw_functionality"
    }

    $canonicalPrefixes = @(
        "Scripts/",
        "calyx/",
        "cbo_hub/",
        "docs/",
        "tests/",
        "tools/",
        "rust/",
        "benchmarks/",
        "policy/",
        "governance/",
        "proposals/",
        "ide_toolbox/"
    )
    if (Test-PathPrefix -Path $p -Prefixes $canonicalPrefixes) {
        return "canonical_candidate"
    }

    $canonicalExact = @(
        ".gitignore",
        "AGENTS.md",
        "CALYX_CONTRACT.yaml",
        "COMPENDIUM.md",
        "HEARTBEAT.md",
        "HISTORY.md",
        "IDENTITY.md",
        "README.md",
        "SOUL.md",
        "TOOLS.md",
        "USER.md",
        "requirements.txt"
    )
    if ($p -in $canonicalExact) {
        return "canonical_candidate"
    }

    if ($Status.Trim().StartsWith("D")) {
        return "operator_decision"
    }

    return "operator_decision"
}

function Get-ClassificationReason {
    param([string]$Class)
    switch ($Class) {
        "canonical_candidate" { return "Reviewable source, doctrine, policy, docs, tests, or tooling that may belong in the Git baseline." }
        "local_node_state" { return "Node-specific runtime, identity, continuity, telemetry, or secret-adjacent state; do not commit by default." }
        "scratch_or_generated" { return "Temporary, cache, generated, or probe output; exclude from baseline." }
        "runtime_digest" { return "Generated current Station digest; keep live locally and track only the canonical template/schema." }
        "openclaw_functionality" { return "Auxiliary OpenClaw or skill functionality; not Station baseline material." }
        "operator_decision" { return "Authority, continuity, historical integration, or ambiguous surface requiring explicit operator decision." }
        default { return "Unclassified." }
    }
}

function Read-GitStatus {
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = "git"
    $psi.Arguments = "status --short --untracked-files=all"
    $psi.WorkingDirectory = $repoRoot
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $proc = [System.Diagnostics.Process]::Start($psi)
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    if ($proc.ExitCode -ne 0) {
        throw "git status failed rc=$($proc.ExitCode): $stderr"
    }
    return [ordered]@{
        stdout = $stdout
        stderr = $stderr
    }
}

function Get-GitValue {
    param([string[]]$GitArgs)
    try {
        $value = & git @GitArgs 2>$null
        if ($LASTEXITCODE -eq 0) { return (($value | Out-String).Trim()) }
    } catch { }
    return ""
}

$statusResult = Read-GitStatus
$entries = @()
foreach ($line in ($statusResult.stdout -split "`r?`n")) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    if ($line.Length -lt 4) { continue }
    $status = $line.Substring(0, 2)
    $path = ConvertTo-RepoPath ($line.Substring(3))
    if ($path -match " -> ") {
        $path = ConvertTo-RepoPath (($path -split " -> ")[-1])
    }
    $class = Get-BaselineClass -Path $path -Status $status
    $entries += [ordered]@{
        status = $status.Trim()
        path = $path
        baseline_class = $class
        reason = Get-ClassificationReason -Class $class
    }
}

$countsByClass = [ordered]@{}
foreach ($class in @("canonical_candidate", "operator_decision", "runtime_digest", "openclaw_functionality", "local_node_state", "scratch_or_generated")) {
    $countsByClass[$class] = @($entries | Where-Object { $_.baseline_class -eq $class }).Count
}

$countsByStatus = [ordered]@{
    modified = @($entries | Where-Object { $_.status -match "M" }).Count
    deleted = @($entries | Where-Object { $_.status -match "D" }).Count
    untracked = @($entries | Where-Object { $_.status -eq "??" }).Count
    total = @($entries).Count
}

$branch = Get-GitValue -GitArgs @("rev-parse", "--abbrev-ref", "HEAD")
$head = Get-GitValue -GitArgs @("rev-parse", "HEAD")
$nodeIdPath = Join-Path $repoRoot "runtime\node_id.txt"
$nodeId = ""
if (Test-Path -LiteralPath $nodeIdPath -PathType Leaf) {
    try { $nodeId = (Get-Content -LiteralPath $nodeIdPath -Raw -Encoding UTF8).Trim() } catch { $nodeId = "" }
}

$now = [datetime]::UtcNow.ToString("o")
$report = [ordered]@{
    schema = "station.baseline_parity_report.v1"
    emitted_ts_utc = $now
    authority = "advisory_only"
    authority_boundary_note = "Classifies worktree state; does not stage, commit, delete, or authorize sync."
    repo_root = $repoRoot
    branch = $branch
    head = $head
    node_id = $nodeId
    baseline_manifest = "docs/canonical/STATION_BASELINE_MANIFEST.md"
    counts_by_class = $countsByClass
    counts_by_status = $countsByStatus
    git_status_warnings = @($statusResult.stderr -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    visible_local_state_count = $countsByClass.local_node_state
    visible_scratch_count = $countsByClass.scratch_or_generated
    runtime_digest_count = $countsByClass.runtime_digest
    openclaw_functionality_count = $countsByClass.openclaw_functionality
    operator_decision_count = $countsByClass.operator_decision
    canonical_candidate_count = $countsByClass.canonical_candidate
    entries = $entries
}

$nodeManifest = [ordered]@{
    schema = "station.node_manifest.v1"
    emitted_ts_utc = $now
    node_id = $nodeId
    repo_root = $repoRoot
    branch = $branch
    head = $head
    local_state_roots = @("runtime/", "logs/", "outgoing/", "memory/", "state/", "incoming/", "responses/", "staging/")
    generated_artifacts = @("runtime/baseline_parity_report.json", "runtime/node_manifest.json")
    portability_note = "This manifest identifies node-local state for this workstation. It is generated runtime state and is not committed by default."
}

$runtimeDir = Join-Path $repoRoot "runtime"
if (-not (Test-Path -LiteralPath $runtimeDir)) {
    New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
}
$reportPath = Join-Path $runtimeDir "baseline_parity_report.json"
$nodeManifestPath = Join-Path $runtimeDir "node_manifest.json"
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
$nodeManifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $nodeManifestPath -Encoding UTF8

if ($Json) {
    $report | ConvertTo-Json -Depth 8
} else {
    Write-Host ("BASELINE_PARITY total={0} canonical_candidate={1} operator_decision={2} runtime_digest={3} openclaw_functionality={4} local_node_state={5} scratch_or_generated={6}" -f `
        $countsByStatus.total, `
        $countsByClass.canonical_candidate, `
        $countsByClass.operator_decision, `
        $countsByClass.runtime_digest, `
        $countsByClass.openclaw_functionality, `
        $countsByClass.local_node_state, `
        $countsByClass.scratch_or_generated)
    Write-Host "Report: runtime\baseline_parity_report.json"
    Write-Host "Node manifest: runtime\node_manifest.json"
    if ($statusResult.stderr.Trim()) {
        Write-Host "Warnings captured from git status; see report." -ForegroundColor Yellow
    }
}

if ($FailOnLocalStateVisible -and $countsByClass.local_node_state -gt 0) {
    exit 1
}
exit 0
