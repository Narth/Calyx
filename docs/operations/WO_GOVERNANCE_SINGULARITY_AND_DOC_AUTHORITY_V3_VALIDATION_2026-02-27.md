---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_GOVERNANCE_SINGULARITY_AND_DOC_AUTHORITY_V3 — Validation Report

**Date:** 2026-02-27

---

## Part I — Envelope-Based Deprecated Doc Override

| Criterion | Status |
|-----------|--------|
| doc_policy in envelope schema | ✅ Optional `doc_policy: {include_deprecated, reason, scope}` |
| Envelope override works | ✅ Extract from X-Calyx-Sign-Envelope when verified |
| Legacy token (migration) | ✅ INCLUDE_DEPRECATED_DOCS=TRUE when DOC_OVERRIDE_STRICT_MODE=false |
| Strict mode | ✅ DOC_OVERRIDE_STRICT_MODE=true rejects token |
| audit.doc.override.requested | ✅ source: envelope \| legacy_token |
| audit.doc.override.legacy_token_used | ✅ When token used |
| audit.doc.override.rejected_legacy | ✅ When strict mode rejects |
| audit.doc.read includes override_deprecated, override_source | ✅ |

---

## Part II — Runtime Heartbeat Singularity

| Criterion | Status |
|-----------|--------|
| audit.runtime.singularity.confirmed | ✅ On gateway startup when heartbeat enabled |
| audit_health singularity checks | ✅ Multiple senders → mismatch; singularity.confirmed count |
| Legacy sender | N/A — OpenClaw (external); documented in OPENCLAW_CALYX_INTEGRATION |
| Validation ladder | `docs/operations/WO_GOVERNANCE_SINGULARITY_V3_LADDER.md` |
| Ladder runner | `python Scripts/wo_v3_ladder.py` |

---

## Config

- `DOC_OVERRIDE_STRICT_MODE` — when true, legacy token rejected
- Envelope `doc_policy`: `{ "include_deprecated": true, "scope": "repo_search_only", "reason": "..." }`
