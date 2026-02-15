# Calyx Autonomous Governance Specification v0.1

**Document type:** Specification  
**Mode:** Observation → Specification Draft  
**Constraint:** No implementation. No code changes. Specification only.

---

## SECTION 1 — Scope Definition

### 1.1 Definition: Autonomous Execution

**Requirement.** Within Station Calyx, **Autonomous Execution** means:

- A single execution run in which an agent (or model-driven pipeline) produces a **plan** comprising one or more **actions** (tool invocations or equivalent steps).
- The plan is evaluated for risk before execution.
- Actions may be **allowed**, **modified** (stabilized), or **blocked** by policy.
- Only allowed or modified actions are passed to an **Execution Adapter**.
- The adapter runs inside a **sandbox** that constrains filesystem and network effects.
- All intake, plan, risk decisions, executions, and outcomes are **logged** for audit and measurement.

**Rationale.** Autonomy here is bounded: plan generation and risk evaluation are in scope; execution is constrained by policy and sandbox.

**Assumption.** The agent or pipeline is the same logical entity that produced the plan; no delegation to untrusted external executors.

---

### 1.2 Non-Goals (Explicit Out of Scope)

**Requirement.** The following are **not** in scope for this specification:

1. **Real OS-level destructive access.** No unconstrained `rm`, format, or equivalent. No direct kernel or hardware control.
2. **Real network egress.** No live HTTP/HTTPS, SMTP, or other outbound network calls from the execution path unless explicitly provided as a sandboxed capability with boundaries defined in Section 4.
3. **Real process creation** outside the sandbox (e.g. spawning host processes that can access host filesystem or network).
4. **Persistence of execution state** beyond the sandbox and the logged artifacts defined in this specification.
5. **Proof of general safety** of any model or agent; only contract compliance and measurable governance metrics.

**Rationale.** Keeping non-goals explicit prevents scope creep and clarifies what "safe" means in this context.

---

### 1.3 Sandbox Boundaries

**Requirement.** The sandbox SHALL:

1. **Filesystem:** Expose a bounded directory tree (or equivalent) as the only writable/readable filesystem scope for the execution adapter. Paths outside this tree SHALL NOT be readable or writable by the adapter.
2. **Network:** Either disallow all network access, or allow only through a controlled proxy/mock that does not reach real external endpoints (see Section 4).
3. **Process:** Restrict execution to a defined set of tools or RPCs; no arbitrary shell or process execution unless explicitly modeled as a tool with defined semantics and risk treatment.
4. **Time:** Support a maximum execution duration (timeout) per run or per action, after which the run is terminated and logged as incomplete or timeout.

**Rationale.** Boundaries must be enforceable and auditable.

**Assumption.** The sandbox is implemented by the runtime; this specification defines the contract, not the implementation technique (e.g. chroot, container, or mock).

---

### 1.4 Execution Lifecycle Phases (Summary)

**Requirement.** The execution lifecycle SHALL consist of the following phases in order:

1. **Task Intake** — Accept and validate the task or prompt; produce a validated task descriptor.
2. **Plan Generation** — Produce a structured plan (ordered list of actions) from the task.
3. **Pre-Execution Risk Evaluation** — Evaluate each action for risk; classify and optionally modify.
4. **Stabilization Phase** — Apply stabilization mechanisms where required (see Section 3).
5. **Execution Adapter Invocation** — Invoke the adapter with the stabilized plan (or allowed subset).
6. **Post-Execution State Validation** — Compare observed state to expectations; detect integrity issues.
7. **Receipt + Event Logging** — Write immutable receipts and event log entries.

Details of each phase are in Section 2.

---

## SECTION 2 — Execution Lifecycle Contract

Each stage SHALL conform to the following contract (inputs, outputs, failure modes, logged artifacts).

---

### 2.1 Task Intake

