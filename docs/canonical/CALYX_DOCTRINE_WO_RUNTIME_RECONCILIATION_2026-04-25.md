# Calyx Doctrine, Work Order, And Runtime Reconciliation

Status: canonical support audit
Date: 2026-04-25
Scope: Station Calyx doctrine, documentation, Work Orders, directives, runtime truth surfaces, receipts, and current control path

This audit reconciles what Station Calyx says it is against what the current runtime actually exercises.

The finding is direct: Station Calyx has a real active workstation core, but the documentation and Work Order layer still contains accumulated intent, historical capability claims, planning artifacts, and overbroad `active` labels. The active runtime is narrower and healthier than the total doctrine corpus implies.

## Evidence Boundaries

Evidence used:

- `STATE.md`
- `runtime/clarity_status.json`
- `runtime/service_runtime_snapshot.json`
- `runtime/runtime_topology_snapshot.json`
- `runtime/service_failure_status.json`
- `runtime/receipts/sunrise_receipt__20260425_160701.json`
- `docs/canonical/CALYX_CANONICAL_SYSTEM_MAP.md`
- `docs/canonical/CALYX_CORE_CLASSIFICATION_REGISTRY.md`
- `docs/canonical/CALYX_AUTHORITY_RESOLUTION_REGISTRY.md`
- `docs/canonical/CALYX_DOCUMENT_STATUS_REGISTRY.md`
- `docs/canonical/CALYX_NONCANONICAL_ENFORCEMENT_REGISTRY.md`
- `docs/DOC_STATUS_REGISTRY.json`
- `docs/operations/CANONICAL_OPS_INDEX.md`
- `docs/operations/STATION_CALYX_OPERATIONAL_DOCTRINE.md`
- code references under `Scripts/`, `calyx/`, `cbo_hub/`, and `tests/`

Current inspection counts:

- Markdown docs under `docs/`: 293
- Planning WOs under `docs/planning`: 41
- WO validation/ladder docs under `docs/operations`: 13
- Canonical markdown docs under `docs/canonical`: 12
- Governance receipts under `runtime/receipts/governance`: 47
- Audit receipts under `runtime/receipts/audit`: 1213

## Current Runtime Truth

Observed after `Scripts/update_state_checks.ps1` refresh on 2026-04-25:

| surface | current evidence | reconciliation |
|---|---|---|
| Station checks | `dev_harness=ok,cbo_core=ok,avatar_web=ok,telemetry_gateway=ok` | Core HTTP services and Telemetry support are alive. |
| Runtime truth | `runtime_truth_state=fresh` | Generated truth surfaces were current after refresh. |
| Topology risk | `LOW`; duplicate services `none` | Current runtime is not showing multiplicity failure. |
| Service failure | active flags `0`; lanes `clear` | Failure watch is currently clear. |
| Clarity substrate | `active_objective_status=active`; source registry `valid(5 roots)` | Confusion policy is active in runtime support surfaces. |
| Topology authority counts | canonical core `6`, canonical support `2`, unknown `3` | Three active loop families remain operational but authority-unresolved. |

Runtime services currently supported by evidence:

| system | runtime status | authority status |
|---|---|---|
| Dev Harness | ok | canonical core |
| CBO Core | ok | canonical core |
| Avatar Web | ok | canonical core |
| Discord Gateway | running per sunrise receipt/topology | canonical core |
| Station health loop | running per topology/STATE | canonical core |
| Service failure watch | running/clear | canonical core |
| Telemetry Gateway | ok | canonical support |
| CLI Avatar | running per sunrise/topology | canonical support |
| Local MCP server | validated by sunrise; stdio client-launched | canonical support |
| Navigator/Triage loop | running | unknown, completion/simplification required |
| Energy Churn/CP9 loop | running | unknown, completion/simplification required |
| CP6/CP7 loop | running | unknown, completion/simplification required |
| Bridge Overseer | not started by sunrise unless override | quarantined noncanonical |

## Active And Operational Doctrine

