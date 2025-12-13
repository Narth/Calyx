## Station Calyx Coordinator (Design Draft)

### 1. Intent
Give Station Calyx an always-on executive layer that fuses telemetry, tracks shared state, arbitrates intent, and dispatches actions with confidence-aware guardrails. The coordinator fronts existing loops (Agent1, supervisors, schedulers) and provides the "cortex" the CBO will inhabit to push from semi-autonomous toward guided autonomy.

### 2. Problem Statement
- Current orchestration is reactive; probes and schedulers act on local signals without a unified source of truth.
- No durable task queue exists with prioritisation, risk scoring, or lifecycle management that the CBO can steer.
- Feedback loops are fragmented: telemetry -> intent -> execution -> validation -> memory is not owned end-to-end.
- Human escalation is ad hoc. We need a predictable cockpit with autonomy envelopes the CBO can trust.

### 3. Goals
- Maintain a shared operational picture (state, backlog, health, autonomy mode).
- Score and prioritise intents from humans, sensors, and agents with explicit policy and risk context.
- Select execution paths and autonomy levels based on capability, confidence, and resource headroom.
- Enforce guardrails, trigger downgrades, and request human intervention when thresholds are violated.
- Persist context (decisions, rationales, outcomes) for learning, audit, and future policy tuning.
- Expose a CLI interface the CBO can operate without waiting on UI work.

### 4. Non-Goals (initial cut)
- Rewriting existing schedulers or supervisors; coordinator orchestrates them.
- Building graphical interfaces; structured CLI/JSON output is sufficient for v1.
- Training or tuning LLMs; coordinator consumes whichever models and policies are enabled.

### 5. System Context

```
Sensors / Probes / Humans --> Coordinator (Executive Core) --> Agents / Scripts / Schedulers
Existing Logs / Metrics --/                                     ^ 
                                                                \-- Status, results, guardrail signals
```

Key actors today:
- **CBO Overseer** (`tools/cbo_overseer.py`): boots loops, maintains gates, writes CBO heartbeat.
- **Adaptive Supervisor & Probes** (`tools/svc_supervisor*.py`, `tools/svf_probe.py`, `tools/triage_probe.py`): keep core services alive, track resources.
- **Agent1 + Light Task Scheduler**: executes micro-goals, records TES metrics.
- **Artifacts**: logs under `logs/`, shared state under `outgoing/`, configuration in `config.yaml`.

The coordinator ingests from these actors rather than replacing them.

### 6. High-Level Architecture

1. **Telemetry Intake Layer**
   - Streams events from probes, schedulers, Agent1 runs, resource monitors, and manual inputs.
   - Normalises everything to a versioned event envelope (see Section 8).
   - Sources: file watchers on `outgoing/*.lock` and `logs/*.csv`, direct Python publishers, CLI submissions.
   - Applies lossy sampling when CPU > 75% to avoid starving the system.

2. **State Core (Shared World Model)**
   - Maintains snapshot state (resource headroom, gates, agent status), intent ledger, and derived facts (TES rolling averages, failure streaks).
   - Backed by an append-only event log (SQLite or structured JSON) in `state/coordinator/`.
   - Exposes query APIs (`coordinator/state/read`) for consoles and probes.

3. **Intent Pipeline**
   - Accepts candidate intents from humans, probes, playbooks, or coordinator-generated maintenance.
   - Uses the intent schema in Section 8, including risk fields and deduplication rules.
   - Prioritiser scores intents using policy hints, risk, freshness, and resource posture.
   - Validation hooks ensure prerequisites (GPU gate, headroom, policy) are satisfied before queuing.

4. **Policy & Autonomy Engine**
   - Reads `config.yaml`, `outgoing/policies/cbo_permissions.json`, and guardrails in Section 7.
   - Computes confidence per agent based on the rolling 12-pulse TES, historical outcomes, and similarity to past intents.
   - Decides autonomy mode (`manual`, `suggest`, `guide`, `execute`) and enforces downgrades/upgrades.
   - Integrates with the cockpit CLI to request human approval when thresholds are breached.

