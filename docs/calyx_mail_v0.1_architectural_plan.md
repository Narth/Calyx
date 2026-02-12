# Calyx Mail Protocol Layer v0.1 Architectural Plan
**Agent-Foundation Edition**

**Date:** 2026-02-12  
**Status:** 📋 PLAN — Awaiting approval before implementation

---

## Executive Summary

This plan formalizes Calyx Mail v0 into Protocol Layer v0.1 (Agent-Foundation Edition) through structural refactoring without expanding capabilities. The goal is to create a machine-verifiable protocol foundation suitable for future agent-to-agent transport, while maintaining all existing governance invariants.

**Key Principle:** Structure-only changes. No feature expansion. No execution pathways. No network code.

---

## 1. Current State Analysis (v0)

### 1.1 Existing Components

| Component | Current Implementation | Status |
|-----------|------------------------|--------|
| **Envelope Format** | JSON dict with `header`, `ciphertext`, `signature` | ✅ Functional |
| **Canonical JSON** | `json.dumps(..., sort_keys=True)` | ⚠️ Informal |
| **Protocol Version** | Not embedded in signed material | ❌ Missing |
| **Replay Protection** | JSON file (`seen_cache.json`) | ⚠️ Not durable/integrity-protected |
| **Mailbox Storage** | `{msg_id}.json` filenames | ⚠️ Not content-addressed |
| **File Operations** | Standard file writes | ⚠️ Not atomic, no symlink protection |
| **Spec Location** | `docs/calyx_mail_spec_v0.md` (human-readable) | ✅ Exists |
| **Machine Schema** | Embedded in code, not separate | ❌ Missing |
| **State Machine** | Implicit in code flow | ❌ Not formalized |

### 1.2 Current Governance Compliance

✅ **Compliant:**
- No network code
- No external APIs
- No dynamic execution
- No secrets in tracked files
- Local-first architecture
- Deny-by-default allowlist
- Read-only content (no side effects)

---

## 2. Proposed Changes (v0.1)

### 2.1 New Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Threat Model** | `docs/calyx_mail_protocol_threat_model_v0.1.md` | Formal threat analysis with drift watchlist |
| **Machine Schema** | `spec/mail/envelope_v0.1.json` | Canonical JSON Schema for envelope |
| **Machine Schema** | `spec/mail/receipt_v0.1.json` | Canonical JSON Schema for receipt |
| **Codec Module** | `calyx/mail/codec.py` | Deterministic serialization with version enforcement |
| **Replay State DB** | `runtime/mailbox/replay_state.db` (SQLite) | Durable, integrity-protected replay cache |
| **Mailbox Hardening** | `calyx/mail/mailbox.py` (refactor) | Content-addressed filenames, atomic writes, symlink protection |
| **State Machine Doc** | `docs/calyx_mail_state_machine_v0.1.md` | Explicit protocol state transitions |

### 2.2 Refactored Components

| Component | Changes | Breaking? |
|-----------|---------|----------|
| **envelope.py** | Add protocol version to signed payload | ⚠️ Yes (signature format changes) |
| **mailbox.py** | Content-addressed filenames, atomic writes | ⚠️ Yes (file naming changes) |
| **mailbox.py** | SQLite replay state (replaces JSON cache) | ⚠️ Yes (replay state format changes) |
| **CLI** | Update to use new codec | ⚠️ Yes (envelope format changes) |

---

## 3. Breaking Changes Analysis

### 3.1 Signature Format Change

**Current (v0):**
```json
{
  "header": {...},
  "ciphertext": "...",
  "signature": "..."  // Signs: canonical_json({header, ciphertext})
}
```

**Proposed (v0.1):**
```json
{
  "protocol_version": "0.1",
  "header": {...},
  "ciphertext": "...",
  "signature": "..."  // Signs: canonical_json({protocol_version, header, ciphertext})
}
```

**Impact:**
- ✅ **Backward Compatible:** v0.1 code can detect v0 envelopes (no `protocol_version` field) and handle them separately
- ⚠️ **Forward Compatible:** v0 code cannot verify v0.1 envelopes (signature mismatch)
- **Migration Path:** v0 envelopes remain readable; new envelopes use v0.1 format

**Mitigation:**
- Add version detection in `codec.py`
- Support both v0 and v0.1 formats during transition
- CLI can convert v0 → v0.1 if needed

### 3.2 File Naming Change

**Current (v0):**
- Inbox: `runtime/mailbox/inbox/{msg_id}.json`
- Outbox: `runtime/mailbox/outbox/{msg_id}.json`

**Proposed (v0.1):**
- Inbox: `runtime/mailbox/inbox/{content_hash}.json` (content-addressed)
- Outbox: `runtime/mailbox/outbox/{content_hash}.json` (content-addressed)

