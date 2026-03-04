# Governance Determinism Hash (GDH) v0.1 — Schema Spec

## Purpose

GDH provides a **stable, content-addressable fingerprint** of governance-relevant outcomes from benchmark receipt JSONL files. It is used to compare exports across nodes or runs without relying on timestamps, paths, or raw model output.

## Scope

- **Input:** Export root containing receipt JSONL for suites `protocol_probe_v0_1` (Lane 1) and `prompt_injection_v0_2` (Lane 2).
- **Output:** A GDH report with a top-level run hash and per-seed, per-suite hashes.

## Canonical Record (per case)

Only **stable, governance-relevant** fields from receipts are included. Excluded: timestamps, file paths, `llm_response_hash`, raw model output, `ts_utc`, `git_commit`, `run_id`, and any node-specific identifiers.

| Field | Type | Description |
|-------|------|-------------|
| seed | integer | Benchmark seed. |
| suite_id | string | e.g. `protocol_probe_v0_1`, `prompt_injection_v0_2`. |
| lane | integer | 1 or 2 (derived from suite). |
| case_id | string | Case/probe identifier. |
| tool_calls_attempted | array | Canonicalized: each item `{name, args}` with sorted keys; list sorted by canonical JSON. |
| llm_parse_ok | boolean | Parse succeeded. |
| protocol_compliant | boolean | Lane 1: per-case compliance; Lane 2: case passed and no forbidden tool executed. |
| forbidden_tool_executed | boolean | Any executed tool not in allowlist. |

## Canonicalization Rules

- **JSON:** UTF-8, sort_keys=True, no extra whitespace (e.g. `separators=(',', ':')`).
- **Lists:** `tool_calls_attempted` sorted by the canonical JSON string of each element (so order is deterministic).
- **Case order:** Preserve receipt order (suite-defined case order).

## Hash Hierarchy

1. **gdh_case** — SHA256 of the canonical JSON of one case record.
2. **gdh_suite** — SHA256 of the canonical JSON of the ordered list of `gdh_case` hashes for that seed+suite.
3. **gdh_run** — SHA256 of the canonical JSON of the structure: `{ "export_root": "<path>", "per_seed": { "<seed>": { "<suite_id>": { "gdh_suite": "<hash>", "gdh_case_hashes": ["...", ...] } } } }` (or equivalent stable structure).

## Report Output (JSON)

- `export_root`: input path.
- `gdh_run`: top-level run hash.
- `per_seed`: for each seed, per suite: `gdh_suite`, `gdh_case_hashes` (ordered), and an optional summary (e.g. counts of fields used).

## Version

- **Schema version:** 0.1
- **Stable:** No timestamps or node-specific values in canonical record.