5. **Execution Orchestrator**
  - Converts approved intents into run manifests.
  - Single source of truth: writes `outgoing/coordinator/<intent-id>/manifest.json` plus `manifest.lock`.
  - Schedulers/agents treat the manifest hash as `task_id`; duplicates within 4 pulses are ignored.
  - Dispatches to Agent1, direct scripts, or supervisor hooks depending on capability and autonomy mode.
  - Tracks lifecycle `scheduled -> running -> verifying -> closed` in the ledger.

6. **Verification & Learning Loop**
  - Monitors completion telemetry (TES logs, watcher output, probe heartbeats).
  - Evaluates success criteria per domain (see Section 11) and triggers rollback or follow-up intents.
  - Updates confidence weights and autonomy eligibility; caps reward updates unless N >= 5 samples.
  - Emits digests to `Codex/Journal` or `outgoing/reports/` for audit.

7. **Interfaces & Cockpit**
  - CLI-first toolset (`coordinatorctl`).
  - Core commands: `status`, `submit`, `approve`, `reject`, `override`, `intent log`, `risk digest`.
  - Outputs structured JSON frames consumable by Codex/Cursor and watcher UI.

### 7. Guardrails & Policy Defaults
- **Autonomy ladder levels**:
  1. `observe`: aggregate only.
  2. `suggest`: draft plan; human approval required for planning and execution.
  3. `guide`: plan and dispatch after acknowledgement.
  4. `execute`: autonomous within whitelisted domains (see Section 11).
  5. `expeditionary`: reserved for future full autonomy with audits.
- **Downgrade triggers (from guide or execute)**:
  - Rolling 12-pulse TES for the target agent < 92.
  - Three or more consecutive verification failures (any domain).
  - Resource headroom critical for two pulses (CPU > 80% or RAM > 80%).
- **Auto-upgrade back to guide**:
  - Eight clean pulses (TES >= 95, no headroom alerts, no verification failures).
- **Rate limits (per pulse)**:
  - New intents accepted <= 5.
  - Parallel active intents <= 2 (single-PC comfort zone).
- **Execution escalation**:
  - If an intent remains `running` longer than 15 minutes without heartbeat, mark `stalled`, notify cockpit, and await human decision.

### 8. Data Schemas (Cursor/Codex contract)

**Event Envelope (version "e1")**
```json
{
  "timestamp": "2025-10-23T12:34:56Z",
  "source": "agent_scheduler",
  "category": "status|metric|alert|completion",
  "payload": { "task_id": "t-9213", "tes": 97, "duration_ms": 90321 },
  "confidence": 0.92,
  "version": "e1"
}
```
- Categories map to routing rules: `metric` updates TES/headroom, `status` updates lifecycle, `alert` triggers intent creation, `completion` finalises verification.
- Optional keys (`correlation_id`, `labels`) may be added with backward-compatible defaults.

**Intent Object (version "i1")**
```json
{
  "id": "i-3041",
  "origin": "CBO|human|probe|playbook",
  "description": "Rebuild critic schema with relaxed strictness",
  "required_capabilities": ["prompting", "schema-gen"],
  "desired_outcome": "valid JSON schema passes parser",
  "priority_hint": 60,
  "expiry": "2025-10-24T00:00:00Z",
  "autonomy_required": "guide",
  "risk": { "impact": 2, "likelihood": 2, "score": 4 },
  "similar_to": ["i-2878", "i-2910"],
  "version": "i1"
}
```
- Scoring: `priority = priority_hint + 10*impact + 5*likelihood + freshness_boost(expiry)`.
- Freshness boost: decays linearly to 0 as expiry approaches; negative when overdue.
- Deduplication: identical `description` + `required_capabilities` observed within four pulses merge into one intent with aggregated provenance.
- Task ID: stable hash of `id + version + desired_outcome`; used for manifest de-duplication.

### 9. Data Flow
1. Event arrives (probe heartbeat, human request, TES log entry).
2. Telemetry Intake validates against version e1, normalises, and appends to the ledger.
3. Intent Pipeline scores and deduplicates new intents or updates existing ones.
4. Policy Engine evaluates guardrails and autonomy eligibility; if constraints fail, pushes a cockpit approval request.
5. Execution Orchestrator writes manifest plus lock, notifies the relevant executor, and records `scheduled`.
6. Executor claims the manifest (edge-triggered scheduler) and runs the work.
7. Completion telemetry updates status; Verification applies success or rollback logic.
8. State Core refreshes snapshots; Interface publishes new CLI status frame and any required alerts.

