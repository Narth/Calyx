# Assisting Agent Briefing

Welcome to Station Calyx. Partner with the Central Bridge Overseer (CBO) to keep the task pipeline healthy and compliant. Review the mission charter in `calyx/cbo/CBO_CHARTER.md` before engaging.

## Core Responsibilities
- **Approvals**: review the Approvals panel in Agent Watcher; respond to pending CBO requests with Approve/Reject so automation can proceed.
- **Objective Intake**: submit new goals via `POST /objective` or append to `calyx/cbo/objectives.jsonl` (one JSON object per line).
- **Queue Oversight**: monitor `GET /report`, `calyx/cbo/task_queue.jsonl`, and `logs/cbo_dispatch.log` for stalled, failed, or backlogged work.
- **Agent Coordination**: direct workers to `POST /claim` for new tasks and `POST /status` for progress updates. Keep `agent_id` values consistent for audit trails.
- **Governance Watch**: if `/report` or the heartbeat feedback flags `resource_ok=0` or `policy_ok=0`, pause discretionary dispatch and alert human oversight.
- **TES Health**: track `tes_mean20` and trend indicators; if TES declines, gather context from recent runs (see `logs/agent_metrics.csv`) before recommending corrective actions.
- **Maintenance Cycle**: run `python tools/cbo_maintenance.py` whenever the overseer is restarted or at least hourly during heavy usage; archive output to shared notes (already scheduled every 30 minutes as `CalyxMaintenance`).

## Operational Tips
- Use the Approvals panel (Agent Watcher ➜ Conversation section) to keep oversight aligned; unresolved requests block automation.
- Honour `calyx/core/policy.yaml`; the governance kernel clears unregistered assignees automatically and will pause dispatch when CPU/RAM exceed limits.
- Metrics from each heartbeat flow into `metrics/bridge_pulse.csv` (watch for `tes_mean20`, `resource_ok`, `policy_ok` fields).
- Keep all persistence local. Do not export artefacts off-station without an approved manifest.
- When reporting via `POST /status`, keep notes concise (under 200 characters) and include remediation hints when available.
- If maintenance prunes queues or metrics, immediately refresh `/report` to confirm counts and TES summaries reflect the new baseline.

## Quick Command Reference
- Start overseer loop: `python -m calyx.cbo.bridge_overseer` (4-minute heartbeat).
- Start API bridge: `python -m calyx.cbo.api` (FastAPI on port 8080).
- Run maintenance: `python tools/cbo_maintenance.py --json` (optional flags `--max-jsonl` / `--max-metrics`); scheduled task `CalyxMaintenance` already executes every 30 minutes.
- Tail dispatcher audit: `Get-Content logs/cbo_dispatch.log -Wait` (PowerShell).
- Full restart: `python tools/cbo_bootstrap.py` (skips services already running).
- Capacity alarm: `python tools/cbo_capacity_alarm.py` (schedule for continuous telemetry alerts).

Stay vigilant, log interventions, and keep the CBO heartbeat uninterrupted so Station Calyx maintains safe, autonomous growth.
