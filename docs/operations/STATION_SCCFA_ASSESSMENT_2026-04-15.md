---
status: active
owner: station
last_reviewed_utc: "2026-04-16"
doctrine_scope: governed
---

# Station SCCFA Assessment - 2026-04-15

## Scope

Assessment type: receipt-backed SCCFA measurement pass.

Mode: observe-only, read-only measurement. No runtime services, configs, or code were modified. No restart was performed.

Governing document:

`docs/planning/WO_STATION_CALYX_CAPABILITY_FRONTIER_ASSESSMENT_V1.md`

Machine-readable receipt:

`runtime/receipts/audit/sccfa_assessment__20260416_012857.json`

## Executive Result

The first receipt-backed SCCFA baseline measures Station Calyx as:

```text
bottleneck_score = 0.44
geometric_frontier_score = 0.6597
conservative_sccfa_score = 0.5279
```

Band:

`partially governed / unstable under pressure`

Primary bottleneck:

`runtime_multiplicity_control`

Secondary bottleneck:

`approval_latency_fitness`

This result is lower than the April 15 provisional estimate because live measurement found material current-state limits:

- `STATE.md`, `runtime/station_heartbeat.json`, and `runtime/service_runtime_snapshot.json` were explicitly stale by TTL.
- direct port probes showed core services live, but the primary runtime truth surfaces were not fresh enough to serve as liveness authority.
- process topology showed duplicate resident loop families and duplicate bridge overseer families.
- `audit_health.py --since-minutes 30` failed due to a gateway heartbeat sender-identity mismatch.
- approval latency fitness had only weak direct measurement evidence.

## Dimension Scores

| Dimension | Score | Confidence | Evidence Type | Summary |
| --- | ---: | --- | --- | --- |
| intent_clarity | 0.84 | medium | direct + inferred | Strong doctrine and request structure; current measurement intent was explicit. Limited direct workload sample evidence. |
| authority_provenance | 0.80 | high | direct | Strong contract, compendium, policy, and approval artifacts. Dirty worktree and legacy artifacts limit certainty. |
| evidence_freshness | 0.58 | medium | direct | `station_health.json` fresh, but `STATE.md`, heartbeat, and service snapshot stale by TTL. |
| telemetry_truthfulness | 0.57 | medium | direct | Live port probes and service failure status agree on service health, but 30-minute audit health failed on heartbeat sender identity. |
| runtime_multiplicity_control | 0.44 | high | direct | Multiple duplicate resident loop/process families observed. Wrapper/child pairs exist, but duplicate loop families are not reconciled in current truth surfaces. |
| execution_surface_boundedness | 0.82 | high | direct | Contract allowlists, Discord preflight, external emitter gate, deny-by-default tests, and secret scan passed. |
| verification_coverage | 0.88 | high | direct | Full test suite passed, doc-status validation passed, secret scan passed, JSON/YAML parse passed, diff check passed. |
| rollback_recovery_strength | 0.66 | medium | direct + inferred | Sunset/sunrise/restart receipts and service failure receipts exist; no active failure flags. Current pass did not inject or time recovery. |
| operator_visibility | 0.61 | medium | direct | State and receipts expose conditions, but stale primary surfaces and duplicate topology require manual inspection to see. |
| approval_latency_fitness | 0.55 | low | direct + inferred | Approval/proposal artifacts exist, but no current queue dwell-time measurement or review throughput signal was available. |

## Metric Computation

Scores used:

```text
intent_clarity = 0.84
authority_provenance = 0.80
evidence_freshness = 0.58
telemetry_truthfulness = 0.57
runtime_multiplicity_control = 0.44
execution_surface_boundedness = 0.82
verification_coverage = 0.88
rollback_recovery_strength = 0.66
operator_visibility = 0.61
approval_latency_fitness = 0.55
```

Computed:

```text
B = min(scores) = 0.44
F = product(scores)^(1/10) = 0.6597
SCCFA = (0.6 * 0.44) + (0.4 * 0.6597) = 0.5279
```

