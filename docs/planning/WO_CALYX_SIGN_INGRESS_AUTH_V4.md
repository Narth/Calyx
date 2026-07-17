---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_CALYX_SIGN_INGRESS_AUTH_V4

**Status:** Implemented 2026-02-27
**Trigger:** Cryptographic governance for direct human ingress; no trust by location

---

## Objective

Per-request signature authorization for direct dev ops ingress (Browser/Cursor/API) without requiring a trusted gateway. Governance remains pre-intent.

---

## Signed Request Envelope (v1)

**Schema:** calyx.sign.req.v1

```json
{
  "schema": "calyx.sign.req.v1",
  "ts_utc": "2026-02-27T18:00:00.000000+00:00",
  "nonce": "uuid4-hex",
  "scope": "chat",
  "normalized_request_sha256": "sha256-of-stripped-user-text",
  "node_id": "optional"
}
```

**Headers:**
- X-Calyx-Signature: base64(SSH signature of canonical JSON envelope)
- X-Calyx-Key-Id: architect (or key alias)
- X-Calyx-Sign-Envelope: base64(canonical JSON envelope)

**Normalization:** Same as CRH — `(user_text or "").strip()`

---

## Verification (pre-intent)

1. Decode envelope
2. Verify schema + required fields
3. Timestamp within ±120s
4. Nonce not in ledger (replay protection)
5. normalized_request_sha256 matches computed hash of received user_text
6. ssh-keygen -Y verify with governance/identities/allowed_signers

---

## Nonce Ledger

- **Location:** runtime/receipts/security/nonce_ledger.jsonl
- **Pruning:** Last 24h or 10000 entries
- **Format:** `{"nonce":"...","key_id":"...","ts":"..."}` per line

---

## Ledger Events

| Event | When |
|-------|------|
| governance.signature_verified | Signature valid |
| governance.signature_invalid | Decode/schema/timestamp/hash/verify failed |
| governance.signature_missing | No signature headers |
| governance.signature_replay_detected | Nonce seen before |
| governance.auth.verified | mode=gateway or mode=signature |

---

## CLI

```powershell
python Scripts/calyx_sign_request.py "Produce the latest Station heartbeat." [--key-path PATH] [--key-id architect]
```

Output: headers for Curl/Postman. Key path default: V:/calyx_identity/architect_ed25519 (env CALYX_SIGN_KEY_PATH).

---

## Equivalence

signer_fingerprint for equivalence remains "governed" (gateway and signature paths equivalent). Full signer identity in receipt only.
