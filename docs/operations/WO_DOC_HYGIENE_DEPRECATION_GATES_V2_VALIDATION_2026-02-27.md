---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_DOC_HYGIENE_DEPRECATION_GATES_V2 — Validation Report

**Date:** 2026-02-27
**WO:** Governed Override + Authoritative Status

---

## Acceptance Criteria

| Criterion | Status | Notes |
|-----------|--------|-------|
| Negative: "historical" does NOT include deprecated docs | ✅ | Override only via `INCLUDE_DEPRECATED_DOCS=TRUE` |
| Positive: Explicit token includes deprecated + emits events | ✅ | `audit.doc.override.requested` + `audit.doc.read(..., override_deprecated=true)` |
| Mismatch: header vs registry → preflight flags | ✅ | `audit.doc.status.mismatch` + preflight fails |
| Completeness: All doc reads emit `audit.doc.read` with sha256 | ✅ | FAILURE_EVENT_LOG + repo_search hits |

---

## Implementation Summary

### A) Explicit Override Token

- **Token:** `INCLUDE_DEPRECATED_DOCS=TRUE` (case-insensitive substring match)
- **Removed:** Heuristic triggers (`historical`, `include deprecated`, `deprecated`)
- **Emission:** `audit.doc.override.requested` with `reason`, `scope` (search-only), `corr_id`

### B) Doc Status Registry

- **Path:** `docs/DOC_STATUS_REGISTRY.json`
- **Schema:** `doc_status_registry_v1`
- **Coverage:** `docs/operations/*.md`, `docs/planning/*.md`, `docs/OPENCLAW_CALYX_INTEGRATION.md`
- **Canonical:** Registry overrides in-doc headers; mismatch emits `audit.doc.status.mismatch`

### C) Defensive Defaults

- Registry missing → preflight fails
- Doc not in registry → `audit.doc.status.unknown`, default exclude deprecated
- Unknown status → treat as deprecated for filtering (exclude)

### D) Coverage

- `_load_failure_event_log()` → `audit.doc.read`
- Dev Harness `repo_search` → `audit.doc.read` per unique .md path in hits

---

## Validation Commands

```powershell
# Preflight (doc integrity)
python -c "from pathlib import Path; from calyx.kernel.doc_status import validate_ops_docs; print(validate_ops_docs(Path('.')) or 'pass')"

# Negative: historical does not override
# Query "historical OpenClaw" → deprecated docs excluded

# Positive: explicit token overrides
# Query "INCLUDE_DEPRECATED_DOCS=TRUE OpenClaw" → deprecated docs included, audit.doc.override.requested emitted
```