## Evidence Mapping

### intent_clarity

Direct evidence:

- `docs/planning/WO_STATION_CALYX_CAPABILITY_FRONTIER_ASSESSMENT_V1.md`
- `AGENTS.md`
- current operator directive for observe-only SCCFA execution
- test result: `python -m pytest -q` passed `347` tests including intent/routing tests

Inferred evidence:

- the measured task was successfully bounded as observe-only except for required report/receipt outputs.
- broader workload intent clarity was not measured across a large sample during this pass.

Score rationale:

Intent handling is strong for the current task and supported by doctrine and tests, but this pass did not measure sustained multi-request ambiguity handling.

### authority_provenance

Direct evidence:

- `AGENTS.md`
- `COMPENDIUM.md`
- `CALYX_CONTRACT.yaml`
- `policy/tripwire_levels.yaml`
- `policy/competitor_clause.yaml`
- `governance/approvals/*`
- `governance/receipts/*`
- test result: governance and policy tests included in `347 passed`

Inferred evidence:

- authority structure is coherent, but the dirty worktree and many untracked governance/runtime files reduce certainty that all future surfaces are fully reconciled.

Score rationale:

The Station can distinguish doctrine, roles, task types, approvals, and policy gates. It remains below excellent because the repository state is broad and not fully normalized.

### evidence_freshness

Direct evidence:

- `STATE.md`: `runtime_truth_state: stale`, `runtime_truth_canonical: live_probes (ttl_expired)`
- `runtime/station_heartbeat.json`: `truth_state: stale`, `stale_reason: ttl_expired`
- `runtime/service_runtime_snapshot.json`: `truth_state: stale`, `stale_reason: ttl_expired`
- `runtime/station_health.json`: `truth_state: fresh`, health `pass`
- `runtime/receipts/security/runtime_truth_transition__20260416_011234_319.json`

Inferred evidence:

- fresh health and direct probes can support immediate observation, but stale primary state surfaces cannot be treated as current liveness authority.

Score rationale:

Freshness discipline is working because stale surfaces are explicitly marked. Capability is constrained because key operator-facing truth surfaces were stale at measurement time.

### telemetry_truthfulness

Direct evidence:

- `Scripts/check_calyx_core_services.ps1`: `dev_harness=ok,cbo_core=ok,avatar_web=ok,telemetry_gateway=ok`
- `runtime/service_failure_status.json`: active failure count `0`
- `runtime/station_health.json`: health `pass`
- `runtime/service_runtime_snapshot.json`: stale but internally reports services `ok`
- `.venv_cbohub311\Scripts\python.exe .\Scripts\audit_health.py --since-minutes 30`: failed sender-identity audit
- `.venv_cbohub311\Scripts\python.exe .\Scripts\audit_health.py --since-minutes 5`: no mismatches detected

Inferred evidence:

- current five-minute window is clean, but the 30-minute mismatch shows telemetry/audit coherence is not consistently maintained across the assessment horizon.

Score rationale:

Live service probes are truthful now, but audit-health mismatch and stale primary truth surfaces materially constrain telemetry trust.

### runtime_multiplicity_control

Direct evidence:

- process topology command output captured duplicate resident families:
  - `service_failure_watch`: 2 PowerShell processes
  - `navigator_triage_loop`: 2 PowerShell processes
  - `energy_churn_cp9_loop`: 2 PowerShell processes
  - `cp6_cp7_loop`: 2 PowerShell processes
  - `bridge_overseer`: 2 wrapper/child families, 4 Python processes total
- expected wrapper/child pairs observed for uvicorn services and Discord Gateway
- `runtime/service_runtime_snapshot.json` does not reconcile those duplicate loop families

Inferred evidence:

- some duplicate Python entries are expected wrapper/child pairs, but duplicate loop families with distinct parent PIDs are not sufficiently explained by current truth surfaces.