These doctrine/directive surfaces are currently real enough to be treated as active operational authority, with noted caveats:

| doctrine/directive | path(s) | runtime status | caveat |
|---|---|---|---|
| Session governance charter | `AGENTS.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, `COMPENDIUM.md` | active in operator/agent session behavior | `MEMORY.md` and `COMPENDIUM.md` are support/reference surfaces, not runtime authority. |
| Sunrise/sunset control plane | `Scripts/sunrise_calyx.ps1`, `Scripts/start_calyx_core_services.ps1`, `Scripts/sunset_calyx.ps1`, `docs/canonical/CALYX_CANONICAL_CONTROL_PLANE.md` | active and exercised | `start_calyx_core_services.ps1` name still says "core" while starting support/unknown loops. |
| Governed `/chat` operator path | `cbo_hub/cbo_core/app.py`, `cbo_hub/avatar_web/app.py`, `calyx/cbo/discord_gateway.py`, `docs/canonical/CALYX_CANONICAL_OPERATOR_PATH.md` | active and exercised | Avatar Web and Discord are current operator surfaces; Telemetry and CLI are support. |
| Runtime truth model | `STATE.md`, `Scripts/update_state_checks.ps1`, `Scripts/runtime_truth_contract.ps1`, `runtime/*.json` | active | `STATE.md` is support/advisory, not sole truth. |
| Runtime topology observation | `calyx/governance/runtime_topology.py`, `Scripts/runtime_topology_snapshot.py` | active and emitting fresh evidence | Observer is not liveness authority; it classifies runtime. |
| Service failure watch | `Scripts/service_failure_watch.ps1`, `Scripts/service_failure_contract.ps1`, `runtime/service_failure_status.json` | active and clear | Authority is real, but long-term simplification remains appropriate. |
| External emitter gate | `calyx/kernel/external_emitter_gate.py`, sunrise preflight | active | Enforces OpenClaw/external sender quarantine posture. |
| Local MCP support | `calyx/mcp_server/server.py`, `Scripts/start_calyx_mcp_stdio.ps1`, `docs/canonical/CALYX_LOCAL_MCP_SERVER.md` | active as validated support | Read-only stdio server; not a control plane and not memory ingestion authority. |
| Confusion policy | `docs/canonical/CALYX_CONFUSION_ESCALATION_PROTOCOL.md`, `runtime/active_objective.json`, `runtime/clarity_status.json` | active in runtime support surfaces | Helps classify uncertainty; does not grant new capability. |
| Source authority registry | `docs/canonical/CALYX_SOURCE_AUTHORITY_REGISTRY.json` | active support; all 5 roots exist | Source material authority does not mean every file is canonical truth. |

## Active But Confusing Doctrine

These surfaces are active or still referenced, but their wording/status creates confusion against current reduced reality:

| surface | path(s) | why confusing | current truth |
|---|---|---|---|
| February `DOC_STATUS_REGISTRY` active labels | `docs/DOC_STATUS_REGISTRY.json` | Many docs are marked `active` even when they are historical, support-only, superseded by reduction, or outside current runtime. | Newer canonical docs must outrank this registry where conflict exists. |
| Canonical Ops Index | `docs/operations/CANONICAL_OPS_INDEX.md` | Still lists Bridge Overseer in sunrise-wired components and refers to old docs as active source of truth. | Bridge Overseer is quarantined and no longer normally started. |
| Operational Doctrine | `docs/operations/STATION_CALYX_OPERATIONAL_DOCTRINE.md` | Treats audit layer as "the truth source" and names broader loops as sunrise doctrine. | Current truth is distributed across runtime JSON, receipts, topology, probes, and operator context. |
| Compendium agent ecology | `COMPENDIUM.md`, `docs/AGENT_REPOSITORY.md` | Lists many agents and CP roles as if operationally meaningful. | Several entries are active unknown loops, many are historical, missing, or conceptual. |
| Daily memory doctrine | `AGENTS.md`, `MEMORY.md`, `memory/YYYY-MM-DD.md` | Daily memory is required by doctrine but not reliably enforced by runtime. | Memory is support/reference; daily continuity needs completion or doctrinal demotion. |
| "Core services" naming | `Scripts/check_calyx_core_services.ps1`, `Scripts/start_calyx_core_services.ps1` | Names imply all checked/launched services are core. | Telemetry, CLI, MCP are support; CP loops remain unknown. |
| Runtime singleton/multiplicity doctrine | `docs/planning/WO_RUNTIME_*`, topology receipts | Several WOs imply stronger enforcement than exists. | Topology observes and labels; full singleton enforcement remains partial. |

## Work Order Reconciliation

Classification vocabulary:

- `active_operational`: code is implemented, integrated, exercised, and current.
- `active_support`: implemented/exercised support surface, not core authority.
- `completed_reduction_artifact`: planning/canonicalization work complete; used as authority reference.
- `partial_or_confusing`: some code/docs exist, but authority or exercise is incomplete.
- `quarantined_noncanonical`: explicitly excluded from current authority.
- `archived_or_historical`: retained for history/evidence; not active operation.
- `documented_not_operational`: docs/plans exist but no current runtime exercise.

| Work Order / doctrine target | evidence paths | current classification | reconciliation |
|---|---|---|---|
| WO_CALYX_CORE_REDUCTION_AND_CANONICALIZATION_V1 | `docs/planning/WO_CALYX_CORE_REDUCTION_AND_CANONICALIZATION_V1.md`, `docs/canonical/CALYX_CORE_CLASSIFICATION_REGISTRY.md`, `runtime/receipts/governance/core_reduction_classification__20260423_160000.json` | completed_reduction_artifact | Current authority reference for reduction. |
| WO_CALYX_CANONICAL_AUTHORITY_RESOLUTION_V1 | `docs/planning/WO_CALYX_CANONICAL_AUTHORITY_RESOLUTION_V1.md`, `docs/canonical/CALYX_AUTHORITY_RESOLUTION_REGISTRY.md`, `runtime/receipts/governance/canonical_authority_resolution__20260423_163404.json` | completed_reduction_artifact | Resolved support/quarantine boundaries. |
| WO_CALYX_DOC_AND_PATH_CANONICALIZATION_EXECUTION_V1 | `docs/planning/WO_CALYX_DOC_AND_PATH_CANONICALIZATION_EXECUTION_V1.md`, `docs/canonical/CALYX_DOCUMENT_STATUS_REGISTRY.md`, `docs/canonical/CALYX_PATH_AND_ENTRYPOINT_DEMOTION_REGISTRY.md` | completed_reduction_artifact | Corrected many authority claims; not exhaustive across all old docs. |
| WO_CALYX_RUNTIME_AUTHORITY_LABELING_AND_ENFORCEMENT_ALIGNMENT_V1 | `docs/planning/WO_CALYX_RUNTIME_AUTHORITY_LABELING_AND_ENFORCEMENT_ALIGNMENT_V1.md`, runtime truth scripts, `runtime/receipts/governance/runtime_authority_labeling_alignment__20260423_180000.json` | active_operational | Runtime labels are now active; later confusion-policy alignment extended this. |
| WO_CALYX_NONCANONICAL_PATH_DEMOTION_AND_QUARANTINE_ENFORCEMENT_V1 | `docs/planning/WO_CALYX_NONCANONICAL_PATH_DEMOTION_AND_QUARANTINE_ENFORCEMENT_V1.md`, `docs/canonical/CALYX_NONCANONICAL_ENFORCEMENT_REGISTRY.md` | active_operational | Bridge, legacy Discord, and OpenClaw paths are fenced/refusal-gated. |
| Active runtime confusion policy alignment | `docs/canonical/CALYX_CONFUSION_ESCALATION_PROTOCOL.md`, `runtime/active_objective.json`, `runtime/clarity_status.json`, `runtime/receipts/governance/active_runtime_confusion_policy_alignment__20260425_230800.json` | active_operational | Current confusion policy is visible in runtime truth and sunrise validation. |
| WO_SUNRISE_CANONICAL_BOOTPATH_DISCORD_GATEWAY_V1 | `Scripts/sunrise_calyx.ps1`, `Scripts/start_calyx_core_services.ps1`, `runtime/receipts/sunrise_receipt__20260425_160701.json` | active_operational | Current startup path is real and exercised. |
| WO_OPENCLAW_DECOMMISSION_GATING_V2 | `calyx/kernel/external_emitter_gate.py`, `docs/operations/WO_OPENCLAW_DECOMMISSION_GATING_V2_LADDER.md`, `OPENCLAW_*` docs | active_operational for gate; quarantined_noncanonical for OpenClaw capability | Gate is real; OpenClaw capability is not current authority. |
| WO_GATEWAY_DENY_BY_DEFAULT_HARDEN_V1 | `calyx/cbo/discord_gateway.py`, `Scripts/discord_gateway_preflight.py`, validation docs | active_operational | Discord Gateway deny-by-default posture is implemented. |
| WO_HEARTBEAT_SENDER_UNIFICATION_V1 | `calyx/cbo/discord_gateway.py`, `Scripts/audit_health.py`, validation docs | active_operational | One sender identity is currently audited in sunrise. |
| WO_GOVERNANCE_BUDGET_ACCOUNTING_V1 | `calyx/kernel/governance_budget.py`, `cbo_hub/cbo_core/app.py`, validation docs | active_operational | Budget records are wired into governed response finalization. |
| WO_GOVERNANCE_BUDGET_COVERAGE_GUARANTEE_V2 | `Scripts/governance_budget_coverage_check.py`, `Scripts/governance_budget_coverage_ladder.py`, validation docs | active_support | Coverage tooling exists; runtime use depends on audit/test invocation. |
| WO_VERIFIED_CLAIMS_LEDGER_V1 | `calyx/kernel/verified_claims.py`, `cbo_hub/cbo_core/app.py`, `docs/planning/WO_VERIFIED_CLAIMS_LEDGER_V1.md` | active_operational | Claim lifecycle support is wired into CBO Core. |
| WO_CANONICAL_RESPONSE_HASH_V1 | `calyx/kernel/canonical_bundle.py`, `calyx/kernel/canonical_hash.py`, `calyx/kernel/canonical_json.py`, `cbo_hub/cbo_core/app.py` | active_operational | Canonical bundle/hash path is implemented. |
| WO_CANONICAL_EQUIVALENCE_HASH_V2 | `Scripts/canonical_parity_check.py`, `calyx/kernel/canonical_bundle.py` | active_support | Parity tool exists; not a resident runtime authority. |
| WO_EQUIVALENCE_SCOPE_V3 | `cbo_hub/cbo_core/app.py`, `calyx/kernel/sign_request.py` | active_support | Trusted gateway/governance attestation exists; enforcement depends on config. |
| WO_CALYX_SIGN_INGRESS_AUTH_V4 | `calyx/kernel/sign_request.py`, `calyx/kernel/nonce_ledger.py`, `Scripts/calyx_sign_request.py`, validation docs | active_support | Implemented support for signed ingress; not normal operator path. |
| WO_REQUEST_ORIENTATION_PROTOCOL_V1/V2 | `calyx/kernel/intent_orientation.py`, `cbo_hub/cbo_core/app.py`, tests/validation docs | active_operational | Deterministic fast paths and intent orientation are wired into `/chat`. |
| WO_DOC_HYGIENE_DEPRECATION_GATES_V1/V2 | `calyx/kernel/doc_status.py`, `Scripts/add_doc_status_headers.py`, validation docs | partial_or_confusing | Tooling exists, but doc labels are stale/overbroad after reduction. |
| WO_GOVERNANCE_SINGULARITY_AND_DOC_AUTHORITY_V3 | validation docs, `Scripts/audit_health.py`, CBO Core comments | partial_or_confusing | Some audit checks exist; doc authority remains drifted. |
| WO_CAUSAL_ENVELOPE_AUDIT_CLARITY_V1 | `calyx/kernel/event_ledger.py`, validation docs | active_operational | Causal envelope support is wired into event ledger. |
| WO_AUDIT_QUERY_TOOLING_V1 | `Scripts/audit_trace.py`, `Scripts/audit_anomalies.py`, `Scripts/audit_health.py` | active_support | Tooling exists and used in sunrise; not a service. |
| WO_IDLE_ACTIVITY_GOVERNANCE_V3 | `calyx/cbo/discord_gateway.py`, `calyx/kernel/governance_budget.py`, validation docs | active_operational | Heartbeat/system task governance exists. |
| WO_RUNTIME_TOPOLOGY_LABELING_V1 | `calyx/governance/runtime_topology.py`, `Scripts/runtime_topology_snapshot.py`, receipts | active_operational | Topology labels are active. |
| WO_RUNTIME_TOPOLOGY_NORMALIZATION_V1 | `docs/planning/WO_RUNTIME_TOPOLOGY_NORMALIZATION_V1.md`, topology receipts | partial_or_confusing | Normalization exists as design/partial implementation; not a resolved doctrine layer. |
| WO_RUNTIME_OPERATOR_EXPLICIT_IDENTITY_DISCLOSURE_V1 | `runtime/runtime_topology_snapshot.json`, topology code | active_operational | Process identity disclosure is active but partial by design. |
| WO_RUNTIME_MULTIPLICITY_DECLARATION_AND_LAUNCH_NOTICE_V1 | docs/planning, topology receipts | partial_or_confusing | Multiplicity is observed, not fully governed. |
| WO_RUNTIME_MULTIPLICITY_ENFORCEMENT_AND_VALIDATION_V1 | docs/planning, topology tests | partial_or_confusing | Enforcement claim exceeds current runtime. |
| WO_RUNTIME_SINGLETON_AND_RECONCILIATION_ENFORCEMENT_V1 | `calyx/governance/reconciliation.py`, receipts | partial_or_confusing | Reconciliation exists, but singleton enforcement is not fully settled. |
| WO_BRIDGE_OVERSEER_IDLE_MODE_AND_MULTIPLICITY_NORMALIZATION_V1 | docs/planning, `calyx/cbo/bridge_overseer.py` | quarantined_noncanonical | Bridge is now fenced/quarantined; WO status is confusing if read as active. |
| WO_LOCAL_ORCHESTRATION_PROTOTYPE_V1 | docs/planning, `runtime/receipts/governance/local_orchestration_prototype_scaffold__20260328_121313.json` | documented_not_operational | Scaffold/receipt exists; not current runtime. |
| WO_OPERATOR_INTERVENTION_PROTOCOL_V1 | docs/planning, `tests/test_runtime_operator_intervention.py` | partial_or_confusing | Test/model support exists; not clearly resident runtime behavior. |
| WO_ACTIVE_AUTHORITY_CONTEXT_AND_THREAD_DEMOTION_V1 | docs/planning | documented_not_operational | Good doctrine target; no current enforcement found in runtime path. |
| WO_STATION_HEALTH_LOOP_EFFICIENCY_AND_TRUTH_PRESERVATION_V1 | docs/planning, `Scripts/station_health_loop.ps1` | partial_or_confusing | Health loop is real; this specific WO remains planning/efficiency framing. |
| WO_STATION_CALYX_CAPABILITY_FRONTIER_ASSESSMENT_V1 | docs/planning, operations assessment | archived_or_historical | Assessment artifact, not active runtime. |
| WO_SWARM_EXECUTION_ENVELOPE_AND_WORKER_LEASES_V1 | `calyx/kernel/swarm_*`, `tests/test_swarm_*`, receipts | partial_or_confusing | Staged/test infrastructure; execution/enforcement not active. |
| WO_SWARM_TRACE_GRAPH_AND_RECEIPT_BUNDLE_V1 | `calyx/kernel/swarm_trace.py`, tests, receipts | partial_or_confusing | Trace/receipt tooling exists; not active worker runtime. |
| WO_SANDBOXED_WORKER_RUNTIME_V1 | `calyx/kernel/swarm_sandbox.py`, tests, receipts | partial_or_confusing | Sandbox components exist; not active runtime execution path. |
| WO_OPENCLAW_MEMORY_PLUGIN_BINDING_V0 | docs/planning, governance receipt | quarantined_noncanonical | Historical external integration scaffold. |
| WO_OPENCLAW_REINTEGRATION_PATH_V1 | docs/planning | quarantined_noncanonical | Future/reintegration idea; prohibited from current authority. |
| WO_OPENCLAW_UNIFIED_EXECUTOR_IMPLEMENTATION | docs/planning, `calyx/cbo/discord_gateway.py` comments | quarantined_noncanonical | Historical naming remains, but OpenClaw authority is not active. |
| WO_KALSHI_* family | docs/planning, tests `test_kalshi_*` | archived_or_historical | Market layer is outside current reduced Station. |
| WO_WEATHER_* family | docs/planning, tests `test_weather_*` | archived_or_historical | Weather layer is outside current reduced Station. |

## Documentation Family Reconciliation

| family | representative paths | status | reality |
|---|---|---|---|
| Canonical reduction docs | `docs/canonical/*` | active support/core registries | Strongest current documentation authority. |
| Operational February docs | `docs/operations/*`, `docs/DOC_STATUS_REGISTRY.json` | mixed | Many are useful evidence; some active labels are stale after reduction. |
| BloomOS / Constellation / Vault / ritual doctrine | `docs/BLOOM*`, `docs/CONSTELLATION*`, `docs/VAULT*`, `docs/*CEREMONY*` | historical or conceptual | Cultural/doctrinal corpus; not current runtime implementation. |
| Calyx Mail docs | `docs/calyx_mail_*`, `calyx/mail/*`, `tests/test_mail_*` | partial/test-supported | Mail library has tests and code; not current canonical operator path. |
| Agent ecology docs | `COMPENDIUM.md`, `docs/AGENT_REPOSITORY.md`, CP docs | mixed/confusing | Some active loops exist; many named agents are historical, missing, or conceptual. |
| OpenClaw docs | `docs/OPENCLAW_CALYX_INTEGRATION.md`, OpenClaw WOs/playbooks | quarantined noncanonical | Gate/refusal posture is current; integration authority is not. |
| Cloud/federation docs | `docs/CLOUD_SYNC_WORKFLOW.md`, `docs/workflows/*`, federation docs | quarantined or historical | Not active local-first runtime. |
| Memory architecture docs | `docs/MEMORY_ARCHITECTURE_v1.0.md`, `docs/MEMORY_MVP_IMPLEMENTATION_PROPOSAL.md`, `docs/doctrine/STATION_MEMORY_LIFECYCLE.md` | partial/confusing | Memory doctrine is ahead of active runtime; `MEMORY.md` is support only. |
| Public repo / history rewrite docs | `docs/public_repo_*` | historical/planning | Useful if publishing; not active runtime. |
| Hardware/health docs | `docs/HARDWARE_*`, `docs/operations/STATION_HEALTH_BLOOMOS_AUDIT.md` | partially active | Health loop is real; broader hardware doctrine needs pruning. |

## Highest-Impact Confusion Sources

1. `docs/DOC_STATUS_REGISTRY.json` marks many February/April docs `active` even where reduction has since demoted or narrowed them.
2. `docs/operations/CANONICAL_OPS_INDEX.md` still contains pre-reduction wording around Bridge Overseer and old active docs.
3. `COMPENDIUM.md` presents named agents and CP roles in a way that can look operational even where code is missing or noncanonical.
4. `docs/AGENT_REPOSITORY.md` is correctly marked historical, but still carries enough concrete entrypoint language to mislead.
5. Runtime loop authority for Navigator/Triage, Energy Churn/CP9, and CP6/CP7 remains `unknown` while the loops are active.
6. Singleton/multiplicity WOs imply enforcement that currently exists mostly as observation and labeling.
7. Memory doctrine implies richer continuity than current runtime supports.
8. Calyx Mail code/tests look substantial, but the system does not use mail as the current operator path.
9. Swarm/worker/sandbox tests and receipts can look like active autonomy, but current runtime does not execute through them.
10. Market/weather/Kalshi WOs and tests are real artifacts but not Station core.

## What Is Real

Real current Station Calyx:

- One workstation-bound Station.
- Sunrise/sunset control plane.
- CBO Core governed `/chat`.
- Avatar Web and Discord Gateway as current operator surfaces.
- Dev Harness, CBO Core, Avatar Web as canonical core HTTP services.
- Telemetry Gateway, CLI Avatar, local MCP as canonical support.
- External emitter gate.
- Station health, service failure watch, runtime topology, heartbeat/service snapshot/STATE support truth.
- Clarity/confusion substrate with active objective and source authority registry.
- Receipts and event ledger as evidence, not standalone authority.

## What Was Thought To Be Real

Systems that were treated or documented as more real than they currently are:

- Bridge Overseer as central runtime orchestrator.
- Workspace planning UI as normal planning authority.
- Mail/intent/work-envelope as canonical execution spine.
- Swarm/worker leases as active parallel execution substrate.
- CP ecology as a functioning agent crew.
- Memory hot/warm architecture as active continuity.
- OpenClaw as an integration path.
- Cloud/federation/MCP workflows beyond the local read-only MCP support server.
- Kalshi/weather/market research layers.
- BloomOS/Constellation/Vault ritual doctrine as implementation rather than cultural/historical substrate.

## What Never Made It Close

These are currently documented/conceptual more than operational:

- Full CP-MOE role family as implemented routing/load/provenance system.
- CP8/CP10 and several named agent entrypoints.
- Automatic retroactive context ingestion from `D:\Calyx_Data`.
- Federated/multi-node operational workflows.
- Production-grade container/deploy topology.
- Active autonomous worker swarm.
- Active Calyx Mail operator path.
- Governance metrics implementation from `docs/governance/governance_metrics_spec_v0.1.md`.

## Reduction Implications

Preserve:

- Sunrise/sunset.
- Governed `/chat`.
- Discord Gateway.
- Core HTTP services.
- Station health/failure/topology truth surfaces.
- External emitter gate.
- Local MCP read-only support.
- Confusion policy/source registry/decision ledger.

Simplify:

- Navigator/Triage loop authority and operator value.
- Energy Churn/CP9 loop authority and tuning boundaries.
- CP6/CP7 loop authority and output usefulness.
- `STATE.md`/heartbeat/snapshot overlap.
- DOC_STATUS registry alignment after reduction.

Quarantine:

- Bridge Overseer.
- Workspace planning.
- Legacy Discord intake.
- OpenClaw.
- Mail/intent/work-envelope execution spine.
- Swarm/worker/sandbox runtime.
- Cloud/federation workflows.
- Market/weather/Kalshi layers.

Demote to historical:

- BloomOS/Constellation/Vault ritual and canon docs unless a later pass explicitly maps a subset into runtime.
- Agent ecology entries without code/runtime evidence.
- Old validation reports that no longer represent current authority.
- Hot/warm memory architecture claims beyond support reference.

Complete only if still desired:

- Daily memory continuity discipline.
- Runtime multiplicity/singleton enforcement.
- Operator intervention protocol.
- Documentation status registry repair.

## Final Assessment

The Station is operational, but its mental model is overloaded by accumulated doctrine. The active runtime is now much smaller and clearer than the corpus around it.

The next safe work is not to implement old WOs blindly. The next safe work is to select one confusing family at a time, decide whether it is still wanted, then either complete, simplify, quarantine, or demote it against current runtime evidence.
