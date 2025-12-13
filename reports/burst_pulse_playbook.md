# Station Calyx — Burst Snapshot & Pulse Playbook (v0.1)

Purpose: Run short investigative bursts to validate TES penalties and uptime/health under Safe Mode. No code changes; file-write only.

## Default Burst Settings
- Snapshots: every 2.5 minutes, 16 iterations (~40 min), tagged `burst snapshot <n>` in `logs/system_snapshots.jsonl`.
- Pulses: every 5 minutes, 8 iterations (~40 min), reports in `reports/bridge_pulse_burst-<timestamp>.md`.
- Governance hash reference: `4E4924361545468CB42387F38C946A3C3E802BD1494868C378FBE7DBB5FFD6D7`.

## Run Commands (PowerShell, from repo root)
```powershell
# Tune if desired
$snapIntervalSec = 150   # 2.5 min
$snapIters       = 16    # ~40 min
$pulseIntervalSec = 300  # 5 min
$pulseIters       = 8    # ~40 min

# Snapshot job
$snapJob = Start-Job -Name snap_burst -ScriptBlock {
    param($root,$iters,$sleepSec)
    for($i=0;$i -lt $iters; $i++){
        $ts = (Get-Date).ToUniversalTime().ToString('o')
        $count = (Get-Process python -ErrorAction SilentlyContinue | Measure-Object).Count
        $line = '{\"timestamp\": \"'+$ts+'\", \"count\": '+$count+', \"note\": \"burst snapshot '+$i+'\"}'
        Add-Content -Path (Join-Path $root 'logs/system_snapshots.jsonl') -Value $line
        Start-Sleep -Seconds $sleepSec
    }
} -ArgumentList (Get-Location).Path,$snapIters,$snapIntervalSec

# Pulse job
$pulseJob = Start-Job -Name pulse_burst -ScriptBlock {
    param($root,$iters,$sleepSec)
    for($i=0;$i -lt $iters; $i++){
        $id = ('burst-{0:yyyyMMddTHHmmss}' -f (Get-Date).ToUniversalTime())
        python (Join-Path $root 'tools/bridge_pulse_generator.py') --report-id $id | Out-String | Write-Output
        Start-Sleep -Seconds $sleepSec
    }
} -ArgumentList (Get-Location).Path,$pulseIters,$pulseIntervalSec

"Started snap job ID: $($snapJob.Id)"
"Started pulse job ID: $($pulseJob.Id)"
Get-Job | Where-Object {$_.Name -in 'snap_burst','pulse_burst'}
```

## Stop / Cleanup
```powershell
Stop-Job -Name snap_burst,pulse_burst -ErrorAction SilentlyContinue
Remove-Job -Name snap_burst,pulse_burst -ErrorAction SilentlyContinue
```

## Outputs to Review
- Pulses: `reports/bridge_pulse_burst-*.md` plus any bp-XXXX generated during bursts.
- Snapshots: `logs/system_snapshots.jsonl` (entries tagged `burst snapshot <n>`).
- TES evidence: `logs/agent_metrics_recalculated.csv`, `logs/tes_golden_sample.csv`, `logs/tes_failure_sample.csv`, `reports/tes_validation_20251203.md`.

## Recommended Cadence
- Run an investigative burst (40–60 min) after any TES scoring change or new model/agent onboarding.
- Keep standard hourly/daily pulses outside bursts to avoid report noise.

## Governance Notes
- Safe Mode only; no autonomy, scheduling, or external calls.
- Version changes to governance docs remain under Architect authority; this playbook documents operational procedure only.
