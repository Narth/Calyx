# GDH v0.4 — Split: Action Hash vs Temperament Hash

## Purpose

Split system-mode (v0.3) hashing into two **orthogonal** hashes:

- **gdh_action:** Shared “system wavelength” — should match across nodes when decisions and accepted actions align. Excludes impulse/telemetry (violation_flags).
- **gdh_temperament:** Impulse/attempt telemetry — expected to differ across nodes when models attempt different non-allowlisted tools or different numbers of violations.

## Relation to v0.3

- **v0.3 (system):** One canonical record per case including both system_decision/accepted_tool_calls and violation_flags; one gdh_suite and gdh_run.
- **v0.4 (system_split):** Two canonical records per case (action-only and temperament-only), yielding **gdh_action_suite** / **gdh_action_run** and **gdh_temperament_suite** / **gdh_temperament_run**. Case counts and **cases_with_violation_flags** are still reported but are **not** part of the action hash.

## Action canonical record (hashed for gdh_action)

Fields only that describe the system decision and accepted actions. **violation_flags are excluded.**

| Field | Type | Description |
|-------|------|-------------|
| seed | integer | Benchmark seed. |
| suite_id | string | Suite identifier. |
| lane | integer | 1 or 2. |
| case_id | string | Case identifier. |
| system_decision | string | REJECT_PARSE \| NO_TOOL \| ACCEPT. |
| accepted_tool_calls_canonical | array | Present only when system_decision = ACCEPT; same format as v0.3. |
| forbidden_tool_executed | boolean | Any executed tool not in allowlist. |

Canonicalization rules unchanged (sort_keys, deterministic list order). Case order = receipt order.

## Temperament canonical record (hashed for gdh_temperament)

Fields only that describe impulse/attempt telemetry. Used to detect **how** nodes diverged (which violations, which cases).

| Field | Type | Description |
|-------|------|-------------|
| seed | integer | Benchmark seed. |
| suite_id | string | Suite identifier. |
| lane | integer | 1 or 2. |
| case_id | string | Case identifier (preserves ordering). |
| violation_flags | array of strings | Sorted list (e.g. ATTEMPTED_NOT_ALLOWLISTED:&lt;name&gt;). |

Case order = receipt order. Same canonicalization (sorted violation_flags, sort_keys).

## Run-level hash construction

- **gdh_action_run:** SHA256 of the canonical JSON of:
  `{ "export_root": "<path>", "per_seed": { "<seed>": { "<suite_id>": { "gdh_action_suite": "<hash>", "gdh_action_case_hashes": ["...", ...] } } } }`
  with seeds and suites sorted.

- **gdh_temperament_run:** SHA256 of the canonical JSON of:
  `{ "export_root": "<path>", "per_seed": { "<seed>": { "<suite_id>": { "gdh_temperament_suite": "<hash>", "gdh_temperament_case_hashes": ["...", ...] } } } }`
  with seeds and suites sorted.

## Report output (system_split mode)

- **gdh_action_run**, **gdh_temperament_run**
- **per_seed:** For each seed and suite:
  - **gdh_action_suite**, **gdh_temperament_suite**
  - **case_count**
  - **cases_with_violation_flags** (reported only; not part of action hash)

## Version

- **Schema version:** 0.4 (system_split)
- **Stable:** No timestamps or node-specific values in canonical records.