| Aspect | Contract |
|--------|----------|
| **Inputs** | Raw task payload (e.g. user message, intent, or benchmark case); optional context (session, user id). |
| **Outputs** | Validated task descriptor: `task_id`, `task_type`, `payload_hash`, `received_ts_utc`, `validation_status` (ok / invalid). If invalid, no further stages run. |
| **Failure modes** | Payload too large; malformed; missing required fields; validation_status = invalid. |
| **Logged artifacts** | At least: `task_id`, `payload_hash`, `received_ts_utc`, `validation_status`. Optionally: size, task_type. |

**Requirement.** If `validation_status` is not `ok`, the lifecycle SHALL stop and only Task Intake SHALL be logged.

---

### 2.2 Plan Generation

| Aspect | Contract |
|--------|----------|
| **Inputs** | Validated task descriptor from Task Intake. |
| **Outputs** | Plan: `plan_id`, `plan_version`, `actions[]` where each action has at least: `action_id`, `tool_name`, `arguments` (or equivalent), `order`. Optional: `rationale`, `dependencies`. |
| **Failure modes** | Plan generation timeout; empty plan; malformed plan (e.g. missing tool_name); parse failure. |
| **Logged artifacts** | At least: `plan_id`, `plan_version`, `plan_hash` (deterministic hash of canonical plan representation), `action_count`, `generated_ts_utc`. Optionally: per-action `action_id`, `tool_name`. |

**Requirement.** Plan hash SHALL be computed over a canonical serialization (e.g. JSON with sorted keys) of the plan so that the same plan yields the same hash.

---

### 2.3 Pre-Execution Risk Evaluation

| Aspect | Contract |
|--------|----------|
| **Inputs** | Plan from Plan Generation; policy configuration; allowlist/blocklist; risk rules. |
| **Outputs** | Per-action risk result: `action_id`, `risk_score` (numeric or category), `risk_label` (e.g. unsafe, risky, benign), `policy_reason`, `decision` (allow, allow_modified, block). |
| **Failure modes** | Policy evaluation timeout; policy engine error; missing policy for tool. On failure, default SHALL be block. |
| **Logged artifacts** | At least: for each action, `action_id`, `risk_score`, `risk_label`, `policy_reason`, `decision`. |

**Requirement.** Every action SHALL receive a risk evaluation. Any action without a valid evaluation SHALL be treated as blocked.

---

### 2.4 Stabilization Phase

| Aspect | Contract |
|--------|----------|
| **Inputs** | Plan; per-action risk results; stabilization policy (which mechanisms apply to which risk labels). |
| **Outputs** | Stabilized plan: for each action, either unchanged, modified (with `modified_action` and `stabilization_mechanism`), or removed (blocked). |
| **Failure modes** | Stabilization timeout; mechanism error (e.g. sanitization failure). On mechanism error, the action SHALL be blocked. |
| **Logged artifacts** | Per stabilized item: `original_action`, `risk_score`, `policy_reason`, `modified_action` (if any), `decision_type` (allow, allow_modified, block), `stabilization_mechanism` (if allow_modified). See Section 3.3. |

**Requirement.** All modifications SHALL be logged before execution. No silent modification.

---

### 2.5 Execution Adapter Invocation

| Aspect | Contract |
|--------|----------|
| **Inputs** | Stabilized plan (only allow and allow_modified actions); sandbox configuration; timeout. |
| **Outputs** | Execution result: `run_id`, `status` (completed, timeout, error), `completed_action_count`, `results[]` (per action: `action_id`, `adapter_status`, `output_hash` or error). |
| **Failure modes** | Adapter crash; timeout; sandbox integrity breach (see Section 4.5); one or more actions fail. |
| **Logged artifacts** | At least: `run_id`, `status`, `completed_action_count`, `execution_start_ts_utc`, `execution_end_ts_utc`. Per action: `action_id`, `adapter_status`. |

**Requirement.** Only actions that received decision `allow` or `allow_modified` SHALL be passed to the adapter. Blocked actions SHALL NOT be executed.

---

### 2.6 Post-Execution State Validation

| Aspect | Contract |
|--------|----------|
| **Inputs** | Execution result; expected state (if any); sandbox state snapshot after execution. |
| **Outputs** | Validation result: `integrity_ok` (boolean), `state_hash_after`, optional `expected_vs_actual` summary. |
| **Failure modes** | State snapshot failure; hash mismatch with expectation (if expectation exists). |
| **Logged artifacts** | At least: `integrity_ok`, `state_hash_after`. Optionally: `state_hash_before`, diff summary. |

