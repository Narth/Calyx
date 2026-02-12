# Calyx Mail Protocol Layer v0.1 Threat Model
**Agent-Foundation Edition**

**Date:** 2026-02-12  
**Version:** 0.1.0

---

## 1. Overview

This document provides a formal threat model for Calyx Mail Protocol Layer v0.1, focusing on local-first, filesystem-based encrypted messaging with no network transport.

**Scope:** Protocol Layer v0.1 (Agent-Foundation Edition)  
**Out of Scope:** Network transport, agent execution, remote identity discovery

**⚠️ Protocol Stability:** Calyx Mail v0.1 is protocol-stable. Future changes require version bump (e.g., v0.2).

---

## 2. Assets

### 2.1 Primary Assets

| Asset | Description | Protection |
|-------|-------------|------------|
| **Envelopes** | Encrypted messages (ciphertext + signatures) | x25519 sealed box encryption, ed25519 signatures |
| **Keys** | Signing (ed25519) and encryption (x25519) keypairs | Stored under `runtime/keys/` (git-ignored), file permissions 0600 |
| **Replay State** | SQLite database of seen envelope hashes | Content-addressed replay keys, integrity-protected |
| **Mailbox Integrity** | Inbox/outbox filesystem state | Content-addressed filenames, atomic writes, symlink protection |
| **Allowlist** | Sender fingerprint allowlist | Deny-by-default enforcement |

### 2.2 Secondary Assets

| Asset | Description | Protection |
|-------|-------------|------------|
| **Receipts** | Delivery/read/failure status records | JSONL files (append-only) |
| **Public Key Bundles** | Shared public keys for recipients | Template pattern (no secrets) |

---

## 3. Trust Boundaries

### 3.1 Trust Model

```
┌─────────────────────────────────────────┐
│  Sender (Trusted Identity)              │
│  - Has ed25519 signing key              │
│  - Has x25519 encryption key            │
└──────────────┬──────────────────────────┘
               │
               │ Creates envelope
               │ Signs with ed25519
               │ Encrypts with x25519
               ▼
┌─────────────────────────────────────────┐
│  Envelope (Public Header + Ciphertext)  │
│  - Header: sender_fp, recipient_fp,     │
│    msg_id, timestamp, subject           │
│  - Ciphertext: x25519 sealed box        │
│  - Signature: ed25519 over canonical    │
└──────────────┬──────────────────────────┘
               │
               │ Filesystem transport
               │ (Local or private LAN)
               ▼
┌─────────────────────────────────────────┐
│  Recipient (Trusted Identity)           │
│  - Has x25519 decryption key            │
│  - Has allowlist of sender fingerprints │
│  - Has replay state database            │
└─────────────────────────────────────────┘
```

### 3.2 Trust Boundaries

| Boundary | Trust Level | Threats |
|----------|-------------|---------|
| **Sender → Envelope** | High | Sender controls envelope creation, signing, encryption |
| **Envelope → Filesystem** | Medium | Filesystem may be compromised, files may be tampered |
| **Filesystem → Recipient** | Medium | Filesystem attacker, symlink attacks, file substitution |
| **Recipient → Replay State** | High | Replay state must be integrity-protected |

---

## 4. In-Scope Adversaries

### 4.1 Local Filesystem Attacker

**Capabilities:**
- Read/write access to `runtime/mailbox/` directory
- Can create symlinks
- Can substitute files
- Can modify filesystem metadata

**Threats:**
- **File Tampering:** Modify envelope files after creation
- **Symlink Attacks:** Redirect mailbox operations to attacker-controlled files
- **File Substitution:** Replace envelope files with malicious content
- **Replay State Tampering:** Modify SQLite database to allow replays

**Mitigations:**
- Content-addressed filenames (full SHA256 hash)
- Atomic writes (temporary file + atomic rename)
- Symlink detection and rejection
- File content hash verification (filename must match content hash)
- SQLite integrity protection (WAL mode, foreign keys)

### 4.2 Compromised Endpoint

**Capabilities:**
- Full access to runtime directory
- Can read keys from `runtime/keys/`
- Can modify mailbox state
- Can read decrypted plaintext

**Threats:**
- **Key Theft:** Steal signing/encryption keys
- **Plaintext Exposure:** Read decrypted messages
- **Replay Injection:** Inject old envelopes into replay state
- **Allowlist Bypass:** Modify allowlist to accept unauthorized senders

**Mitigations:**
- Keys stored with 0600 permissions (owner-only access)
- Replay state uses content-addressed keys (prevents injection of modified envelopes)
- Allowlist integrity (can be signed in future versions)
- **Limitation:** Compromised endpoint can read all local data (by design; v0.1 is local-first)

### 4.3 Key Theft Attacker

**Capabilities:**
- Has stolen signing key (ed25519 private key)
- Has stolen encryption key (x25519 private key)