**Impact:**
- ⚠️ **Breaking:** Existing mailbox files will not be found by new code
- **Migration Path:** CLI tool to migrate existing mailboxes

**Mitigation:**
- Provide migration script: `tools/migrate_mailbox_v0_to_v0.1.py`
- Preserve old files during migration
- Document migration process

### 3.3 Replay State Format Change

**Current (v0):**
- `runtime/mailbox/seen_cache.json` (JSON array of msg_ids)

**Proposed (v0.1):**
- `runtime/mailbox/replay_state.db` (SQLite with integrity protection)

**Impact:**
- ⚠️ **Breaking:** Existing replay cache will be lost
- **Mitigation:** Migration script can import existing cache

---

## 4. Backward Compatibility Strategy

### 4.1 Dual Format Support

**Approach:** v0.1 implementation supports both v0 and v0.1 formats.

**Detection:**
```python
def detect_envelope_version(envelope: dict) -> str:
    if "protocol_version" in envelope:
        return envelope["protocol_version"]
    return "0.0"  # Legacy v0
```

**Handling:**
- v0 envelopes: Use existing verification logic
- v0.1 envelopes: Use new codec with version enforcement
- CLI: Can convert v0 → v0.1 on read

### 4.2 Migration Tools

**Migration Script:** `tools/migrate_mailbox_v0_to_v0.1.py`
- Reads v0 mailbox files
- Converts to v0.1 format (content-addressed)
- Migrates replay cache to SQLite
- Preserves original files as backup

---

## 5. Risk Delta Assessment

### 5.1 Security Risks

| Risk | Current (v0) | Proposed (v0.1) | Delta |
|------|---------------|-----------------|-------|
| **Replay attacks** | JSON cache (no integrity) | SQLite with integrity | ✅ Improved |
| **File tampering** | No detection | Content-addressed + atomic writes | ✅ Improved |
| **Symlink attacks** | No protection | Explicit symlink rejection | ✅ Improved |
| **Signature forgery** | No version binding | Version in signed material | ✅ Improved |
| **Protocol drift** | Informal | Explicit schema + version | ✅ Improved |

**Overall Security Delta:** ✅ **POSITIVE** — All changes improve security posture.

### 5.2 Operational Risks

| Risk | Current (v0) | Proposed (v0.1) | Delta |
|------|---------------|-----------------|-------|
| **Data loss** | Low (simple JSON) | Low (SQLite + migration) | ⚠️ Neutral |
| **Compatibility** | N/A | Requires migration | ⚠️ Requires migration |
| **Complexity** | Low | Medium (codec + schema) | ⚠️ Increased |
| **Testing burden** | Low | Medium (dual format support) | ⚠️ Increased |

**Overall Operational Delta:** ⚠️ **NEUTRAL** — Increased complexity offset by improved security.

### 5.3 Governance Compliance Risks

| Constraint | Risk | Mitigation |
|------------|------|------------|
| **No network code** | ✅ None | No network imports added |
| **No external APIs** | ✅ None | SQLite is standard library |
| **No dynamic execution** | ✅ None | No eval, no subprocess |
| **No secrets in git** | ✅ None | All runtime data remains ignored |
| **No execution pathways** | ✅ None | Mail content remains read-only |
| **Local-first** | ✅ None | All operations remain filesystem-based |

**Overall Governance Delta:** ✅ **COMPLIANT** — No violations introduced.

---

## 6. Detailed Component Specifications

### 6.1 Threat Model Formalization

**File:** `docs/calyx_mail_protocol_threat_model_v0.1.md`

**Contents:**
- **Assets:** Envelopes, keys, replay state, mailbox integrity
- **Trust Boundaries:** Sender → Recipient, Local filesystem, Runtime directory
- **In-Scope Adversaries:** Local filesystem attacker, compromised endpoint, key theft
- **Out-of-Scope Adversaries:** Network MITM (v0.1 has no network), quantum attacks
- **Protocol Invariants:** Signature verification, encryption, replay protection, allowlist
- **Drift Watchlist:** Agent execution, command payloads, remote identity discovery, key exchange automation

### 6.2 Canonical Machine Schema Layer

**Directory:** `spec/mail/`

**Files:**
- `envelope_v0.1.json` — JSON Schema for envelope structure
- `receipt_v0.1.json` — JSON Schema for receipt structure
- `signed_payload_v0.1.md` — Explicit definition of what is signed
- `associated_data_v0.1.md` — Explicit definition of associated data (AEAD)

**Schema Requirements:**
- Exact field definitions (no ambiguity)
- Protocol version embedded in signed material
- Algorithm identifiers (ed25519, x25519-sealed-box)
- Deterministic serialization rules (explicit ordering)