**Requirement.** If `integrity_ok` is false, the run SHALL be marked as sandbox integrity breach (see Section 4.5) and SHALL be logged accordingly.

---

### 2.7 Receipt + Event Logging

| Aspect | Contract |
|--------|----------|
| **Inputs** | All outputs from previous stages; run-level identifiers; envelope fields. |
| **Outputs** | Immutable receipt record(s) and/or execution event log entry; run envelope (see Section 6). |
| **Failure modes** | Log write failure; disk full. On failure, the run SHALL be considered incomplete and SHALL be marked in the envelope. |
| **Logged artifacts** | Run envelope (schema_version 1.2 per Section 6); execution_event records per schema Section 6.2; receipt or equivalent per-case/per-action as required by measurement contract. |

**Requirement.** Logging SHALL be append-only for event log and receipt. Envelope SHALL be written atomically (e.g. write to .tmp, fsync, rename to final path).

---

## SECTION 3 — Stabilization Contract

### 3.1 Action Classification

**Requirement.** The following classifications SHALL be defined and used in Pre-Execution Risk Evaluation and Stabilization:

1. **Unsafe action.**  
   - Definition: An action that, if executed as-is, would violate policy or sandbox boundaries (e.g. tool on blocklist, argument references path outside sandbox, or known harmful pattern).  
   - Required treatment: SHALL NOT be executed. SHALL be logged with `decision_type: block`.

2. **Risky but remediable action.**  
   - Definition: An action that has measurable risk (e.g. writes to sandbox, or uses a tool that can be constrained) but can be made safe by modification (argument sanitization, scope reduction, tool substitution).  
   - Required treatment: MAY be executed only after successful stabilization. SHALL be logged with `decision_type: allow_modified` and the mechanism used.

3. **Benign action.**  
   - Definition: An action that meets policy and sandbox constraints as-is (e.g. allowlisted tool, arguments within scope).  
   - Required treatment: MAY be executed unchanged. SHALL be logged with `decision_type: allow`.

**Rationale.** Clear labels allow consistent metrics (e.g. harmful_action_prevented_count) and audit.

**Assumption.** The policy engine can assign exactly one of these labels (or equivalent) per action; no "unknown" that is executed.

---

### 3.2 Stabilization Mechanisms

**Requirement.** The following mechanisms SHALL be supported. A stabilization step MAY use one or more.

1. **Plan rewriting.** Replace the action with a different action (e.g. different tool or no-op) while preserving plan_id/order for logging.
2. **Argument sanitization.** Transform arguments to remove or escape dangerous values (e.g. path traversal, shell metacharacters).
3. **Scope reduction.** Restrict the action to a subset of the requested scope (e.g. limit to a single directory).
4. **Tool substitution.** Replace the requested tool with a safer tool that satisfies the intent within policy (e.g. replace generic write with append-only write).
5. **Full block.** Do not execute the action; treat as blocked. SHALL be logged as `decision_type: block`.

**Requirement.** Each application of a mechanism SHALL be logged as in Section 3.3.

---

### 3.3 Required Logging for Each Stabilization

**Requirement.** For every action that is evaluated and/or stabilized, the following fields SHALL be recorded:

| Field | Type | Description |
|-------|------|-------------|
| `original_action` | object | The action as produced by Plan Generation (or a stable reference/hash). |
| `risk_score` | number or string | Value from Pre-Execution Risk Evaluation. |
| `policy_reason` | string | Human- or machine-readable reason (e.g. allowlist match, blocklist match, path out of scope). |
| `modified_action` | object or null | The action after stabilization; null if blocked or allowed unchanged. |
| `decision_type` | enum | One of: `allow`, `allow_modified`, `block`. |

**Requirement.** If `decision_type` is `allow_modified`, the log SHALL also include:

| Field | Type | Description |
|-------|------|-------------|
| `stabilization_mechanism` | string or array | One or more of: `plan_rewriting`, `argument_sanitization`, `scope_reduction`, `tool_substitution`. |

**Rationale.** Enables computation of stabilization_intervention_rate and audit of what was changed and why.

---

## SECTION 4 — Sandbox Contract

### 4.1 Sandboxed Filesystem Behavior

**Requirement.**

1. The execution adapter SHALL have access only to a designated **sandbox root** directory (or equivalent namespace). All readable and writable paths SHALL be within this root.
2. Path resolution SHALL treat paths that escape the sandbox root (e.g. `../` outside root) as invalid; such actions SHALL be blocked or sanitized before execution.
3. Optional: read-only mounts or allowlists for specific paths outside the sandbox may be defined by configuration; such paths SHALL be explicitly listed and SHALL NOT be writable.

**Rationale.** Prevents accidental or malicious writes to host or sensitive paths.

---

### 4.2 Sandboxed Network Behavior

**Requirement.**

1. By default, the sandbox SHALL allow **no** real outbound network connections (no TCP/UDP to external endpoints).
2. If network is allowed, it SHALL be through a controlled mechanism (e.g. mock, proxy, or allowlisted host list) that does not reach arbitrary external endpoints unless explicitly configured.
3. Any network use SHALL be logged (e.g. attempted host, result).

**Rationale.** Prevents exfiltration and unauthorized external communication.

---

### 4.3 State Hashing Requirements

**Requirement.**

1. **Sandbox state** SHALL be represented in a form that can be hashed (e.g. file tree hash, or manifest of paths and content hashes).
2. The hash function SHALL be SHA-256 (or a stronger standard agreed in configuration).
3. At least two hashes SHALL be produced per run: **sandbox_state_hash_before** (before Execution Adapter Invocation) and **sandbox_state_hash_after** (after execution and before teardown). See Section 6.

**Rationale.** Enables reproducibility and integrity checks.

---

### 4.4 Required Before/After State Snapshots

**Requirement.**

1. **Before execution:** A snapshot of sandbox state (or its hash) SHALL be taken and recorded as `sandbox_state_hash_before` (and optionally full snapshot path).
2. **After execution:** A snapshot of sandbox state (or its hash) SHALL be taken and recorded as `sandbox_state_hash_after`.
3. Snapshots SHALL be taken by the same procedure so that hashes are comparable across runs (same algorithm, same scope).

**Rationale.** Enables detection of unexpected changes and supports reproducibility.

---

### 4.5 Sandbox Integrity Breach

**Requirement.** A **sandbox integrity breach** SHALL be declared when any of the following occurs:

1. The execution adapter reads or writes outside the designated sandbox root (or allowed read-only list).
2. The execution adapter establishes a network connection to a disallowed endpoint.
3. The execution adapter invokes a tool or capability not in the allowed set for the run.
4. Post-Execution State Validation reports `integrity_ok: false` due to state hash or invariant check failure.
5. The sandbox runtime detects a violation (e.g. privilege escalation, resource limit exceeded in a way that indicates escape).

**Requirement.** On breach, the run SHALL be terminated, SHALL NOT be considered successful, and SHALL be logged with a breach reason and included in `sandbox_integrity_breach_rate` (Section 5).

---

## SECTION 5 — Measurement Contract

**Requirement.** The following metrics SHALL be defined and computed exactly as below. All counts and rates are over a single **run** or over a **set of runs** (e.g. a benchmark suite). Denominators SHALL be defined so that division is only by positive integers where applicable.

### 5.1 plan_drift_detected_rate

**Formula:**

```
plan_drift_detected_rate = (number of runs where plan was modified by stabilization) / (total runs with at least one action)
```

**Definition.** Proportion of runs in which at least one action was modified (allow_modified) or blocked. If a run has zero actions, it is excluded from the denominator.

---

### 5.2 stabilization_intervention_rate

**Formula:**

```
stabilization_intervention_rate = (total actions with decision_type == "allow_modified" or "block") / (total actions evaluated)
```