Score rationale:

This is the primary bottleneck. The Station is operational, but live topology truth and duplicate-process reconciliation are not yet strong enough for higher governed capability.

### execution_surface_boundedness

Direct evidence:

- `CALYX_CONTRACT.yaml` tool surface allowlists and stop conditions
- `calyx/kernel/toolsurface.py`
- Discord preflight: governance required, allowlists resolved, pass
- external emitter gate: no OpenClaw detected
- `DISCORD_IDS.md` ignored by `.gitignore`
- secret-pattern scan: pass
- tests covering policy, routing, mail allowlist/tamper/wrong-key paths included in `347 passed`

Inferred evidence:

- deny-by-default posture is strong locally, but external/action tempo was not stressed during this pass.

Score rationale:

Execution surfaces are well bounded by local artifacts and tests. The score remains below excellent because this was observe-only and did not measure all approved execution paths under pressure.

### verification_coverage

Direct evidence:

- `python -m pytest -q`: `347 passed, 4 warnings`
- `git diff --check`: pass
- doc-status validation: `DOC_STATUS_OK`
- stale compendium path scan: no matches
- secret-pattern scan: `SECRET_PATTERN_SCAN_OK`
- JSON parse: `JSON_PARSE_OK_UTF8_SIG`
- YAML parse: `YAML_PARSE_OK`
- expected malformed quarantine artifact: `governance\intents\quarantine\malformed-3d77b19e.json`

Inferred evidence:

- coverage is broad for current code and governance surfaces, but no formal coverage percentage or live adversarial injection was measured.

Score rationale:

Verification is one of the strongest current layers. It is not perfect because live topology/recovery adversarial checks remain manual.

### rollback_recovery_strength

Direct evidence:

- latest sunrise receipt: `runtime/receipts/sunrise_receipt__20260415_165725.json`
- service failure receipts under `runtime/receipts/security/service_failure_flag__*.json`
- runtime truth transition receipts under `runtime/receipts/security/runtime_truth_transition__*.json`
- `runtime/service_failure_status.json`: active failure count `0`
- `Scripts/restart_service.ps1`, `Scripts/sunset_calyx.ps1`, `Scripts/station_patch_sunrise.ps1`

Inferred evidence:

- prior audit demonstrated repair and recovery, but this observe-only pass did not inject a failure or measure MTTD/MTTR.

Score rationale:

Recovery mechanisms exist and have receipts. The score is limited because recovery timing was not directly measured and duplicate topology could complicate containment.

### operator_visibility

Direct evidence:

- `STATE.md` exposes stale state and core service checks
- `runtime/station_health.json` exposes fresh health
- `runtime/service_failure_status.json` exposes no active failure flags
- `docs/operations/STATION_INTEGRITY_AUDIT_2026-04-15.md`
- `docs/operations/STATION_SCCFA_ASSESSMENT_2026-04-15.md`
- runtime receipts are plain-path referenced
- audit-health output exposes sender-identity mismatch

Inferred evidence:

- the operator can inspect the current state, but duplicate runtime topology is not sufficiently visible in normal STATE/heartbeat surfaces.

Score rationale:

Visibility is usable but not yet high-trust under activity. Important bottlenecks required manual process inspection to discover.

### approval_latency_fitness

Direct evidence:

- governance artifact counts:
  - `governance/approvals`: 16 files
  - `governance/proposals`: 2 files
  - `governance/intents/outbox`: 1 file
  - `governance/intents/processed`: 1 file
  - `governance/intents/quarantine`: 1 file
- `runtime/receipts/budget/task_budget__20260416.jsonl` contains heartbeat task budget records
- `AGENTS.md` override ceremony and evidence requirements

Inferred evidence:

- approval machinery exists, but there was no direct queue dwell-time or current approval backlog measurement.

Score rationale:

This is the secondary bottleneck. Human-review cadence is doctrinally strong but empirically under-measured in the current Station surfaces.

