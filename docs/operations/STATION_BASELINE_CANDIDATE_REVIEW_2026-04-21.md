---
status: active
owner: station
last_reviewed_utc: "2026-04-21"
doctrine_scope: governed
---

# STATION_BASELINE_CANDIDATE_REVIEW_2026-04-21

## Purpose

This review narrows the first baseline commit candidate to a defensible subset of source-bearing changes.

The goal is not to absorb the entire worktree. The goal is to define the smallest baseline that truthfully represents the current canonical Station substrate and its active governance posture.

## Baseline Philosophy

The first baseline commit should include only:

- changes required to represent the current canonical Station runtime substrate
- governance and lifecycle work that is now load-bearing
- integration surfaces intentionally retained in active scope

If a source-bearing change is valid but not necessary to describe the current canonical substrate, it should be deferred.

## Candidate Review

### `Scripts/`

**baseline_now**

- `Scripts/start_calyx_core_services.ps1`
- `Scripts/station_health_loop.ps1`
- `Scripts/sunrise_calyx.ps1`
- `Scripts/sunset_calyx.ps1`
- `Scripts/update_state_checks.ps1`
- `Scripts/cp6_cp7_loop.ps1`
- `Scripts/energy_churn_cp9_loop.ps1`
- `Scripts/navigator.ps1`
- `Scripts/navigator_triage_loop.ps1`
- `Scripts/triage_orchestrator.ps1`
- `Scripts/runtime_topology_snapshot.py`
- `Scripts/runtime_truth_contract.ps1`
- `Scripts/restart_service.ps1`
- `Scripts/service_failure_watch.ps1`
- `Scripts/station_health_check.ps1`
- `Scripts/start_station_governed.ps1`
- `Scripts/station_patch_sunrise.ps1`

Reason: these are directly involved in current runtime truth, canonical startup/shutdown, topology emission, reconciliation, health validation, or the currently active loop families.

**valid_but_defer**

- `Scripts/add_doc_status_headers.py`
- `Scripts/audit_anomalies.py`
- `Scripts/audit_trace.py`
- `Scripts/build_safety_check.ps1`
- `Scripts/canonical_parity_check.py`
- `Scripts/carbon_intensity.ps1`
- `Scripts/correlation_log.ps1`
- `Scripts/discord_canonical_transport_declaration_v1.py`
- `Scripts/discord_canonical_transport_recheck_v1.py`
- `Scripts/emit_heartbeat_tick.py`
- `Scripts/generate_daily_24h_review.py`
- `Scripts/generate_sample_ledger.py`
- `Scripts/governance_budget_coverage_check.py`
- `Scripts/governance_budget_coverage_ladder.py`
- `Scripts/install_daily_24h_review_task.ps1`
- `Scripts/ledger_tail.py`
- `Scripts/patch_readiness.ps1`
- `Scripts/run_daily_24h_review_cycle.ps1`
- `Scripts/service_failure_contract.ps1`
- `Scripts/set_ollama_affinity.ps1`
- `Scripts/start_minimal.ps1`
- `Scripts/start_station_health_loop.ps1`
- `Scripts/start_telemetry_gateway.ps1`
- `Scripts/telemetry_hardening_pass_v1.ps1`
- `Scripts/update_contract_hash.py`
- `Scripts/wo_*`

Reason: valid operational tooling, but not required to define the first canonical runtime baseline.

**needs_operator_decision**

- `Scripts/setup_openclaw_calyx.ps1`
- `Scripts/openclaw_cli_invoke_determinism_v1.py`
- `Scripts/openclaw_preflight.ps1`
- `Scripts/openclaw_presence_interface_validation.py`
- `Scripts/openclaw_wiring_freeze_validation.py`
- `Scripts/prompt_calyx_sign.ps1`
- `Scripts/request_calyx_sign.ps1`
- `Scripts/calyx_sign_request.py`

Reason: these touch retained external integration posture or additional operator workflows that are not strictly necessary for the first baseline.

### `calyx/`

**baseline_now**

- `calyx/cbo/discord_gateway.py`
- `calyx/cbo/intent_pipeline/plan.py`
- `calyx/execution/hub_runner.py`
- `calyx/kernel/contract.py`
- `calyx/kernel/envelope.py`
- `calyx/kernel/paths.py`
- `calyx/kernel/receipts.py`
- `calyx/governance/runtime_topology.py`
- `calyx/kernel/swarm_work_envelope.py`
- `calyx/kernel/swarm_lease.py`
- `calyx/kernel/swarm_trace.py`
- `calyx/kernel/swarm_sandbox.py`

Reason: these are the implemented governance substrate pieces that now define active runtime truth or the bounded swarm substrate.

**valid_but_defer**