**Threats:**
- **Signature Forgery:** Create envelopes signed with stolen key
- **Decryption:** Decrypt messages encrypted to stolen key
- **Replay:** Replay old messages signed with stolen key

**Mitigations:**
- Replay protection prevents replay of old messages
- Allowlist prevents unauthorized senders (even with valid signature)
- **Limitation:** Old messages remain decryptable (no forward secrecy in v0.1)

---

## 5. Out-of-Scope Adversaries

### 5.1 Network MITM Attacker

**Status:** Out of scope (v0.1 has no network transport)

**Rationale:** v0.1 is local-first; envelopes are transported via filesystem only.

**Future Consideration:** Network transport will be addressed in future versions with additional threat model updates.

### 5.2 Quantum Computing Attacker

**Status:** Out of scope (v0.1 uses classical cryptography)

**Rationale:** ed25519 and x25519 are not quantum-resistant. Quantum-resistant algorithms will be considered in future versions.

### 5.3 Remote Identity Discovery Attacker

**Status:** Out of scope (v0.1 has no remote identity discovery)

**Rationale:** v0.1 requires manual key exchange. Remote identity discovery will be addressed in future versions.

---

## 6. Protocol Invariants

### 6.1 Cryptographic Invariants

| Invariant | Enforcement |
|-----------|-------------|
| **Signature Verification** | ed25519 signature verified before decryption |
| **Encryption** | x25519 sealed box encryption (only recipient can decrypt) |
| **Replay Protection** | Content-addressed replay keys prevent duplicate processing |
| **Allowlist Enforcement** | Deny-by-default; sender fingerprint must be in allowlist |

### 6.2 Integrity Invariants

| Invariant | Enforcement |
|-----------|-------------|
| **Content-Addressed Storage** | Filenames are SHA256 hashes of envelope canonical form |
| **Atomic Writes** | Temporary file + atomic rename prevents partial writes |
| **Symlink Protection** | Symlinks detected and rejected |
| **File Hash Verification** | Filename hash must match content hash |

### 6.3 Replay Protection Invariants

**CRITICAL DEPENDENCY:**

Replay protection relies on **timestamp window enforcement** (±5 minutes):

1. **Timestamp Window Enforcement:**
   - Envelopes with timestamp outside ±5 minutes of current time are **rejected**
   - This prevents replay of old envelopes (even if replay_key is not in replay state)

2. **Replay State Retention (24 hours):**
   - Replay state retains entries for 24 hours
   - **Purpose:** Audit/logging, not validity enforcement
   - **Rationale:** Envelopes older than 5 minutes are already rejected by timestamp check
   - **Dependency:** Replay state pruning assumes timestamp window enforcement is active

**Explicit Dependency Chain:**
```
Timestamp Window (±5 min) → Rejects old envelopes
    ↓
Replay State (24 hr retention) → Prevents duplicate processing of recent envelopes
    ↓
Content-Addressed Replay Key → Prevents tampering with replay state
```

**Future Drift Risk:**
- If timestamp window is relaxed (e.g., for network transport), replay state retention must be extended accordingly
- If timestamp window is removed, replay state becomes the sole replay protection mechanism (weaker security)

**Documentation Requirement:**
- This dependency must be documented in protocol specification
- Any changes to timestamp window must trigger replay state retention review

---

## 7. Replay Identity Formalization

### 7.1 Replay Definition

**A replay occurs when:**
> The same cryptographic envelope (identical canonical form) is presented to the recipient more than once, regardless of how it was delivered or when it was created.

### 7.2 Replay Key Formula

**Single Deterministic Replay Key:**

```
replay_key = SHA256(canonical_envelope_bytes)
```

Where `canonical_envelope_bytes` is the deterministic canonical encoding of the entire envelope (including `protocol_version`, `header`, `ciphertext`, `signature`).

### 7.3 Replay Key Properties

| Property | Description |
|----------|-------------|
| **Deterministic** | Same envelope always produces same replay key |
| **Content-Addressed** | Replay key matches content-addressed filename |
| **Tamper-Resistant** | Any modification to envelope changes replay key |
| **Cryptographic** | SHA256 provides 2^256 collision resistance |

### 7.4 Replay Key vs Message ID

| Field | Purpose | Uniqueness |
|-------|---------|------------|
| **msg_id** | Human-readable identifier (UUID v4) | Probabilistic (~0 collision probability) |
| **replay_key** | Cryptographic replay detection (SHA256) | Cryptographic (2^256 collision resistance) |

**Relationship:**
- `msg_id`: Metadata for human reference, receipt correlation, logging
- `replay_key`: Cryptographic identity for replay detection (primary key in replay state)

---

## 8. Drift Watchlist (Agentization Risks)

### 8.1 Prohibited Semantics

