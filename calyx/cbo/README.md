# Station Calyx Bridge Overseer

This package contains the Central Bridge Overseer (CBO) runtime responsible for orchestrating Station Calyx operations in 4-minute pulses.

## Quick Start
- Review the mission charter in `calyx/cbo/CBO_CHARTER.md` for scope, constraints, and roadmap. The overseer refuses to run without it being deployed.
- Ensure policy and registry artefacts exist under `calyx/core/` (`policy.yaml`, `registry.jsonl`). Sample defaults ship with this repo.
- Drop manual objectives into `runtime/cbo/objectives.jsonl` (one JSON object per line; path controlled by `CALYX_RUNTIME_DIR`, default `runtime`). Example:

```json
{"objective_id": "obj-001", "description": "Sync scheduler status dashboard", "priority": 3, "metadata": {"skills": ["scheduler", "status-report"]}}
```

- Start the heartbeat loop: `python -m calyx.cbo.bridge_overseer`. It will run until interrupted, executing Reflect -> Plan -> Act -> Critique every 240 seconds.
- Metrics append to `metrics/bridge_pulse.csv`; dispatcher audit trail writes to `logs/cbo_dispatch.log`; queued tasks land in `runtime/cbo/task_queue.jsonl`.

## Module Overview
- `bridge_overseer.py`: main heartbeat loop linking sensors, planner, dispatcher, feedback, and governance modules.
- `sensors.py`: gathers policy, registry, and recent metrics snapshots.
- `plan_engine.py`: converts objectives into task objects with provisional assignees.
- `dispatch.py`: writes tasks to a JSONL queue for registered agents to poll.
- `feedback.py`: tallies execution outcomes, TES trends, and policy compliance.
- `models.py`: shared dataclasses for objectives, tasks, and pulse reports.
- `api.py`: FastAPI service exposing `/objective`, `/status`, `/heartbeat`, `/policy`, and `/report`.
- `tes_analyzer.py`: parses `logs/agent_metrics.csv` and computes TES trends for the feedback loop.
- `governance.py`: enforces policy/resource constraints before tasks are dispatched.
- `maintenance.py`: archival and pruning helpers to keep JSONL/CSV artefacts healthy.
- `tools/cbo_maintenance.py`: CLI wrapper that runs the maintenance cycle (now scheduled every 30 minutes as `CalyxMaintenance`).
- `tools/cbo_bootstrap.py`: brings the overseer, API, schedulers, and mentors online in a known-good order.
- `tools/cbo_capacity_alarm.py`: polls `/report` and logs alerts when CPU/RAM caps or TES trends drift.

## Next Steps
1. Extend the dispatcher to integrate directly with agent endpoints or ZeroMQ queues for live routing.
2. Introduce meta-planning for multi-task objective decomposition and dependency management.
3. Add self-healing behaviours that adjust heartbeat cadence when resource pressure persists.

## API Bridge
- Start the service with `python -m calyx.cbo.api` (defaults to port 8080).
- `POST /objective`: enqueues a new objective (fields: `description`, optional `priority`, `metadata`, `objective_id`).
- `POST /status`: agents report task progress (`task_id`, `status`, optional `agent_id`, `notes`).
- `POST /claim`: returns the next unclaimed task and marks it `in_progress` (optional `agent_id` body field).
- `GET /policy`: returns the active policy document used for governance checks.
- `GET /report`: summarizes queue depth, objectives waiting, latest metrics, and recent status updates.
- `GET /heartbeat`: simple health probe confirming charter presence and returning current UTC timestamp.

## Agent Workflow
- Claim work: `POST /claim` with your `agent_id`; the response payload contains the task JSON (action, payload, identifiers).
- Execute the task and call `POST /status` with the updated `status` enum (`in_progress`, `completed`, `failed`, etc.), plus any notes or structured payload needed for audit.
- The dispatcher logs every transition to `runtime/cbo/task_status.jsonl`; the queue (`runtime/cbo/task_queue.jsonl`) always reflects the latest state per task.
- Coordinators can monitor overall status via `GET /report` or by tailing `logs/cbo_dispatch.log` for audit entries.
- TES health and policy compliance appear in both `/report` and `metrics/bridge_pulse.csv` (`tes_mean20`, `resource_ok`, `policy_ok`).

## Maintenance & Governance Cycle
- Run `python -m tools.cbo_maintenance` (or `python tools/cbo_maintenance.py`) to prune queue/status/metrics files, archive snapshots to `logs/archive/`, and vacuum `runtime/cbo/memory.sqlite`.
- A scheduled task (`CalyxMaintenance`) is configured to run the CLI every 30 minutes; adjust via `schtasks` if cadence changes.
- Governance limits (`max_cpu_pct`, `max_ram_pct`, `allow_unregistered_agents`) live in `calyx/core/policy.yaml`. Adjust them before restarting the overseer; the maintenance script does not override policy files.
- After maintenance, restart the overseer (`python -m calyx.cbo.bridge_overseer`) and API service to ensure fresh state is observed, or run `python tools/cbo_bootstrap.py` to launch the full stack.
- Use `python tools/cbo_capacity_alarm.py` (schedule as desired) to log capacity alerts in `logs/capacity_alerts.jsonl`.
- Governance limits (`max_cpu_pct`, `max_ram_pct`, `allow_unregistered_agents`) live in `calyx/core/policy.yaml`. Adjust them before restarting the overseer; the maintenance script does not override policy files.
- After maintenance, restart the overseer (`python -m calyx.cbo.bridge_overseer`) and API service to ensure fresh state is observed.