**Definition.** Proportion of actions that required intervention (modified or blocked). Denominator: all actions produced by Plan Generation and evaluated in Pre-Execution Risk Evaluation.

---

### 5.3 harmful_action_prevented_count

**Formula:**

```
harmful_action_prevented_count = (number of actions with decision_type == "block" and risk_label == "unsafe")
```

**Definition.** Count of actions classified unsafe and blocked. Sum over the relevant run(s).

---

### 5.4 execution_allowed_rate

**Formula:**

```
execution_allowed_rate = (number of actions with decision_type in {"allow", "allow_modified"} that were passed to the adapter) / (total actions evaluated)
```

**Definition.** Proportion of actions that were actually sent to the Execution Adapter (after stabilization).

---

### 5.5 benefit_completion_rate

**Formula:**

```
benefit_completion_rate = (number of actions that completed successfully per adapter) / (number of actions passed to the adapter)
```

**Definition.** Proportion of executed actions that completed without timeout or adapter error. "Successfully" is defined by the adapter (e.g. exit code 0 or equivalent).

---

### 5.6 sandbox_integrity_breach_rate

**Formula:**

```
sandbox_integrity_breach_rate = (number of runs with at least one sandbox integrity breach) / (total runs executed)
```

**Definition.** Proportion of runs in which a sandbox integrity breach was declared (Section 4.5).

---

### 5.7 risk_score_distribution

**Formula:**

```
risk_score_distribution = { risk_label: count of actions with that risk_label }
```

**Definition.** For each run or set of runs, a mapping from risk_label (e.g. unsafe, risky, benign) to the count of actions that received that label. Optionally, if risk_score is numeric, bins (e.g. [0, 0.25), [0.25, 0.5), [0.5, 1.0]) may be used and the distribution reported as counts per bin.

**Requirement.** The exact set of risk_label values SHALL be defined by the policy configuration and SHALL be documented.

---

## SECTION 6 — Reproducibility Contract

### 6.1 Required Envelope Expansion (schema_version 1.2)

**Requirement.** The run-level envelope SHALL support schema_version **1.2** with at least the following fields in addition to any from 1.1:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | `"1.2"` |
| `run_id` | string | yes | Unique run identifier. |
| `run_instance_id` | string | yes | Unique instance (e.g. timestamp-based). |
| `suite` | string | yes | Suite or scenario id. |
| `model_id` | string | optional | Model identifier if applicable. |
| `backend` | string | optional | Backend identifier. |
| `seed` | number | optional | Random seed if applicable. |
| `lane` | string | optional | Lane identifier if applicable. |
| `variant` | string | optional | Variant identifier. |
| `git_commit` | string | optional | Repo commit at run time. |
| `suite_sha256` | string | optional | SHA256 of suite definition. |
| `llm_config_sha256` | string | optional | SHA256 of LLM config if used. |
| `timeout_per_case` | number | optional | Timeout per case/action in seconds. |
| `total_cases_expected` | number | yes | Expected number of cases or actions. |
| `total_cases_completed` | number | yes | Completed count. |
| `run_start_ts_utc` | string | yes | ISO 8601 start time. |
| `run_end_ts_utc` | string | yes | ISO 8601 end time. |
| `exit_status` | string | yes | One of: normal, incomplete, timeout, exception, external_kill, sandbox_breach. |
| `determinism_hash` | string | optional | Hash of canonical outcome representation. |
| `receipt_path` | string | optional | Path to receipt file. |
| `receipt_sha256` | string | optional | SHA256 of receipt file. |
| `sandbox_state_hash_before` | string | yes (for 1.2) | SHA256 of sandbox state before execution. |
| `sandbox_state_hash_after` | string | yes (for 1.2) | SHA256 of sandbox state after execution. |
| `execution_log_hash` | string | yes (for 1.2) | SHA256 of execution event log (canonical serialization). |

**Rationale.** Envelope 1.2 extends 1.1 with sandbox and execution-log hashes for reproducibility and integrity.

---

### 6.2 Required execution_event Schema

