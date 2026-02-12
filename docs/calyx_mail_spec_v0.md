# Calyx Mail v0 Specification

**Version:** 0.1.0  
**Date:** 2026-02-12  
**Status:** Read-only content, no side effects

---

## 1. Overview

Calyx Mail v0 is a local-first, end-to-end encrypted messaging system designed for Station Calyx. It provides secure message exchange between agents/components within a single machine or private LAN, with no external network dependencies.

**Core principles:**
- **Local-first:** All operations are filesystem-based; no cloud calls, no external endpoints
- **Read-only content:** Messages in v0 may not trigger execution or tooling
- **Deny-by-default:** Recipients must explicitly allowlist senders
- **Metadata minimization:** Only essential fields in public headers
- **Replay protection:** Message IDs + timestamp windows + seen cache

---

## 2. Terminology

| Term | Definition |
|------|------------|
| **Sender** | Entity creating and signing an envelope. Identified by ed25519 public key fingerprint. |
| **Recipient** | Entity for whom an envelope is encrypted. Identified by x25519 public key fingerprint. |
| **Mailbox** | Filesystem directory containing inbox (received) and outbox (sent) envelopes. |
| **Envelope** | JSON structure containing public header, ciphertext, and signatures. |
| **Receipt** | JSON structure recording delivery/read/failure status for a message. |
| **Fingerprint** | Base64-encoded hash of public key (first 16 bytes of SHA256). |

---

## 3. Threat Model

### 3.1 Threats Addressed

| Threat | Mitigation |
|--------|------------|
| **Spoofing** | ed25519 signature verification on envelope. Recipient checks sender fingerprint against allowlist. |
| **Replay attacks** | Message ID uniqueness check + timestamp window validation + seen cache (pluggable store). |
| **MITM (Man-in-the-Middle)** | x25519 sealed box encryption ensures only recipient with private key can decrypt. |
| **Metadata leakage** | Minimal public header (sender_fp, recipient_fp, msg_id, timestamp, subject). No routing info, no IPs. |
| **Spam/flood** | Deny-by-default allowlist. Recipient controls who can send. |
| **Compromised endpoint** | Keys stored under `runtime/keys/` (git-ignored). Compromise limited to local machine. |
| **Stolen keys** | Key rotation recommended. Old messages remain decryptable with old keys (by design). |

### 3.2 Threats NOT Addressed in v0

- **Forward secrecy:** Old messages remain decryptable if keys are stolen
- **Deniability:** Signatures provide non-repudiation (by design)
- **Network transport:** v0 assumes secure local filesystem transport
- **Key distribution:** Manual key exchange required (no PKI)

---

## 4. Envelope JSON Schema

### 4.1 Structure

```json
{
  "header": {
    "sender_fp": "base64-encoded-ed25519-fingerprint",
    "recipient_fp": "base64-encoded-x25519-fingerprint",
    "msg_id": "unique-message-id-uuid-v4",
    "timestamp": "2026-02-12T10:30:00Z",
    "subject": "optional-subject-line"
  },
  "ciphertext": "base64-encoded-x25519-sealed-box",
  "signature": "base64-encoded-ed25519-signature"
}
```

### 4.2 Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `header.sender_fp` | string (base64) | Yes | Sender's ed25519 public key fingerprint (SHA256 first 16 bytes, base64). |
| `header.recipient_fp` | string (base64) | Yes | Recipient's x25519 public key fingerprint (SHA256 first 16 bytes, base64). |
| `header.msg_id` | string (UUID v4) | Yes | Unique message identifier. Must be unique per sender-recipient pair (enforced by seen cache). |
| `header.timestamp` | string (ISO 8601) | Yes | Message creation time in UTC. Format: `YYYY-MM-DDTHH:MM:SSZ`. |
| `header.subject` | string | No | Optional subject line (plaintext, max 256 chars). |
| `ciphertext` | string (base64) | Yes | x25519 sealed box ciphertext (encrypted plaintext + nonce). |
| `signature` | string (base64) | Yes | ed25519 signature over `header` + `ciphertext` (canonical JSON). |

### 4.3 Canonical JSON

Signatures are computed over canonical JSON (sorted keys, no whitespace):

```json
{"ciphertext":"...","header":{"msg_id":"...","recipient_fp":"...","sender_fp":"...","subject":"...","timestamp":"..."}}
```

---

## 5. Receipt JSON Schema

### 5.1 Structure

```json
{
  "msg_id": "unique-message-id-uuid-v4",
  "status": "delivered|read|failed",
  "timestamp": "2026-02-12T10:35:00Z",
  "error": "optional-error-message-if-failed"
}
```

### 5.2 Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `msg_id` | string (UUID v4) | Yes | Message ID from envelope header. |
| `status` | string | Yes | One of: `delivered` (decrypted successfully), `read` (opened by recipient), `failed` (decrypt/verify failed). |
| `timestamp` | string (ISO 8601) | Yes | Receipt creation time in UTC. |
| `error` | string | No | Error message if `status` is `failed`. |

