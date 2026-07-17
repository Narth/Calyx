---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_REQUEST_ORIENTATION_PROTOCOL_V2

**Status:** Implemented 2026-02-27
**Trigger:** FE-2026-02-27-3, FE-2026-02-27-4 (compound query misroute; failure event knowledge path missing)

---

## Objective

Add Compound Intent Handling + Failure Event Knowledge Path. Preserve multi-part human intent; bind knowledge domains to canonical sources.

---

## New Intents (V2)

| Intent | Trigger | Fast Path |
|--------|---------|-----------|
| INTENT_COMPOUND_QUERY | "search for X and which file defines Y" with X ≠ Y | repo_search(X) + repo_search(Y); two-section reply |
| INTENT_FAILURE_EVENT_QUERY | "failure event" + ("what" \| "looks like" \| "format" \| "define" \| "confirm") | Read FAILURE_EVENT_LOG.md; extract format |

---

## Implementation

| Component | Location |
|-----------|----------|
| parse_compound_targets, is_compound_query | `calyx/kernel/intent_orientation.py` |
| _is_failure_event_query | `calyx/kernel/intent_orientation.py` |
| INTENT_COMPOUND_QUERY handler | `cbo_hub/cbo_core/app.py` |
| INTENT_FAILURE_EVENT_QUERY handler | `cbo_hub/cbo_core/app.py` |
| _extract_failure_event_format, _load_failure_event_log | `cbo_hub/cbo_core/app.py` |
| override_ignore_globs | `cbo_hub/dev_harness/app.py` — RepoSearchReq |

---

## Repo Search Override

When query contains "failure event" or "failure_event_log", REPO_SEARCH_IGNORE_GLOBS is disabled for that query. Human explicit reference overrides ignore policies.

---

## Sample Ledger Traces

### Compound Query

```json
{"event":"intent.classified","data":{"intent":"INTENT_COMPOUND_QUERY","entry_point":"browser"}}
{"event":"intent.compound.detected","data":{"x":"failure event","y":"emit","entry_point":"browser"}}
{"event":"repo_search.override_ignore","data":{"query":"failure event"}}
{"event":"fastpath.used","data":{"intent":"INTENT_COMPOUND_QUERY","deterministic_path_used":true,"x":"failure event","y":"emit"}}
{"event":"response.finalized","data":{"intent":"INTENT_COMPOUND_QUERY","deterministic_path_used":true}}
```

### Failure Event Query

```json
{"event":"intent.classified","data":{"intent":"INTENT_FAILURE_EVENT_QUERY","entry_point":"browser"}}
{"event":"failure_event.query.bound","data":{"source":"docs/operations/FAILURE_EVENT_LOG.md"}}
{"event":"fastpath.used","data":{"intent":"INTENT_FAILURE_EVENT_QUERY","deterministic_path_used":true}}
{"event":"response.finalized","data":{"intent":"INTENT_FAILURE_EVENT_QUERY","deterministic_path_used":true}}
```

---

## Validation Protocol

| Test | Expected |
|------|----------|
| "Search for FAILURE EVENT and which file defines emit" | Two-section: Search Target (FAILURE_EVENT_LOG), File Definition (event_ledger.py) |
| "Confirm what a failure event looks like" | Structured format from FAILURE_EVENT_LOG.md; identical across channels |

---

## Edge Cases

1. **event_ledger + emit (same target):** When X=event_ledger and Y=emit, treat as FILE_LOCATION (single intent), not compound.
2. **Compound Y search:** For Y=emit, use query "event_ledger" with glob "**/event_ledger.py".
