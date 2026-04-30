---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_CALYX_SIGN_INGRESS_AUTH_V4 — Validation Report

**Date:** 2026-02-26
**Status:** PASS

---

## Environment

- `CALYX_GOVERNANCE_REQUIRED=true`
- CBO Core on 127.0.0.1:7778
- Test key: `runtime/test_keys/architect_ed25519` (architect-test in allowed_signers for validation)

---

## Test 1 — Ungoverned Direct Rejection

**Action:** POST /chat without gateway header and without signature.

**Result:** HTTP 403, detail `governance.auth.required`

**Ledger:**
- `governance.signature_missing`
- `governance.ungoverned_ingress_detected`
- `governance.auth.required`

**Intent classified:** No (pre-intent rejection)

---

## Test 2 — Signed Direct Acceptance

**Action:** POST /chat with valid X-Calyx-Signature, X-Calyx-Key-Id, X-Calyx-Sign-Envelope.

**Result:** HTTP 200, heartbeat response returned

**Ledger:**
- `governance.signature_verified` (auth_mode=signature, key_id=architect-test)
- `governance.auth.verified` (auth_mode=signature, signer_fingerprint=key:architect-test)
- `intent.classified` (INTENT_HEARTBEAT)
- `cbo.chat.complete`

---

## Test 3 — Replay Rejection

**Action:** Re-send exact same signed request (same nonce).

**Result:** HTTP 403, detail `governance.auth.required`

**Ledger:**
- `governance.signature_replay_detected` (nonce_sha256, key_id)
- `governance.auth.required` (reason=replay)

**Intent classified:** No

---

## Test 4 — Parity (Signature vs Gateway)

**Action:** Same heartbeat prompt via:
1. X-Calyx-Source: calyx-discord-gateway
2. Signed direct /chat (fresh nonce)

**Result:**
- `response_sha256`: identical (`29520a8f693edcadbfac34f7b581e5d45eda2912a2ea5df52b7f6c7cc37dc17a`)
- `equivalence_hash_sha256`: identical (`24f27f5f3d08f580dc5d5ccc0026ce86798be6ec9af1a010154bbb3d5f8e9981`)
- `receipt_sha256`: differs (expected — different auth_mode, signer_fingerprint)

---

## Confirmation

- Governance check remains pre-intent everywhere
- No ungoverned direct requests reach intent classification under `CALYX_GOVERNANCE_REQUIRED=true`
- Signed direct requests accepted and replay-protected
- Parity between signed direct and gateway requests proven via equivalence hash
