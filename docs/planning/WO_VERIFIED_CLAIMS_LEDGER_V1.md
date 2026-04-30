---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_VERIFIED_CLAIMS_LEDGER_V1

**Status:** Implemented 2026-02-27
**Trigger:** Mandatory postcondition verification for side-effect claims; no silent success

---

## Objective

Establish mandatory postcondition verification for all side-effect claims. No side effect may be claimed without verification.

---

## Doctrine

- No side effect may be claimed without verification.
- Verification must be deterministic, produce auditable evidence, emit explicit verified/failed events.
- Prevent "silent success."

---

## Event Types (VCL)

| Event | When |
|-------|------|
| claim.attempted | Before attempting a claim |
| claim.verified | After verification passes |
| claim.failed | When verification fails |

All include: `claim_type`, `artifact_path` (optional), `sha256` (optional), `reason` (if failed), `corr_id`.

---

## CRH Claim Lifecycle

1. `claim.attempted` (claim_type=canonical_hash)
2. `response.canonical_hash`
3. Receipt file: create dir, write, verify exists, size > 0, compute sha256
4. `claim.verified` (or `claim.failed` on any step)

---

## Sunrise Preflight

On sunrise (startup script + CBO Core lifespan):

- Verify/create: `runtime/ledger/`, `runtime/receipts/`, `runtime/receipts/canonical/`
- If missing after create: emit `station.preflight.failed`, exit non-zero

---

## Governance Assertion

If `canonical_response_mode == true` and first valid request produces `claim.failed` (no `claim.verified`):

- Emit `governance.assertion.failed`
- FE candidate auto-suggested (appended to FAILURE_EVENT_LOG.md)

---

## FE Log Integration

On `claim.failed`:

- Append FE candidate to `docs/operations/FAILURE_EVENT_LOG.md`
- Include: claim_type, corr_id, reason, timestamp, artifact_path

---

## Implementation

| Component | Location |
|-----------|----------|
| Verified claims | `calyx/kernel/verified_claims.py` |
| CRH integration | `cbo_hub/cbo_core/app.py` — `_emit_canonical_hash` |
| Preflight | `cbo_hub/cbo_core/app.py` — `_run_sunrise_preflight` |
| Startup script | `Scripts/start_calyx_core_services.ps1` |

---

## Validation Protocol

1. Sunrise.
2. Trigger one HEARTBEAT request.
3. Expect sequence: `human.request.received` → `intent.classified` → `fastpath.used` → `claim.attempted` → `response.canonical_hash` → `claim.verified` → `response.finalized` (no `claim.failed`).
4. If `claim.failed` appears: stop, log FE entry, do not continue parity testing.

---

## Example Ledger Trace (Successful)

```
human.request.received
intent.classified (INTENT_HEARTBEAT)
fastpath.used
heartbeat.fastpath
claim.attempted (canonical_hash)
response.canonical_hash
claim.verified (artifact_path, sha256)
response.finalized
```

---

## Simulated Failure Test

To test claim.failed: temporarily rename `runtime/receipts/canonical` before a request. CBO Core will create it on next request; to force failure, make the parent `runtime/receipts` read-only (or remove write permission) so mkdir fails. Expect: `claim.failed`, `governance.assertion.failed`, FE entry appended.