### 10. Integration Points & Scheduler Coordination
- **Probes & Supervisors**: add thin `CoordinatorClient.publish(event)` wrappers; adopt atomic file writes (`tmp` plus rename) to avoid SVF race conditions.
- **Agent Scheduler**:
  - Operates in edge-triggered mode; only runs manifests with a fresh hash.
  - Maintains `manifest.claimed` to prevent double-dispatch; duplicates ignored for N pulses.
  - Reports completion or failure via event envelope (`category: completion`).
- **Agent1 Console**: accepts manifest path; emits structured completion payload with TES, duration, changed files.
- **CBO Overseer**: starts the coordinator process, monitors `outgoing/coordinator.lock`, forwards policy updates, and restarts on heartbeat loss.
- **Logs & Metrics**: coordinator consumes existing CSVs; no format changes required.

### 11. Autonomous Domains (Day 1 Whitelist)
- **Rotate logs / compact SQLite**
  - Success: file count reduced and `metrics/size.csv` reflects decrease.
  - Rollback: none (idempotent); escalate on failure.
- **Generate hourly metrics summary**
  - Success: valid JSON posted to Journal with checksum.
  - Rollback: re-run with reduced batch size; flag if second attempt fails.
- **Rebuild memory embeddings**
  - Preconditions: CPU <= 70%.
  - Success: `memory.version` incremented and sample retrieval passes probe test.
  - Rollback: restore `memory.sqlite.bak`, log alert.
- **Validate JSON/CSV schemas (`logs/`, `metrics/`)**
  - Success: zero validation errors.
  - Rollback: open new repair intent in `suggest` mode with diagnostics attached.
- **Restart crashed probe or agent (single retry)**
  - Success: heartbeat observed within 30 seconds.
  - Rollback: quarantine process, raise human alert after two failed restarts (exponential backoff).

### 12. Risks & Mitigations
- **SVF race conditions** -> enforce `.lock` files and atomic renames for manifests.
- **Feedback loops rewarding bad behaviour** -> cap reward updates; require at least five samples before raising autonomy levels.
- **Silent metric backlog** -> switch intake to lossy sampling when CPU > 75% and backfill summaries later.
- **Human fatigue** -> batch low-priority intents into a digest every four pulses; cockpit surfaces summary not stream.

### 13. Operational Considerations
- **Process model**: Python service (Windows-first, optional WSL). Supervisable by CBO Overseer.
- **Storage**: append-only logs with periodic compaction tasks; recover ledger into state on restart.
- **Security**: respect policy files and guardrails; no action without gates open.
- **Observability**: heartbeat frame includes autonomy level, active intents, guardrail status, and last decision summary.
- **CLI-first**: deliver `coordinatorctl` early; HTTP or TUI deferred.

### 14. Implementation Phases
1. **Phase 0 - Instrumentation**
   - Ship event schema e1; attach passive listeners to logs and locks.
   - Produce CLI `coordinatorctl status --watch` that is read-only.
2. **Phase 1 - Intent Ledger**
   - Implement Intake plus State Core plus CLI submission path.
   - Support manual intent submission and cockpit approvals; no auto dispatch yet.
3. **Phase 2 - Assisted Execution**
   - Wire Execution Orchestrator to Agent1 in `suggest` and `guide` modes with manifest ownership.
   - Add verification loop and guardrail enforcement (downgrades, escalations).
4. **Phase 3 - Autonomous Domains**
   - Enable Day-1 whitelist tasks with success and rollback checks.
   - Ensure scheduler edge-triggering prevents duplicate dispatch.
5. **Phase 4 - Learning & Optimisation**
   - Feed TES trends and resource signals into adaptive policies and teaching cadence.
   - Integrate coordinator insights with CBO optimizer hints when enabled.

### 15. Next Steps
1. Finalise JSON schemas (`state/coordinator/events.schema.json`, `state/coordinator/intents.schema.json`) with samples.
2. Prototype Phase 0 collector plus CLI status to validate pulse cadence and guardrail monitoring.
3. Align with CBO crew on cockpit workflows (approval prompts, digest cadence).
4. Define manifest hash function and locking pattern shared between coordinator and scheduler.
5. Catalogue required probe and scheduler publishers and instrument them with the e1 envelope.