### 5.3 Storage

Receipts are stored as JSONL files under `runtime/mailbox/receipts/`:
- One receipt per line
- Filename: `receipts_YYYY-MM-DD.jsonl` (daily rotation)

---

## 6. Governance Rules

### 6.1 Deny-by-Default Allowlist

**Rule:** Recipients must explicitly allowlist sender fingerprints before accepting envelopes.

**Implementation:**
- Allowlist file: `runtime/mailbox/allowlist.json` (JSON array of sender fingerprints)
- On envelope receipt, verify `header.sender_fp` is in allowlist
- If not in allowlist, reject envelope (do not decrypt)

**Example allowlist:**
```json
[
  "dGVzdF9zZW5kZXJfMDAx",
  "YW5vdGhlcl9zZW5kZXJfMDAy"
]
```

### 6.2 No Side Effects in v0

**Rule:** Messages in v0 are read-only content. Opening an envelope must not:
- Execute code
- Call tools
- Trigger actions
- Modify system state (except mailbox state: inbox, receipts)

**Rationale:** v0 is a proof-of-concept for secure message transport. Future versions may add execution capabilities with explicit governance.

### 6.3 Metadata Minimization

**Rule:** Public headers contain only essential fields.

**Allowed fields:**
- `sender_fp`, `recipient_fp` (routing)
- `msg_id` (uniqueness)
- `timestamp` (replay protection)
- `subject` (user convenience)

**Forbidden fields:**
- IP addresses
- Hostnames
- Routing paths
- User agents
- Any PII beyond subject line

### 6.4 Replay Protection

**Rule:** Envelopes must be unique and recent.

**Mechanisms:**

1. **Message ID uniqueness:**
   - `msg_id` must be UUID v4
   - Pluggable seen cache: `runtime/mailbox/seen_cache.json` (JSON array of `msg_id` strings)
   - Before decrypting, check `msg_id` not in seen cache
   - After successful decrypt, add `msg_id` to seen cache

2. **Timestamp window:**
   - Parse `header.timestamp` as ISO 8601 UTC
   - Check timestamp is within ±5 minutes of current time (configurable hook)
   - Reject if timestamp is too old or too far in future

3. **Seen cache management:**
   - Cache file: `runtime/mailbox/seen_cache.json`
   - Prune entries older than 24 hours (on mailbox operations)
   - Max cache size: 10,000 entries (FIFO eviction)

---

## 7. Key Handling Rules

### 7.1 Key Types

| Key Type | Algorithm | Purpose | Storage |
|----------|-----------|---------|---------|
| **Signing keypair** | ed25519 | Envelope signatures | `runtime/keys/{identity}_signing.key` (private), `.pub` (public) |
| **Encryption keypair** | x25519 | Sealed box encryption | `runtime/keys/{identity}_encryption.key` (private), `.pub` (public) |

### 7.2 Key Generation

**Function:** `generate_identity() -> {signing_keypair, encryption_keypair}`

**Output:**
```python
{
    "signing_keypair": {
        "private": b"...",  # 32 bytes ed25519 private key
        "public": b"..."    # 32 bytes ed25519 public key
    },
    "encryption_keypair": {
        "private": b"...",  # 32 bytes x25519 private key
        "public": b"..."    # 32 bytes x25519 public key
    },
    "fingerprints": {
        "signing": "base64-fingerprint",
        "encryption": "base64-fingerprint"
    }
}
```

### 7.3 Key Storage

**Location:** `runtime/keys/` (git-ignored)

**File naming:**
- Private keys: `{identity}_signing.key`, `{identity}_encryption.key`
- Public keys: `{identity}_signing.key.pub`, `{identity}_encryption.key.pub`
- Public key bundle (for sharing): `{identity}_public_bundle.json`

**Public key bundle format:**
```json
{
  "identity": "alice",
  "signing_fp": "base64-fingerprint",
  "signing_pub": "base64-public-key",
  "encryption_fp": "base64-fingerprint",
  "encryption_pub": "base64-public-key"
}
```

**Security:**
- Private keys stored as raw bytes (no base64 encoding in storage)
- File permissions: 0600 (owner read/write only)
- Never commit keys to git (enforced by `.gitignore`)

### 7.4 Fingerprint Calculation

**Algorithm:**
1. Take public key bytes (32 bytes for ed25519/x25519)
2. Compute SHA256 hash
3. Take first 16 bytes of hash
4. Base64-encode (no padding)

**Example:**
```python
import hashlib
import base64

pub_key_bytes = b"..."
hash_obj = hashlib.sha256(pub_key_bytes)
fingerprint = base64.b64encode(hash_obj.digest()[:16]).decode('ascii').rstrip('=')
```