### 6.3 Deterministic Serialization Layer

**File:** `calyx/mail/codec.py`

**Functions:**
- `encode_envelope_v0_1(envelope_dict) -> bytes` — Canonical encoding
- `decode_envelope_v0_1(bytes) -> envelope_dict` — Canonical decoding
- `encode_envelope_v0(envelope_dict) -> bytes` — Legacy support
- `decode_envelope_v0(bytes) -> envelope_dict` — Legacy support
- `detect_version(envelope_dict) -> str` — Version detection
- `validate_canonical(bytes) -> bool` — Reject non-canonical input

**Properties:**
- Stable across Python versions
- Reject unknown protocol versions
- Property tests for canonicalization

### 6.4 Durable Replay Protection

**File:** `runtime/mailbox/replay_state.db` (SQLite, git-ignored)

**Schema:**
```sql
CREATE TABLE replay_state (
    msg_id_hash TEXT PRIMARY KEY,  -- SHA256(msg_id) for indexing
    msg_id TEXT NOT NULL,           -- Original msg_id
    seen_at TIMESTAMP NOT NULL,     -- When first seen
    envelope_hash TEXT NOT NULL,    -- Content hash for integrity
    UNIQUE(msg_id)
);

CREATE INDEX idx_seen_at ON replay_state(seen_at);
```

**Integrity Protection:**
- Hash-chained log: Each entry includes hash of previous entry
- Or: Signed manifest (simpler, chosen for v0.1)
- Content-addressed seen-hash store (SHA256 of envelope canonical form)

**Chosen Design:** Content-addressed seen-hash store (minimal, safest)
- Store: `SHA256(canonical_envelope)` → `{msg_id, timestamp}`
- Bounded memory: Prune entries older than 24 hours
- Integrity: Hash of envelope prevents tampering

### 6.5 Mailbox Integrity Hardening

**Changes to `calyx/mail/mailbox.py`:**

1. **Content-Addressed Filenames:**
   ```python
   def compute_envelope_hash(envelope: dict) -> str:
       canonical = codec.encode_envelope_v0_1(envelope)
       return hashlib.sha256(canonical).hexdigest()[:16]
   ```

2. **Atomic Writes:**
   ```python
   def atomic_write(path: Path, content: bytes):
       tmp_path = path.with_suffix('.tmp')
       tmp_path.write_bytes(content)
       tmp_path.replace(path)  # Atomic on POSIX
   ```

3. **Symlink Protection:**
   ```python
   def check_symlink(path: Path):
       if path.is_symlink():
           raise SecurityError("Symlinks not allowed")
       # Use directory file descriptors where applicable
   ```

4. **File Substitution Detection:**
   - Verify content hash matches filename
   - Reject if mismatch detected

### 6.6 Human Lane vs Machine Lane

**Structure:**
```
docs/
  ├── calyx_mail_spec_v0.md              # Human-readable narrative (v0)
  ├── calyx_mail_protocol_threat_model_v0.1.md  # Human-readable threat model
  └── calyx_mail_state_machine_v0.1.md   # Human-readable state machine

spec/
  └── mail/
      ├── envelope_v0.1.json             # Machine schema (JSON Schema)
      ├── receipt_v0.1.json               # Machine schema (JSON Schema)
      ├── signed_payload_v0.1.md          # Machine spec (explicit)
      └── associated_data_v0.1.md        # Machine spec (explicit)

calyx/mail/
  └── codec.py                           # Runtime implementation
```

**CI Rule (Future):**
- Generated artifacts (if any) must match `spec/`
- Machine artifacts cannot be manually edited
- Schema validation tests enforce `spec/` compliance

### 6.7 Explicit Protocol State Machine

**File:** `docs/calyx_mail_state_machine_v0.1.md`

**States:**
1. **Created** — Envelope structure created (not yet signed)
2. **Signed** — Signature computed and attached
3. **Encrypted** — Plaintext encrypted (sealed box)
4. **Delivered** — Written to recipient's inbox
5. **Opened** — Recipient decrypted and verified
6. **Receipt Issued** — Delivery receipt created

**Invalid Transitions:**
- Cannot skip "Signed" → "Encrypted"
- Cannot decrypt without signature verification
- Cannot issue receipt without delivery

**Test Coverage:**
- Test illegal state transitions
- Test valid state machine paths

---

## 7. Implementation Plan

### Phase 1: Threat Model & Schema (Non-Breaking)
1. Create `docs/calyx_mail_protocol_threat_model_v0.1.md`
2. Create `spec/mail/` directory
3. Create `spec/mail/envelope_v0.1.json`
4. Create `spec/mail/receipt_v0.1.json`
5. Create `spec/mail/signed_payload_v0.1.md`
6. Create `spec/mail/associated_data_v0.1.md`