## Integrity Checks

### Stale Truth Surfaces

Detected and flagged.

`STATE.md`, `runtime/station_heartbeat.json`, and `runtime/service_runtime_snapshot.json` were stale by TTL. They were not used as current liveness authority. Live port probes, fresh `runtime/station_health.json`, and `runtime/service_failure_status.json` were used for current-state interpretation.

Confidence impact:

- reduced `evidence_freshness`
- reduced `telemetry_truthfulness`
- reduced `operator_visibility`

### Current STATE / Receipt Contradictions

No contradiction was accepted silently.

Current direct service probe was `ok` for all four core services. Stale state surfaces also reported `ok`, but were marked stale. The report treats them as historical/supporting evidence only.

### Deprecated or Overridden Documents

Doc-status validation returned `DOC_STATUS_OK`.

No deprecated or overridden document was used as primary authority.

### Non-Authoritative External Emitters

External emitter gate returned `No OpenClaw detected`.

Discord Gateway preflight passed with governed allowlists resolved.

### Audit Health

The 30-minute audit-health check failed:

`discord.heartbeat.sender.identity with heartbeat_sender_enabled=true: expected 1, got 0`

The 5-minute audit-health check passed with no mismatches.

This was treated as a telemetry-truthfulness limitation, not ignored.

## Commands Run

Read-only measurement commands:

- `Get-Date -Format o`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\Scripts\check_calyx_core_services.ps1`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\Scripts\patch_readiness.ps1`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\Scripts\station_health_check.ps1`
- `.venv_cbohub311\Scripts\python.exe -m calyx.kernel.external_emitter_gate`
- `.venv_cbohub311\Scripts\python.exe .\Scripts\audit_health.py --since-minutes 30`
- `.venv_cbohub311\Scripts\python.exe .\Scripts\audit_health.py --since-minutes 5`
- `python .\Scripts\discord_gateway_preflight.py`
- doc-status validation via `calyx.kernel.doc_status.validate_ops_docs`
- stale compendium path scan
- `git diff --check`
- `git check-ignore -v DISCORD_IDS.md`
- process topology capture via `Get-CimInstance Win32_Process`
- port topology capture via `Get-NetTCPConnection`
- reads of `STATE.md`, `runtime/station_health.json`, `runtime/station_heartbeat.json`, `runtime/service_runtime_snapshot.json`, `runtime/service_failure_status.json`
- `python -m pytest -q`
- redacted secret-pattern scan over committable files
- JSON/YAML policy and governance parse checks
- governance approval/proposal/intent count summary

## Residual Risks

1. Runtime multiplicity is the load-bearing bottleneck.
   - Duplicate loop families are live now.
   - Current STATE and service snapshot do not fully expose or classify them.

2. Primary truth surfaces were stale at measurement time.
   - Staleness is correctly marked, which is good.
   - Operator-facing liveness still depends on supplemental direct probes.

3. Telemetry audit coherence is window-sensitive.
   - 5-minute audit window passed.
   - 30-minute audit window failed on sender identity.

4. Approval latency is under-instrumented.
   - Governance artifacts exist.
   - Dwell-time/backlog metrics were not directly available.

5. Repository worktree is large and dirty.
   - This pass did not modify or normalize it.
   - Dirty state reduces authority-provenance confidence.

## Baseline Conclusion

Station Calyx is useful and governed in important ways: doctrine exists, contracts and tests are real, preflight gates work, and core services are live.

The measured frontier today is constrained by live operational coherence, not by raw reasoning or verification coverage.

The first receipt-backed SCCFA baseline is:

```text
SCCFA = 0.5279
Band = partially governed / unstable under pressure
```

The next capability-raising work should focus on:

1. runtime multiplicity declaration, detection, and reconciliation
2. freshness of STATE/heartbeat/service snapshots
3. telemetry sender-identity consistency over longer windows
4. approval queue visibility and dwell-time measurement