- `calyx/cbo/api.py`
- `calyx/cbo/discord_intake.py`
- `calyx/cbo/discord_response.py`
- `calyx/cbo/home_node_executor.py`
- `calyx/cbo/intent_pipeline/__init__.py`
- `calyx/cbo/intent_pipeline/clarify.py`
- `calyx/cbo/intent_pipeline/ingest.py`
- `calyx/cbo/intent_pipeline/registry.py`
- `calyx/cbo/intent_pipeline/intake_card.py`
- `calyx/cbo/intent_pipeline/routing_proof.py`
- `calyx/kernel/canonical_*`
- `calyx/kernel/correlation_log.py`
- `calyx/kernel/critique_checkpoint.py`
- `calyx/kernel/event_ledger.py`
- `calyx/kernel/failure_*`
- `calyx/kernel/governance_budget.py`
- `calyx/kernel/intent_orientation.py`
- `calyx/kernel/ledger_*`
- `calyx/kernel/nonce_ledger.py`
- `calyx/kernel/pocket_contract.py`
- `calyx/kernel/routing_proof.py`
- `calyx/kernel/transport_comparator.py`
- `calyx/kernel/verified_claims.py`
- `calyx/governance/approvals.py`
- `calyx/governance/proposals.py`
- `calyx/governance/receipts.py`
- `calyx/governance/reconciliation.py`
- `calyx/governance/state_model.py`

Reason: valid governance and intake stack work, but not all of it is required for the first baseline commit.

**needs_operator_decision**

- `calyx/kernel/openclaw_intake_guard.py`
- `calyx/governance/execution_gate.py`

Reason: these sit close to external capability posture and future execution gating.

### `cbo_hub/`

**baseline_now**

- `cbo_hub/cbo_core/app.py`
- `cbo_hub/cbo_core/stamping.py`
- `cbo_hub/dev_harness/app.py`
- `cbo_hub/telemetry_gateway/app.py`
- `cbo_hub/telemetry_gateway/__init__.py`
- `cbo_hub/telemetry_gateway/__main__.py`
- `cbo_hub/cli_avatar/main.py`
- `cbo_hub/avatar_web/__init__.py`
- `cbo_hub/avatar_web/app.py`

Reason: these are current live service surfaces or direct service support code.

**valid_but_defer**

- `cbo_hub/avatar_web/workspace_v0.html`
- `cbo_hub/avatar_web/workspace_v0.py`
- `cbo_hub/docs/USAGE_AND_HEALTH.md`
- `cbo_hub/docs/CALYX_CORE_SERVICES.md`

Reason: useful, but not required to define the first substrate baseline.

**needs_operator_decision**

- none beyond the general exclusion of `cbo_hub/data/` local workspace state

### `docs/`

**baseline_now**

- `docs/public_repo_denylist.md`
- `docs/DOC_STATUS_REGISTRY.json`
- `docs/OPENCLAW_CALYX_INTEGRATION.md`
- `docs/operations/CANONICAL_OPS_INDEX.md`
- `docs/operations/STATION_INTERRUPTION_AND_RECOVERY_MODEL.md`
- `docs/operations/STATION_EXTERNAL_CAPABILITY_DECLARATION_2026-04-17.md`
- `docs/planning/WO_ACTIVE_AUTHORITY_CONTEXT_AND_THREAD_DEMOTION_V1.md`
- `docs/planning/WO_RUNTIME_OPERATOR_EXPLICIT_IDENTITY_DISCLOSURE_V1.md`
- `docs/planning/WO_SWARM_EXECUTION_ENVELOPE_AND_WORKER_LEASES_V1.md`
- `docs/planning/WO_SANDBOXED_WORKER_RUNTIME_V1.md`
- `docs/planning/WO_SWARM_TRACE_GRAPH_AND_RECEIPT_BUNDLE_V1.md`
- `docs/planning/WO_OPENCLAW_REINTEGRATION_PATH_V1.md`

Reason: these documents describe active doctrine, active authority, active runtime truth, or the implemented swarm substrate.

**valid_but_defer**

- onboarding and reference docs:
  - `docs/AGENT_ONBOARDING.md`
  - `docs/AGENT_ONBOARDING_SVF_v2.md`
  - `docs/CBO_AGENT_ONBOARDING.md`
  - `docs/COPILOTS.md`
  - `docs/INDEX.md`
  - `docs/QUICK_REFERENCE.md`
- evidence and audit outputs:
  - `docs/operations/STATION_EXTERNAL_CAPABILITY_SURFACE_AUDIT_2026-04-17.md`
  - `docs/operations/STATION_INTEGRITY_AUDIT_2026-04-15.md`
  - `docs/operations/STATION_POWER_LOSS_INCIDENT_2026-04-18.md`
  - `docs/operations/STATION_REPO_INTEGRITY_AUDIT_2026-04-21.md`
  - `docs/operations/STATION_REPO_BASELINE_CLASSIFICATION_2026-04-21.md`
  - `docs/operations/STATION_REPO_BASELINE_READINESS_2026-04-21.md`
  - `docs/operations/STATION_SCCFA_ASSESSMENT_2026-04-15.md`
