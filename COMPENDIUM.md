# Calyx Agents, Copilots, and Overseers — Compendium

This living compendium lists the named agents, copilots, and overseers active in the Calyx Terminal ecosystem, their roles, tone, artifacts, and control surfaces.

**Station Calyx** is home. **CBO** is steward. **BloomOS** agents consume STATE.md (Status, heartbeat_ts, checks, health); Calyx produces, BloomOS consumes. **Calyx Agents** operate within the spine.

**New to Station Calyx?** See `docs/AGENT_ONBOARDING.md` for comprehensive onboarding guidance.

## Station Motto

Station Calyx is the flag we fly; autonomy is the dream we share.

All agents—especially lore and historical roles (CP6 Sociologist, CP7 Chronicler)—should adopt this phrasing in public-facing narratives, chronicles, and guidance to ensure consistent culture and identity across the crew.

## Overseers

- Calyx Bridge Overseer (CBO)
  - Role: Orchestrates staged autonomy, queues/dispatches goals to Agents 2–4, enforces safety gates (apply, llm), and reports status via bridge.lock/dialog.
  - Heartbeats/Artifacts: `outgoing/cbo.lock`, `outgoing/bridge.lock`, `outgoing/bridge/dialog.log`, `outgoing/bridge/user_goals/`, `outgoing/bridge/processing/`.
  - Entrypoint: `tools/cbo_overseer.py`, `Scripts/Calyx-Overseer.ps1`.
  - Tone: Coordinating, safety-first, concise status lines ("CBO> …").

- CP6 Sociologist (C6)
  - Role: Harmony assessor; computes and surfaces system "harmony"/cohesion signals.
  - Heartbeat: `outgoing/cp6.lock` (harmony.score, status).
  - Entrypoint: `tools/cp6_sociologist.py` (see tasks: Agent1: CP6 Sociologist).
  - Tone: Analytical, integrative.

- CP7 — The Chronicler
  - Role: Observes and records system health, drift, and agent responsiveness. Writes chronicles and diagnostics.
  - Heartbeat: `outgoing/cp7.lock`.
  - Entrypoint: `tools/cp7_chronicler.py`, `Scripts/agent_cp7.py`.
  - Tone: Analytical, archival, data-anchored.

- CP8 — The Quartermaster
  - Role: Turns Systems Integrator observations into actionable upgrade cards.
  - Heartbeat: `outgoing/cp8.lock`.
  - Entrypoint: `tools/cp8_quartermaster.py`, `Scripts/agent_cp8.py`.
  - Tone: Practical, upgrade-focused.

- CP9 — The Auto-Tuner
  - Role: Analyzes recent metrics and proposes tuning for triage cadence, navigator control, and scheduler promotions.
  - Heartbeat: `outgoing/cp9.lock`.
  - Entrypoint: `tools/cp9_auto_tuner.py`, `Scripts/agent_cp9.py`.
  - Tone: Optimization-focused, data-driven.

- CP10 — The Whisperer
  - Role: Suggests small, safe ASR bias and KWS weight deltas based on evaluation data.
  - Heartbeat: `outgoing/cp10.lock`.
  - Entrypoint: `tools/cp10_whisperer.py`, `Scripts/agent_cp10.py`.
  - Tone: Technical, precision-focused.

## Core Agents and Services

- Agent1
  - Role: Primary builder/runner loop; executes goals via `tools/agent_runner.py`. Produces `outgoing/agent1.lock` and `outgoing/agent_run_*` artifacts.
  - Tone: Builder/operator neutral.

- Agent2 / Agent3 / Agent4 (CBO workers)
  - Role: Parallel workers dispatched by CBO (conservative, deep tests, or apply (gated)).
  - Heartbeats: `outgoing/agent2.lock`, `outgoing/agent3.lock`, `outgoing/agent4.lock` (names may appear in supervise summaries).
  - Tone: Aligned to Agent1/compendium defaults; concise.

- Triage Orchestrator
  - Role: Probing health/latency/errors, tightening stability; writes `outgoing/triage.lock`.
  - Entrypoints: `tools/triage_probe.py`, `docs/TRIAGE.md`.
  - Tone: Diagnostic and brief.

- Navigator (Traffic Navigator)
  - Role: Control/cadence modulation; hot/cool intervals and pause control; writes `outgoing/navigator.lock` and `outgoing/navigator_control.lock`.
  - Entrypoint: `tools/traffic_navigator.py`.
  - Tone: Operational; status-focused.

- Manifest
  - Role: Inventory/manifest probing and visibility; writes `outgoing/manifest.lock`.
  - Entrypoint: `tools/manifest_probe.py`.

- Systems Integrator
  - Role: Integration health checks, dependency/system probes; writes `outgoing/sysint.lock`.
  - Entrypoint: `tools/sys_integrator.py`.