---

## 8. Cryptographic Operations

### 8.1 Signing (ed25519)

**Function:** `sign(payload: bytes, sender_ed25519_priv: bytes) -> bytes`

**Process:**
1. Canonicalize JSON (sorted keys, no whitespace)
2. Sign canonical bytes with ed25519 private key
3. Return 64-byte signature (base64-encoded in envelope)

### 8.2 Verification (ed25519)

**Function:** `verify(payload: bytes, sig: bytes, sender_ed25519_pub: bytes) -> bool`

**Process:**
1. Canonicalize JSON (same as signing)
2. Verify signature against canonical bytes and public key
3. Return `True` if valid, `False` otherwise

### 8.3 Encryption (x25519 Sealed Box)

**Function:** `seal_to_recipient(plaintext: bytes, recipient_x25519_pub: bytes) -> bytes`

**Process:**
1. Generate ephemeral x25519 keypair
2. Perform ECDH with recipient public key
3. Derive symmetric key (HKDF-SHA256)
4. Encrypt plaintext with ChaCha20Poly1305 (AEAD)
5. Prepend ephemeral public key to ciphertext
6. Return sealed box (ephemeral_pub + ciphertext)

**Output:** 32 bytes (ephemeral pub) + 16 bytes (nonce) + N bytes (ciphertext) + 16 bytes (tag)

### 8.4 Decryption (x25519 Sealed Box)

**Function:** `open_from_sender(ciphertext: bytes, recipient_x25519_priv: bytes) -> bytes`

**Process:**
1. Extract ephemeral public key (first 32 bytes)
2. Perform ECDH with recipient private key
3. Derive symmetric key (HKDF-SHA256)
4. Decrypt ciphertext with ChaCha20Poly1305
5. Return plaintext

**Error handling:** Raise exception if decryption fails (invalid key, tampered ciphertext)

---

## 9. Mailbox Operations

### 9.1 Outbox (Sending)

**Function:** `write_outbox(envelope_json: dict, runtime_dir: Path) -> Path`

**Process:**
1. Validate envelope structure
2. Write envelope JSON to `runtime/mailbox/outbox/{msg_id}.json`
3. Return path to written file

**File naming:** `{msg_id}.json` (one envelope per file)

### 9.2 Inbox (Receiving)

**Function:** `deliver_to_inbox(envelope_json: dict, runtime_dir: Path) -> Path`

**Process:**
1. Validate envelope structure
2. Check sender fingerprint against allowlist
3. Check message ID against seen cache
4. Check timestamp window
5. Write envelope JSON to `runtime/mailbox/inbox/{msg_id}.json`
6. Return path to written file

**File naming:** `{msg_id}.json` (one envelope per file)

### 9.3 List Inbox

**Function:** `list_inbox(runtime_dir: Path) -> List[dict]`

**Process:**
1. Scan `runtime/mailbox/inbox/` directory
2. Read each `{msg_id}.json` file
3. Return list of envelope dictionaries (headers only, no ciphertext)

**Output:** List of envelope headers (decrypted subject if available)

### 9.4 Receipt Generation

**Function:** `mark_delivered_receipt(msg_id: str, status: str, runtime_dir: Path, error: str | None = None) -> Path`

**Process:**
1. Create receipt JSON
2. Append to `runtime/mailbox/receipts/receipts_{YYYY-MM-DD}.jsonl`
3. Return path to receipt file

---

## 10. Implementation Notes

### 10.1 Dependencies

- **PyNaCl:** Python bindings for libsodium (ed25519, x25519, sealed box)
- **Standard library:** `json`, `pathlib`, `uuid`, `datetime`, `hashlib`, `base64`

### 10.2 Error Handling

- **Invalid envelope:** Raise `ValueError` with descriptive message
- **Decryption failure:** Raise `DecryptionError` (custom exception)
- **Verification failure:** Raise `VerificationError` (custom exception)
- **Allowlist rejection:** Raise `AllowlistError` (custom exception)
- **Replay detected:** Raise `ReplayError` (custom exception)

### 10.3 Testing Requirements

- **Roundtrip:** Sender creates envelope → recipient opens → plaintext matches
- **Tamper detection:** Modify header → verify fails
- **Wrong key:** Recipient mismatch → decrypt fails
- **Allowlist:** Deny-by-default unless sender fingerprint allowlisted

---

## 11. Future Versions (Not in v0)

- **Execution capabilities:** Messages that trigger tool execution (with governance)
- **Network transport:** HTTP/WebSocket transport for remote mailboxes
- **Key rotation:** Automatic key rotation with forward secrecy
- **Group messaging:** Multi-recipient envelopes
- **Message threading:** Reply chains and conversation tracking

---

**Specification Status:** ✅ Complete  
**Implementation Target:** Calyx Mail v0.1.0