- broader planning set not required for first baseline

Reason: valid and useful, but not all of it needs to be in the first canonical consolidation point.

**needs_operator_decision**

- `docs/COMPENDIUM.md` deletion finalization

Reason: the authority move is decided, but the Git-normalized transition must still be explicitly included in the first baseline commit.

### `tests/`

**baseline_now**

- `tests/test_discord_ids_resolution.py`
- `tests/test_runtime_topology_visibility.py`
- `tests/test_runtime_reconciliation.py`
- `tests/test_station_interruption_governance.py`
- `tests/test_swarm_work_envelope.py`
- `tests/test_worker_lease_validation.py`
- `tests/test_swarm_trace_graph.py`
- `tests/test_swarm_sandbox.py`
- `tests/test_swarm_hub_runner_staging.py`

Reason: these validate the load-bearing runtime and swarm substrate work that baseline-now includes.

**valid_but_defer**

- governance suite:
  - `tests/governance/*`
- intake/routing/critique suites:
  - `tests/test_contract_intake_parity.py`
  - `tests/test_critique_checkpoint_phase3.py`
  - `tests/test_intake_card_phase1.py`
  - `tests/test_routing_proof_phase2.py`
- market/weather/workspace suites:
  - `tests/test_kalshi_*`
  - `tests/test_weather_*`
  - `tests/test_workspace_*`
- `tests/test_benchmark_harness.py`

Reason: valid tests, but outside the minimal first baseline.

**needs_operator_decision**

- none

### `tools/`

**baseline_now**

- `tools/cp6_sociologist.py`
- `tools/cp7_chronicler.py`
- `tools/cp9_auto_tuner.py`
- `tools/runtime_truth.py`

Reason: these are directly used by active loop families or truth/governance surfaces.

**valid_but_defer**

- `tools/calyx_guardian/*`

Reason: valid tooling, not required for first baseline.

**needs_operator_decision**

- `tools/calyx_sign.ps1`

Reason: separate operator workflow, not required for the first canonical substrate commit.

### `governance/`

**baseline_now**

- none

**valid_but_defer**

- `governance/COMPETITOR_CLAUSE.md`
- `governance/EVIDENCE_LEDGER.md`
- `governance/TRIPWIRE_ENGINE.md`

Reason: legitimate governance material, but not necessary for the smallest first baseline set.

**needs_operator_decision**

- none

### `policy/`

**baseline_now**

- none

**valid_but_defer**

- `policy/__init__.py`
- `policy/boot_context_budget.json`
- `policy/competitor_clause.yaml`
- `policy/intake_classification.json`
- `policy/openclaw_intake_policy.json`
- `policy/service_failure_registry.json`
- `policy/tripwire_levels.yaml`
- `policy/validator.py`

Reason: valid policy substrate, but not required to represent the current canonical runtime and baseline-now code path.

**needs_operator_decision**

- none

### Preserved OpenClaw integration surfaces

**baseline_now**

- `skills/calyx-cbo-bridge/README.md`
- `skills/calyx-cbo-bridge/index.js`
- `skills/calyx-cbo-bridge/manifest.json`
- `skills/calyx-cbo-bridge/package.json`
- `openclaw/extensions/calyx-governance/index.ts`
- `openclaw/extensions/calyx-governance/openclaw.plugin.json`

Reason: these most directly represent the intentionally retained Calyx/OpenClaw bridge and governance boundary.

**valid_but_defer**

- `openclaw/completions/*`
- `openclaw/canvas/*`
- `openclaw/cron/jobs*.json*`
- `openclaw/openclaw.json*`
- `openclaw/subagents/runs.json`
- `openclaw/update-check*.json`
- `openclaw/agents/main/agent/models.json`

Reason: part of the broader OpenClaw dependency surface, but not essential to the first baseline’s boundary representation.

**needs_operator_decision**

- `openclaw/gateway.cmd`
- `openclaw/calyx/openclaw/calyx-profile.json`
- tracked deletion of `openclaw/calyx-profile.json`

Reason: these are the sharpest boundary between “retained integration surface” and “historical configuration artifact.”

## Narrowed First Baseline Candidate

If compressed aggressively, the first baseline candidate should contain:

1. runtime truth / reconciliation / lifecycle scripts and their supporting loop scripts
2. `calyx` governance/runtime/swarm substrate that is already integrated
3. current live `cbo_hub` service code
4. the minimum doctrine and planning docs that describe the implemented substrate
5. tests for those exact surfaces
6. the minimum OpenClaw bridge/governance integration source needed to represent retained dependency posture
7. the root `COMPENDIUM.md` plus the deletion of `docs/COMPENDIUM.md`

## Recommendation

The next pass should be a **baseline commit selection pass**, not another broad audit.

That pass should take only the `baseline_now` set, verify it builds/tests coherently, and then surface only the remaining `needs_operator_decision` items for approval.
