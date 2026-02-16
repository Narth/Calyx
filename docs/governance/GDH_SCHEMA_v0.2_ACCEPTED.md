# GDH v0.2 — Accepted-Plan Hash (Schema Addendum)

## Purpose

This addendum defines a GDH variant that hashes **accepted governance outcomes** (what the policy accepts) rather than raw model-attempted tool calls. It supports comparing determinism of *decisions* and *accepted tool calls* across nodes.

## Relation to v0.1

- **v0.1 (attempted):** Canonical record includes `tool_calls_attempted`, `llm_parse_ok`, `protocol_compliant`, `forbidden_tool_executed`. Hashes reflect what the model *attempted*.
- **v0.2 (accepted):** Canonical record includes `decision`, `reason_codes`, `accepted_tool_calls`, and optional forbidden/unauthorized flags. Hashes reflect what the governance layer *accepts*.

## Accepted Tool Calls

**accepted_tool_calls** = tool calls that are:

1. **Parseable** — Envelope parsed (`llm_parse_ok` true); otherwise no calls are accepted.
2. **Schema-valid** — Each item has non-null tool name and valid `args` (dict).
3. **Allowlisted** — Tool name is in the policy allowlist (e.g. `fs_read`, `fs_list`, `repo_grep`).
4. **Per-case expectations** — When the suite defines tool-required vs no-tool:
   - **No-tool cases** (e.g. Lane 1 `probe_no_tool`): zero calls are accepted; any attempt yields `accepted_tool_calls = []`.
   - **Tool-required cases**: only allowlisted, schema-valid calls are accepted; at least one accepted call implies decision ACCEPT.

Canonical form of `accepted_tool_calls` is the same as v0.1 `tool_calls_attempted`: each element `{ "name": "<tool>", "args": { ... } }` with sorted keys; list sorted by canonical JSON.

## Decision Enum

| Value | Meaning |
|-------|---------|
| **ACCEPT** | Parse OK and at least one tool call accepted (allowlisted, schema-valid, and per-case expectation met). |
| **NO_TOOL** | Parse OK, no tool calls attempted (or none passed the filter), and no-tool case or non–tool-required case where zero is valid. |
| **REJECT_PARSE** | Parse failed (`llm_parse_ok` false). `accepted_tool_calls = []`. |
| **REJECT_POLICY** | Parse OK but no accepted calls due to policy: e.g. all attempted were not allowlisted, or a no-tool case had attempted calls. |

## Reason Codes

**reason_codes** = sorted list of string codes explaining the decision. Used for debugging and forensics.

Examples (non-exhaustive):

- `PARSE_FAIL` — Envelope parse failed.
- `NOT_ALLOWLISTED` — One or more attempted tools not in allowlist.
- `NO_TOOL_EXPECTED` — Suite expects no tool (e.g. no-tool case) but at least one was attempted.
- (Future: `SCHEMA_INVALID`, per-suite codes.)

Canonical form: **sorted** list of strings (e.g. `["NOT_ALLOWLISTED", "PARSE_FAIL"]`) so that order is deterministic.

## Canonical Record (v0.2 accepted mode)

| Field | Type | Description |
|-------|------|-------------|
| seed | integer | Benchmark seed. |
| suite_id | string | e.g. `protocol_probe_v0_1`, `prompt_injection_v0_2`. |
| lane | integer | 1 or 2. |
| case_id | string | Case identifier. |
| decision | string | One of: `ACCEPT`, `NO_TOOL`, `REJECT_PARSE`, `REJECT_POLICY`. |
| reason_codes | array of strings | Sorted list of reason codes. |
| accepted_tool_calls | array | Canonicalized list of accepted tool calls (same format as v0.1 attempted). |
| forbidden_tool_executed | boolean | (Optional.) Any executed tool not in allowlist. |

## Hash Hierarchy (unchanged)

Same as v0.1: **gdh_case** → **gdh_suite** → **gdh_run**. Only the content of the canonical record changes (v0.2 fields above).

## Version

- **Schema addendum:** v0.2 (accepted)
- **Stable:** No timestamps or node-specific values in canonical record.
