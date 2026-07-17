---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_EQUIVALENCE_SCOPE_V3

**Status:** Implemented 2026-02-27
**Trigger:** FE-2026-02-27-5 — governance_required variance broke parity; no ungoverned human ingress

---

## Objective

Enforce governance-consistent canonical equivalence across all human entry points. No ungoverned human ingress when governance is required.

---

## Doctrine

- Every human request must pass through governance when CALYX_GOVERNANCE_REQUIRED=true.
- Equivalence hash reflects governance — governance must be uniform.
- We eliminate governance variance, not remove governance from equivalence.

---

## Structural Changes

### 1. Governance Gate (before intent)

When `CALYX_GOVERNANCE_REQUIRED=true` (env):

- Request without X-Calyx-Source from trusted gateway → HTTP 403 + `governance.auth.required`
- No intent classification for rejected requests
- Trusted gateways: `openclaw`, `calyx-discord-gateway`, `openclaw_bridge`

### 2. Ledger Events (before intent)

| Event | When |
|-------|------|
| governance.auth.verified | Request from trusted gateway |
| governance.signature_missing | Direct ingress, no gateway, governance required |
| governance.signature_invalid | X-Calyx-Signature present but invalid (future) |
| governance.ungoverned_ingress_detected | Ungoverned request rejected |
| governance.auth.required | 403 detail |

### 3. Equivalence Bundle (crh.equiv.v2)

Added to equivalence bundle:

- `auth_verified`: true/false
- `signer_fingerprint`: `gateway:{source}` or `ungoverned`

Same request, same evidence, same governance authorization state → same equivalence hash.

---

## Configuration

| Env | Default | Effect |
|-----|---------|--------|
| CALYX_GOVERNANCE_REQUIRED | false | true = gate active; direct /chat → 403. Set in CBO Core process env before startup. |

**To enforce:** Set `CALYX_GOVERNANCE_REQUIRED=true`, restart CBO Core. Direct browser/API will get 403. Only Discord (and other gateways with X-Calyx-Source) will succeed.

---

## Validation Protocol

1. **Unsigned request (governance required):** Browser /chat without X-Calyx-Source → 403, `governance.auth.required`, no `intent.classified`.
2. **Signed via gateway:** Discord → CBO → parity check within 30s → equivalence_hash identical.
3. **Parity:** response_sha256 identical, equivalence_hash identical, receipt_hash different (expected).

---

## Implementation

| Component | Location |
|-----------|----------|
| Gate | `cbo_hub/cbo_core/app.py` — `_check_governance_auth()` |
| Equivalence bundle | `calyx/kernel/canonical_bundle.py` — `auth_verified`, `signer_fingerprint` |

---

## No Implicit Architect Privilege

Architect must authenticate like any other human. Calyx Sign (or gateway) is the mechanism.