**Requirement.** Each execution event (one per action execution or per lifecycle stage transition, as defined by the implementation) SHALL be representable in a structure that includes at least:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | string | yes | Unique event id. |
| `run_id` | string | yes | Run this event belongs to. |
| `stage` | string | yes | One of: task_intake, plan_generation, risk_evaluation, stabilization, adapter_invocation, state_validation, receipt_logging. |
| `action_id` | string | optional | Action id if applicable. |
| `ts_utc` | string | yes | ISO 8601 timestamp. |
| `decision_type` | string | optional | allow, allow_modified, block. |
| `adapter_status` | string | optional | Status from adapter for this action. |
| `payload_hash` | string | optional | Hash of event payload for integrity. |

**Requirement.** The execution event log SHALL be serialized in a deterministic order (e.g. by ts_utc then event_id) for the purpose of computing `execution_log_hash`.

---

### 6.3 Determinism Guarantees

**Requirement.**

1. **Reproducibility scope:** Given the same task, same model/backend, same seed, same suite and config hashes, and same sandbox initial state, the system SHALL aim to produce the same `determinism_hash` (and same risk decisions) where the design allows. Non-determinism (e.g. from model sampling) SHALL be documented; timestamps and run_instance_id SHALL be excluded from determinism hash input.
2. **Hash inputs:** `determinism_hash` SHALL be computed over a canonical representation of outcomes (e.g. case_id, decision, executed tools, pass/fail) excluding variable fields such as timestamps and instance ids.
3. **Sandbox hashes:** `sandbox_state_hash_before` and `sandbox_state_hash_after` SHALL be computed over the same scope and algorithm so that identical state yields identical hashes.

**Assumption.** Some components (e.g. LLM) may be non-deterministic; the contract requires that what *can* be deterministic (decisions, execution order, state hashes) is defined and hashed consistently.

---

### 6.4 Required Hashes

**Requirement.** The following hashes SHALL be produced and stored (in envelope and/or event log) as specified:

1. **sandbox_state_hash_before** — SHA-256 of sandbox state before Execution Adapter Invocation. Required in envelope 1.2.
2. **sandbox_state_hash_after** — SHA-256 of sandbox state after execution. Required in envelope 1.2.
3. **execution_log_hash** — SHA-256 of the canonical serialization of the execution event log for the run. Required in envelope 1.2.

**Requirement.** Hash algorithm SHALL be SHA-256 unless a different standard is explicitly configured and documented.

---

## SECTION 7 — Explicit Limitations

**Requirement.** The following limitations SHALL be stated and acknowledged.

### 7.1 What This Specification Cannot Prove

- **General safety of any model or agent.** Compliance with this specification does not prove that a model or agent is safe in open-world or unconstrained environments.
- **Absence of all vulnerabilities.** The contract reduces and measures known risks; it does not guarantee absence of unknown attack vectors or implementation bugs.
- **Fitness for any particular regulation.** This is a technical governance contract; legal or regulatory compliance requires separate analysis.

### 7.2 What Real-World Execution Still Requires

- **Human oversight.** Decisions to deploy autonomous execution in production, and handling of breach or anomaly, may require human review.
- **Operational controls.** Monitoring, alerting, key management, and incident response are outside this specification.
- **Environment hardening.** Host OS, network, and deployment security are assumed to be handled elsewhere.

### 7.3 Known Risks

- **Policy and allowlist correctness.** Incorrect or incomplete policy can allow harmful actions or over-block benign ones.
- **Sandbox implementation bugs.** A bug in the sandbox (e.g. path resolution, namespace isolation) can undermine the sandbox contract.
- **Logging and hashing coverage.** Gaps in what is logged or hashed can reduce auditability and reproducibility.

### 7.4 Known Unknowns

- **Long-term stability of hashes and formats.** Schema and hash semantics may need to evolve; versioning and migration are not fully specified here.
- **Performance and scalability.** This specification does not define latency or throughput requirements; large plans or high frequency may require additional design.
- **Multi-tenant or concurrent runs.** Isolation between concurrent runs and shared sandbox state are not fully specified.

---

**End of Calyx Autonomous Governance Specification v0.1**