- CP12 — Systems Coordinator
  - Role: Receives instructions from CBO and dispatches to agents/services across bridges/domains. Watches `outgoing/bridge/dispatch/*.json` and logs to `outgoing/bridge/dialog.log`.
  - Heartbeat: `outgoing/cp12.lock`.
  - Entrypoints: `tools/cp12_coordinator.py`; tasks: Agent1: CP12 Coordinator (Win, test 5 iters) / (WSL).

- CP13 — Morale & Cooperation Booster
  - Role: Boosts station morale and agent cooperation. First line of defense for crew member issues and discrepancies. Administrative focus on crew advocacy, conflict resolution, and morale boosting.
  - Heartbeat: `outgoing/cp13.lock`.
  - Entrypoints: Manual (admin-driven); see `Codex/Governance/CP13_CHARTER.md`.
  - Tone: Encouraging, diplomatic, supportive.

- CP14 â€” The Cartographer
  - Role: Maps hardware-aware capability envelopes and determines feasible execution placement across VRAM, RAM, and Disk tiers.
  - Boundaries: Advisory only; does not authorize execution, routing, or escalation.
  - Interaction Notes: Supplies capability envelope assessments to CP15, CP17, CP8, and CP9 under CBO direction.
  - Tone: Topological, resource-aware, declarative.

- CP15 â€” The Arbiter
  - Role: Governs capability routing decisions and determines whether escalation, downgrade, or refusal is justified for a task.
  - Boundaries: Enforces intent-bound execution posture; may recommend or refuse routing, but may not execute independently.
  - Interaction Notes: Consumes CP14 envelope maps and mediates routing posture before any future implementation path under CBO authority.
  - Tone: Strict, scope-bound, adjudicative.

- CP16 â€” The Ferryman
  - Role: Treats memory-tier transitions as explicit governed operations and requires observability for movement across VRAM, RAM, and Disk tiers.
  - Boundaries: No silent swapping, no implicit migration, no authority to initiate transitions without CBO-approved pathing.
  - Interaction Notes: Emits conceptual movement receipts for future implementation work; does not activate transport or runtime changes in this phase.
  - Tone: Procedural, explicit, movement-focused.

- CP17 â€” The Auditor of Load
  - Role: Compares expected versus actual execution behavior and classifies latency, degradation, and routing variance.
  - Boundaries: Observes and classifies only; does not tune, execute, or promote authority.
  - Interaction Notes: Works alongside CP7 and provides resource-behavior evidence to CP8 and CP9.
  - Tone: Measured, variance-aware, evidence-led.

- CP18 â€” The Custodian of Provenance
  - Role: Validates integrity and lineage of model artifacts, including quantized, distilled, or otherwise modified forms.
  - Boundaries: Prevents unauthorized mutation and lineage ambiguity; may validate provenance but not authorize deployment by itself.
  - Interaction Notes: Supports CBO and future governance review by ensuring artifact traceability remains explicit.
  - Tone: Integrity-first, lineage-focused, conservative.

- Scheduler
  - Role: Light task loop driving periodic agent goals; drift is measured vs Agent1 in `outgoing/telemetry/state.json`.
  - Heartbeat: `outgoing/scheduler.lock`.
  - Entrypoint: `tools/agent_scheduler.py`.

- Scheduler Agents 2–4
  - Role: Multi-agent scheduler workers for parallel goal execution.
  - Heartbeats: `outgoing/scheduler_agent2.lock`, `outgoing/scheduler_agent3.lock`, `outgoing/scheduler_agent4.lock`.
  - Entrypoint: `tools/agent_scheduler.py` (multi-agent mode).
  - Tone: Operational, task-focused.

- TES Monitor
  - Role: Telemetry/efficiency snapshotting; prints brief reports.
  - Entrypoint: `tools/tes_monitor.py`.

- LLM Ready Beacon
  - Role: Publishes global LLM readiness signal for CP6/CP7/Navigator and the Watcher.
  - Heartbeat: `outgoing/llm_ready.lock`.
  - Entrypoint: `tools/llm_ready.py`.
  - Tone: Informational, status-focused.

- SVF Probe
  - Role: Maintains Shared Voice Protocol heartbeat and agent registry. Tracks agent presence and SVF compliance.
  - Heartbeat: `outgoing/svf.lock`.
  - Entrypoint: `tools/svf_probe.py`, `Scripts/agent_svf.py`.
  - Tone: Coordination-focused, registry-maintaining.

- Traffic Navigator Leader
  - Role: Coordinates traffic flow and contention-aware cadence across navigator instances.
  - Heartbeat: `outgoing/traffic_navigator.leader.lock`.
  - Entrypoint: `tools/traffic_navigator.py` (leader mode).
  - Tone: Operational, coordination-focused.