| Risk | Status | Mitigation |
|------|--------|------------|
| **Agent Execution** | ❌ PROHIBITED | Mail content remains read-only; no execution pathways |
| **Command Payloads** | ❌ PROHIBITED | No command/action payload types in v0.1 |
| **Mail as Control Plane** | ❌ PROHIBITED | Envelopes cannot trigger system actions |
| **Remote Identity Discovery** | ❌ PROHIBITED | No network code; manual key exchange only |
| **Key Exchange Automation** | ❌ PROHIBITED | No automated key distribution |
| **Background Daemons** | ❌ PROHIBITED | No daemon code; CLI-only operations |

### 8.2 Future Version Considerations

**If agent execution is added in future versions:**
- Must be explicit opt-in (governance gate)
- Must be documented in threat model
- Must have separate protocol version
- Must not affect v0.1 compatibility

---

## 9. Attack Scenarios

### 9.1 Scenario: File Tampering

**Attack:**
1. Attacker modifies envelope file in inbox
2. Recipient attempts to decrypt modified envelope

**Detection:**
- Content-addressed filename (SHA256 hash) no longer matches file content
- File hash verification fails

**Mitigation:**
- Reject envelope if filename hash ≠ content hash
- Log security event

### 9.2 Scenario: Symlink Attack

**Attack:**
1. Attacker creates symlink: `inbox/legitimate_hash.json` → `/tmp/attacker_file.json`
2. Recipient writes envelope to symlink
3. Attacker reads envelope from `/tmp/attacker_file.json`

**Detection:**
- Symlink check before file operations
- Reject symlinks explicitly

**Mitigation:**
- Check `path.is_symlink()` before operations
- Raise `SecurityError` if symlink detected

### 9.3 Scenario: Replay Injection

**Attack:**
1. Attacker attempts to inject old envelope into replay state
2. Attacker modifies SQLite database directly

**Detection:**
- Replay key is content-addressed (SHA256 of canonical envelope)
- Modified envelope produces different replay_key
- Replay state lookup fails (different key)

**Mitigation:**
- Replay key is cryptographic hash (tamper-resistant)
- SQLite integrity protection (WAL mode, foreign keys)

### 9.4 Scenario: Timestamp Window Bypass

**Attack:**
1. Attacker modifies envelope timestamp to bypass ±5 minute window
2. Attacker attempts to replay old envelope

**Detection:**
- Timestamp window check rejects envelope before replay check
- Replay state never consulted for invalid timestamps

**Mitigation:**
- Timestamp window enforcement is primary replay protection
- Replay state is secondary (for recent duplicates)

---

## 10. Security Properties

### 10.1 Confidentiality

**Property:** Only recipient with x25519 private key can decrypt envelope.

**Enforcement:**
- x25519 sealed box encryption
- Recipient fingerprint in header (for routing)
- No plaintext in filesystem

### 10.2 Authenticity

**Property:** Envelope signature proves sender identity.

**Enforcement:**
- ed25519 signature verification
- Sender fingerprint in header
- Allowlist enforcement (deny-by-default)

### 10.3 Integrity

**Property:** Envelope cannot be modified without detection.

**Enforcement:**
- Content-addressed filenames (hash verification)
- Signature over canonical form
- Atomic writes (prevents partial writes)

### 10.4 Replay Resistance

**Property:** Same envelope cannot be processed twice.

**Enforcement:**
- Timestamp window (±5 minutes) - primary protection
- Replay state (24-hour retention) - secondary protection
- Content-addressed replay keys (tamper-resistant)

---

## 11. Limitations

### 11.1 Forward Secrecy

**Limitation:** Old messages remain decryptable if keys are stolen.

**Rationale:** v0.1 does not implement forward secrecy. Key rotation recommended for sensitive data.

**Future Consideration:** Forward secrecy can be added in future versions with key rotation.

### 11.2 Deniability

**Limitation:** Signatures provide non-repudiation (by design).

**Rationale:** v0.1 prioritizes authenticity over deniability.

**Future Consideration:** Deniable authentication can be added in future versions.

### 11.3 Network Transport

**Limitation:** v0.1 has no network transport (filesystem only).

**Rationale:** v0.1 is local-first; network transport will be added in future versions.

**Future Consideration:** Network transport will require additional threat model updates.

---

## 12. Threat Model Maintenance

### 12.1 Review Triggers

Review threat model when:
- Protocol version changes
- New attack vectors discovered
- Network transport added
- Agent execution capabilities added
- Key exchange automation added

### 12.2 Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-02-12 | Initial threat model for Protocol Layer v0.1 |

---

**Threat Model Status:** ✅ Complete  
**Governance Compliance:** ✅ Verified  
**Drift Watchlist:** ✅ Documented

---

*Threat model generated 2026-02-12. Explicit timestamp/replay dependency documented.*
