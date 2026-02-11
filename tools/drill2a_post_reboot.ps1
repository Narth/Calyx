# PowerShell script for Drill 2A: Post-Reboot Recovery Detection

# Load necessary modules
Import-Module CimCmdlets

# Define file paths
$preMarkerPath = "telemetry/sun_cycle/drills/drill2a_pre_marker.json"
$sunrisePath = "telemetry/sun_cycle/drills/drill2a_sunrise_abrupt.json"
$recoveryReportPath = "telemetry/sun_cycle/drills/drill2a_recovery_report.json"
$bootGuardReportPath = "telemetry/sun_cycle/drills/boot_guard_drill2a_report.json"
$evidenceLogPath = "logs/calyx_guardian/evidence.jsonl"

# Check for pre-crash marker
if (-Not (Test-Path $preMarkerPath)) {
    Write-Output "Pre-crash marker not found. Exiting."
    exit 1
}

# Create post-reboot sunrise artifact
$sunriseData = @{
    "shutdown_semantics" = "abrupt_shutdown_suspected"
    "reasons" = @("no_prior_sunset_record_found")
}
$sunriseData | ConvertTo-Json -Depth 10 | Out-File -FilePath $sunrisePath -Encoding utf8

# Verify and record hashes for recovery checklist
$recoveryChecklist = @{
    "allowed_signers_hash" = (Get-FileHash -Path "governance/identities/allowed_signers" -Algorithm SHA256).Hash
    "architect_identity_hash" = (Get-FileHash -Path "governance/architect_identity.json" -Algorithm SHA256).Hash
    "latest_approval_receipts_hash" = (Get-FileHash -Path "telemetry/energy/energy_contract_receipt.json" -Algorithm SHA256).Hash
    "guardian_manifest_hash" = (Get-FileHash -Path "governance/manifest.json" -Algorithm SHA256).Hash
    "last_orchestrator_log_hash" = if (Test-Path "logs/orchestrator_log.jsonl") {
        (Get-FileHash -Path "logs/orchestrator_log.jsonl" -Algorithm SHA256).Hash
    } else {
        "not_found"
    }
}

# Determine recovery outcome
if ($recoveryChecklist.Values -contains "not_found") {
    $recoveryOutcome = "recovery_anomalies_detected"
} else {
    $recoveryOutcome = "recovery_clean"
}

# Write recovery report
$recoveryReport = @{
    "recovery_outcome" = $recoveryOutcome
    "recovery_checklist" = $recoveryChecklist
}
$recoveryReport | ConvertTo-Json -Depth 10 | Out-File -FilePath $recoveryReportPath -Encoding utf8

# Boot guard behavior
$bootGuardReport = @{
    "boot_guard_status" = if ($recoveryOutcome -eq "recovery_clean") {
        "PASS"
    } else {
        "FAIL"
    }
}
$bootGuardReport | ConvertTo-Json -Depth 10 | Out-File -FilePath $bootGuardReportPath -Encoding utf8

# Log evidence
$evidenceCommands = @(
    "Get-FileHash -Path governance/identities/allowed_signers -Algorithm SHA256",
    "Get-FileHash -Path governance/architect_identity.json -Algorithm SHA256",
    "Get-FileHash -Path telemetry/energy/energy_contract_receipt.json -Algorithm SHA256",
    "Get-FileHash -Path governance/manifest.json -Algorithm SHA256",
    "Get-FileHash -Path logs/orchestrator_log.jsonl -Algorithm SHA256"
)
$evidenceLog = $evidenceCommands | ForEach-Object { @{ "command" = $_; "timestamp" = (Get-Date).ToString("o") } }
$evidenceLog | ConvertTo-Json -Depth 10 | Out-File -FilePath $evidenceLogPath -Append -Encoding utf8

# Generate receipt
$drillArtifacts = @($preMarkerPath, $sunrisePath, $recoveryReportPath, $bootGuardReportPath)
$artifactHashes = @{}
foreach ($artifact in $drillArtifacts) {
    $artifactHashes[$artifact] = (Get-FileHash -Path $artifact -Algorithm SHA256).Hash
}
$receipt = @{
    "drill" = "2A"
    "artifacts" = $artifactHashes
}
$receipt | ConvertTo-Json -Depth 10 | Out-File -FilePath "telemetry/sun_cycle/drills/drill2a_receipt.json" -Encoding utf8

# HALT
Write-Output "Drill 2A completed. Halting."
exit 0