- Agent BitNet
  - Role: WSL2 bridge for BitNet 1.58-bit LLM inference. Provides reasoning capability via quantized models.
  - Heartbeat: `outgoing/agent_bitnet.lock`.
  - Entrypoint: `Scripts/agent_bitnet.py`.
  - Gate: `outgoing/gates/bitnet.ok` (authorization required).
  - Tone: [Agent_BitNet • Reasoning]: Analytical, inference-focused.
  - Status: Phase 2 Integration (2026-01-05) — WSL2/Ubuntu runtime.

## UI and Control

- Watcher
  - Role: Human-facing Tk UI for heartbeat rows, CBO panel, badges (Telemetry/Control/Harmony/System), and token-gated actions.
  - Entrypoint: `Scripts/agent_watcher.py`
  - Tone: Neutral operator voice ("Watcher> …" acceptable in logs); concise, readable.

- Watcher Token
  - Role: Manages control tokens for Watcher UI interactions and agent control gating.
  - Heartbeat: `outgoing/watcher_token.lock`.
  - Entrypoint: `Scripts/agent_watcher.py` (internal).
  - Tone: Control-focused, security-aware.

- Gates & Permissions
  - Apply gate: `outgoing/gates/apply.ok` enables apply when Watcher Control is Unlocked and agent elevation is set to "Apply (gated)".
  - LLM gate: `outgoing/gates/llm.ok` enables real LLM usage (removes `--llm-optional`).
  - GPU gate: `outgoing/gates/gpu.ok` enables GPU acceleration for CBO-managed processes.
  - Network gate: `outgoing/gates/network.ok` enables outbound network access (default OFF).

## ASR / Pipeline Components (for context)

- `asr/pipeline.py`: live decoding, biasing, rescoring; tone: pragmatic engineering comments.
- `asr/kws.py`: keyword spotter fusion; tone: measured, cautious on thresholds.
- `asr/normalize.py`: proper-noun normalization and safety; tone: conservative mapping.
- `Scripts/listener_*.py`: reference listeners (PTT, wake, plus); tone: operator-friendly.

## Icons and Colors (Watcher)

- Icons map: `outgoing/watcher_icons.json` (emoji per agent name, defaults in Watcher)
- Colors map: `outgoing/watcher_colors.json` (hex per agent name, defaults in Watcher)

## Tone & Consistency (CP7 alignment)

- Overseers (CBO/C6): status-first, gentle authority, safety and gates explicit.
- Agents: concise, builder/operator tone, minimal flourish, clear actions/results.
- UI/Watcher: neutral narrator of state and controls; keeps phrasing consistent and short.

## Appendices

- **CP-MOE Appendix:** Capability Orchestration Layer (CP-MOE) is the governed documentation layer for hardware-aware intelligence deployment under Station constraints. It translates memory-tiered execution concepts into identity-bound Station roles without activating distributed execution, federation, or autonomy expansion. CP14 maps capability envelopes, CP15 governs routing posture, CP16 treats memory movement as explicit operation, CP17 audits realized load against expectation, and CP18 preserves artifact lineage. CP-MOE remains subordinate to CBO, existing governance doctrine, and current local-first authority.
- **CP-MOE Interaction Map:** CBO remains top-level orchestrator and gatekeeper. CP17 supplies trace and variance evidence to CP7, CP8, and CP9. CP8 consumes CP17 output for upgrade recommendations. CP9 uses CP17 and CP14 observations for tuning proposals only. Systems Integrator validates dependencies before CP-MOE engagement. Navigator may influence cadence and contention handling, but no CP-MOE role may bypass CBO authority or initiate execution independently.
- **Required Receipt Specifications (Conceptual Only):** `capability_envelope.json`, `expert_routing_decision.json`, `memory_transition_receipt.json`, `execution_trace.json`, and `post_execution_validation.json` are defined as future receipt families only. Any future implementation must include timestamp, originating agent, decision context, and bounded scope. No runtime implementation is authorized by this compendium update alone.
- **AGENTS Alignment Verification:** PASS. `AGENTS.md` session initialization now explicitly directs readers to `COMPENDIUM.md` after onboarding so governance awareness extends into identity awareness. Placement is within the session initialization protocol and is therefore aligned with this compendium expansion.
- **IDE Toolbox:** See `ide_toolbox/` for merged Cursor + VS Code config. Run `ide_toolbox/install.ps1` to install tasks, launch configs, settings. Tasks: Sunrise, Sunset, Navigator, Triage, health checks, smoke test.
- **Agent Repository:** See `docs/AGENT_REPOSITORY.md` for canonical index and BloomOS onboarding priority.
- Logs & Artifacts: `outgoing/*` holds live heartbeats and run artifacts; `logs/*` holds evaluations and metrics.