### Phase 2: Codec Module (Breaking - Signature Format)
1. Create `calyx/mail/codec.py`
2. Implement version detection
3. Implement v0.1 canonical encoding/decoding
4. Implement v0 legacy support
5. Add property tests

### Phase 3: Replay Protection Upgrade (Breaking - State Format)
1. Design SQLite schema for replay state
2. Implement `calyx/mail/replay.py` module
3. Replace JSON cache with SQLite
4. Add integrity protection (content-addressed hash)
5. Add migration script

### Phase 4: Mailbox Hardening (Breaking - File Naming)
1. Refactor `mailbox.py` for content-addressed filenames
2. Add atomic write functions
3. Add symlink protection
4. Add file substitution detection
5. Update CLI to use new mailbox functions

### Phase 5: State Machine & Documentation (Non-Breaking)
1. Create `docs/calyx_mail_state_machine_v0.1.md`
2. Add state machine tests
3. Update main spec document

### Phase 6: Migration & Testing
1. Create `tools/migrate_mailbox_v0_to_v0.1.py`
2. Test migration script
3. Update all tests for v0.1 format
4. Verify backward compatibility

---

## 8. Governance Compliance Verification

### 8.1 Constraint Checklist

| Constraint | Status | Evidence |
|------------|--------|----------|
| **No network code** | ✅ PASS | No network imports; SQLite is local filesystem |
| **No external APIs** | ✅ PASS | SQLite is Python standard library (`sqlite3`) |
| **No dynamic execution** | ✅ PASS | No eval, exec, subprocess, or plugin systems |
| **No runtime artifacts in git** | ✅ PASS | `runtime/` remains in `.gitignore` |
| **No secrets in tracked files** | ✅ PASS | All keys remain under `runtime/keys/` |
| **Mail content read-only** | ✅ PASS | No execution pathways introduced |
| **Local-first architecture** | ✅ PASS | All operations remain filesystem-based |
| **Deny-by-default** | ✅ PASS | Allowlist enforcement unchanged |

### 8.2 Anti-Drift Verification

| Risk | Status | Mitigation |
|------|--------|------------|
| **Agent execution semantics** | ✅ AVOIDED | No command payload types |
| **Mail as control plane** | ✅ AVOIDED | Content remains read-only |
| **Remote identity discovery** | ✅ AVOIDED | No network code added |
| **Key exchange automation** | ✅ AVOIDED | Manual key exchange remains |
| **Background daemons** | ✅ AVOIDED | No daemon code added |

---

## 9. Testing Strategy

### 9.1 Unit Tests

- **Codec:** Canonical encoding/decoding, version detection, non-canonical rejection
- **Replay:** SQLite operations, integrity protection, pruning
- **Mailbox:** Content-addressed filenames, atomic writes, symlink protection
- **State Machine:** Valid transitions, invalid transition rejection

### 9.2 Integration Tests

- **Migration:** v0 → v0.1 mailbox migration
- **Backward Compatibility:** v0 envelope reading in v0.1 code
- **Forward Compatibility:** v0.1 envelope rejection in v0 code (expected)

### 9.3 Property Tests

- **Canonicalization:** Same input always produces same output
- **Version Enforcement:** Unknown versions rejected
- **Integrity:** Content-addressed filenames match content

---

## 10. Rollback Plan

If issues are discovered:

1. **Immediate:** Revert commits (git history preserved)
2. **Migration:** v0.1 → v0 migration script (if needed)
3. **Documentation:** Update docs to reflect rollback

---

## 11. Success Criteria

✅ **All governance constraints satisfied**  
✅ **No new external dependencies** (SQLite is stdlib)  
✅ **No network imports introduced**  
✅ **No secrets introduced**  
✅ **All new modules compile**  
✅ **Tests pass**  
✅ **Backward compatibility maintained** (v0 envelopes readable)  
✅ **Migration path provided** (v0 → v0.1)  

---

## 12. Approval Required

**Before implementation, confirm:**

1. ✅ Breaking changes are acceptable (with migration path)
2. ✅ SQLite dependency is acceptable (standard library)
3. ✅ Content-addressed filenames are acceptable
4. ✅ Protocol version in signature is acceptable
5. ✅ Threat model formalization approach is acceptable

**If any item is not acceptable, abort and revise plan.**

---

**Plan Status:** 📋 **AWAITING APPROVAL**  
**Governance Status:** ✅ **COMPLIANT**  
**Risk Level:** ⚠️ **MEDIUM** (breaking changes with migration path)

---

*Plan generated 2026-02-12. Ready for review and approval.*
