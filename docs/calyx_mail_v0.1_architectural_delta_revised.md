# Calyx Mail Protocol Layer v0.1 Architectural Delta (Revised)
**Agent-Foundation Edition — Clarifications Applied**

**Date:** 2026-02-12  
**Status:** 📋 REVISED PLAN — Architectural tightenings addressed

---

## Executive Summary

This revised plan addresses architectural tightenings requested by architect approval:
1. Full SHA256 hash (no truncation)
2. Explicit replay identity formalization
3. Formal canonical encoding contract (with CBOR alternative)
4. Replay pruning policy justification
5. Updated risk delta assessment

**Governance Status:** ✅ All invariants remain intact.

---

## 1. Content Hash Length Clarification

### 1.1 Original Plan (INCORRECT)

**Previous:** Truncated SHA256 to 16 hex characters for filenames
```python
def compute_envelope_hash(envelope: dict) -> str:
    canonical = codec.encode_envelope_v0_1(envelope)
    return hashlib.sha256(canonical).hexdigest()[:16]  # ❌ TRUNCATED
```

**Risk:** Truncation introduces collision risk (birthday paradox).

### 1.2 Revised Plan (CORRECT)

**Updated:** Use full SHA256 hex (64 characters)

```python
def compute_envelope_hash(envelope: dict) -> str:
    """
    Compute full SHA256 hash of canonical envelope.
    
    Returns:
        64-character hexadecimal string (no truncation)
    """
    canonical = codec.encode_envelope_v0_1(envelope)
    return hashlib.sha256(canonical).hexdigest()  # ✅ FULL HASH
```

**Filename Format:**
- Inbox: `runtime/mailbox/inbox/{full_sha256_hash}.json`
- Outbox: `runtime/mailbox/outbox/{full_sha256_hash}.json`

**Threat Model Justification:**
- **Collision Risk:** Full SHA256 provides 2^256 collision resistance (cryptographically secure)
- **Truncation Risk:** 16 hex chars = 64 bits = ~2^64 collision resistance (insufficient for long-term storage)
- **Decision:** Full hash required for content-addressed storage integrity

---

## 2. Replay Identity Formalization

### 2.1 Problem Statement

**Current Ambiguity:**
- Replay protection uses `msg_id` (UUID v4)
- Content-addressed storage uses `content_hash` (SHA256 of envelope)
- Integrity checks use `envelope_hash` (SHA256 of canonical form)

**Question:** What exactly constitutes a replay?

### 2.2 Replay Definition

**A replay occurs when:**
> The same cryptographic envelope (identical canonical form) is presented to the recipient more than once, regardless of how it was delivered or when it was created.

**Key Insight:** Replay is about **content identity**, not message ID identity.

### 2.3 Replay Key Formula

**Single Deterministic Replay Key:**

```
replay_key = SHA256(canonical_envelope_bytes)
```

Where `canonical_envelope_bytes` is the deterministic canonical encoding of the entire envelope (including protocol_version, header, ciphertext, signature).

**Rationale:**
- **Deterministic:** Same envelope always produces same replay key
- **Content-addressed:** Replay key matches content-addressed filename
- **Tamper-resistant:** Any modification to envelope changes replay key
- **Signature-independent:** Replay key computed from envelope structure (signature is part of envelope)

### 2.4 Replay Key vs Message ID

| Field | Purpose | Uniqueness Guarantee |
|-------|---------|---------------------|
| **msg_id** | Human-readable message identifier (UUID v4) | Probabilistic (collision probability ~0) |
| **replay_key** | Cryptographic replay detection (SHA256) | Cryptographic (2^256 collision resistance) |

**Relationship:**
- `msg_id` is metadata (for human reference, receipts, logging)
- `replay_key` is the cryptographic identity (for replay detection)

**Why Both?**
- `msg_id`: Allows human-readable references, receipt correlation, logging
- `replay_key`: Provides cryptographic replay protection (tamper-resistant)

### 2.5 Replay State Schema (Revised)

**SQLite Schema:**
```sql
CREATE TABLE replay_state (
    replay_key TEXT PRIMARY KEY,        -- SHA256(canonical_envelope) - FULL 64-CHAR HEX
    msg_id TEXT NOT NULL,                -- Original msg_id (for correlation)
    sender_fp TEXT NOT NULL,             -- Sender fingerprint (for allowlist correlation)
    recipient_fp TEXT NOT NULL,          -- Recipient fingerprint (for routing correlation)
    seen_at TIMESTAMP NOT NULL,          -- When first seen (UTC)
    envelope_timestamp TEXT NOT NULL,     -- Original envelope timestamp (for pruning)
    UNIQUE(replay_key)
);

CREATE INDEX idx_seen_at ON replay_state(seen_at);
CREATE INDEX idx_msg_id ON replay_state(msg_id);  -- For receipt correlation
```

**Replay Detection Logic:**
```python
def check_replay(envelope: dict, runtime_dir: Path) -> bool:
    """
    Check if envelope is a replay.
    
    Returns:
        True if replay detected, False otherwise
    """
    canonical_bytes = codec.encode_envelope_v0_1(envelope)
    replay_key = hashlib.sha256(canonical_bytes).hexdigest()  # Full SHA256
    
    # Check SQLite replay state
    return replay_db.has_replay_key(replay_key)
```

### 2.6 Documentation Updates

**Threat Model Addition:**
- Explicit replay definition
- Replay key formula specification
- Relationship between msg_id and replay_key

**Schema Addition:**
- Replay key field definition in `spec/mail/replay_state_v0.1.md`
- Replay detection algorithm specification

---

## 3. Canonical Encoding Contract

### 3.1 Problem Statement

**Current Implementation:**
```python
def canonical_json(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8')
```

**Issues:**
- JSON float representation ambiguity (e.g., `1.0` vs `1`)
- JSON key ordering ambiguity (handled by `sort_keys=True`, but not fully specified)
- Unicode normalization ambiguity
- Numeric type ambiguity (int vs float)

### 3.2 Formal Canonical Encoding Specification

**Encoding:** UTF-8

**Key Ordering:**
- Recursive alphabetical sort (depth-first)
- Case-sensitive (A < a)
- Numeric keys sorted as strings ("1" < "10" < "2")

**Whitespace Rules:**
- No whitespace between tokens
- No trailing whitespace
- No leading whitespace
- Separators: `,` (comma) and `:` (colon) only

**Numeric Normalization:**
- **Integers:** Represented as JSON numbers (no decimal point)
- **Floats:** **DISALLOWED** (reject on encoding)
- **Rationale:** Float representation ambiguity (e.g., `1.0` vs `1` vs `1e0`)

**Disallowed Types:**
- `float` (use `Decimal` or `int` with explicit scaling)
- `NaN`, `Infinity` (not JSON-compliant)
- `set` (use sorted list)
- Custom objects (must be dict/list/str/int/bool/None)

**Allowed Types:**
- `str` (UTF-8 encoded)
- `int` (arbitrary precision)
- `bool` (true/false)
- `None` (null)
- `dict` (string keys only, sorted)
- `list` (ordered, no duplicates required)

**Version Binding:**
- Protocol version (`protocol_version: "0.1"`) must be first field in signed payload
- Signed payload structure:
  ```json
  {
    "protocol_version": "0.1",
    "header": {...},
    "ciphertext": "..."
  }
  ```

**Unicode Normalization:**
- Use NFC (Canonical Decomposition, followed by Canonical Composition)
- Enforce UTF-8 encoding (reject invalid UTF-8)

### 3.3 Canonical Encoding Implementation

**Python Implementation:**
```python
def canonical_encode(obj: Any) -> bytes:
    """
    Canonical encoding with strict type checking.
    
    Raises:
        ValueError: If disallowed types are present
    """
    # Type validation
    validate_canonical_types(obj)
    
    # Canonical JSON encoding
    canonical_json_str = json.dumps(
        obj,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,  # Allow UTF-8 (will normalize)
        allow_nan=False,     # Reject NaN/Infinity
    )
    
    # Unicode normalization (NFC)
    normalized = unicodedata.normalize('NFC', canonical_json_str)
    
    # UTF-8 encoding
    return normalized.encode('utf-8')


def validate_canonical_types(obj: Any) -> None:
    """Validate that object contains only canonical types."""
    if isinstance(obj, float):
        raise ValueError("Floats disallowed in canonical encoding (use int with scaling)")
    if isinstance(obj, (float('nan'), float('inf'), float('-inf'))):
        raise ValueError("NaN/Infinity disallowed")
    if isinstance(obj, set):
        raise ValueError("Sets disallowed (use sorted list)")
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ValueError(f"Dict keys must be strings, got {type(k)}")
            validate_canonical_types(v)
    elif isinstance(obj, list):
        for item in obj:
            validate_canonical_types(item)
```

### 3.4 CBOR Alternative Consideration

**If JSON canonicalization proves insufficient:**

**CBOR (Concise Binary Object Representation) Advantages:**
- Deterministic encoding (CBOR deterministic mode)
- No float ambiguity (CBOR tags for decimal)
- Smaller encoding size
- Standardized canonical form (RFC 7049)

**CBOR Disadvantages:**
- Less human-readable (binary format)
- Additional dependency (`cbor2` library)
- Less familiar to developers

**Decision:** **Stick with JSON** for v0.1
- JSON is human-readable (important for debugging)
- Strict type validation eliminates float ambiguity
- No additional dependency required
- If issues arise, CBOR can be adopted in future version

**Fallback Plan:**
- If JSON canonicalization issues discovered, document in threat model
- Propose CBOR migration in v0.2 if needed

---

## 4. Replay Pruning Policy Justification

### 4.1 Current Policy

**24-hour pruning window:**
- Replay entries older than 24 hours are pruned from replay state
- Rationale: Reduces database size, prevents unbounded growth

### 4.2 Justification

**Why 24 hours is safe:**

1. **Timestamp Window Enforcement:**
   - Envelopes must have timestamp within ±5 minutes of current time
   - Envelope older than 5 minutes is rejected (replay protection)
   - Therefore: Envelope older than 24 hours cannot be valid (already rejected by timestamp check)

2. **Replay Detection Window:**
   - Replay protection is **immediate** (checked on delivery)
   - Once envelope is seen, replay_key is added to replay state
   - Subsequent identical envelopes are rejected immediately
   - 24-hour retention is for **audit/logging**, not replay detection

3. **Storage Boundedness:**
   - Without pruning, replay state grows unbounded
   - 24-hour window limits growth to ~86,400 entries/day (if 1 msg/sec)
   - Practical limit: ~1M entries (manageable SQLite size)

### 4.3 Configurability

**Question:** Should replay window be configurable?

**Decision:** **No** (for v0.1)

**Rationale:**
- 24-hour window is safe (envelopes older than 5 minutes are already rejected)
- Configurability adds complexity without security benefit
- Future versions can add configuration if needed

**Future Consideration:**
- If agent transport requires longer replay windows, add configuration in v0.2
- Configuration would be in `runtime/mailbox/config.json` (git-ignored)

### 4.4 Impact on Agent Transport

**Current (v0.1):**
- Replay window: 24 hours
- Timestamp window: ±5 minutes
- **Impact:** Agent transport must deliver envelopes within 5 minutes of creation

**Future (Agent Transport):**
- May require longer timestamp windows (network latency)
- May require longer replay windows (multi-hop routing)
- **Migration Path:** Extend timestamp window + replay window in transport layer

**Design Decision:**
- Keep v0.1 replay window fixed (24 hours)
- Transport layer can extend windows as needed
- Replay state remains local (no network sync required)

---

## 5. Updated Risk Delta

### 5.1 Security Risks (Updated)

| Risk | Current (v0) | Proposed (v0.1) | Delta |
|------|---------------|-----------------|-------|
| **Replay attacks** | JSON cache (no integrity) | SQLite with full SHA256 replay_key | ✅ **IMPROVED** |
| **File tampering** | No detection | Content-addressed (full SHA256) + atomic writes | ✅ **IMPROVED** |
| **Symlink attacks** | No protection | Explicit symlink rejection | ✅ **IMPROVED** |
| **Signature forgery** | No version binding | Version in signed material | ✅ **IMPROVED** |
| **Protocol drift** | Informal | Explicit schema + version | ✅ **IMPROVED** |
| **Hash collision** | N/A | Full SHA256 (no truncation) | ✅ **IMPROVED** |
| **Canonical ambiguity** | JSON float ambiguity | Strict type validation (no floats) | ✅ **IMPROVED** |

**Overall Security Delta:** ✅ **POSITIVE** — All changes improve security posture.

### 5.2 Operational Risks (Updated)

| Risk | Current (v0) | Proposed (v0.1) | Delta |
|------|---------------|-----------------|-------|
| **Data loss** | Low (simple JSON) | Low (SQLite + migration) | ⚠️ **NEUTRAL** |
| **Compatibility** | N/A | Requires migration | ⚠️ **REQUIRES MIGRATION** |
| **Complexity** | Low | Medium (codec + schema + replay) | ⚠️ **INCREASED** |
| **Testing burden** | Low | Medium (dual format + canonical tests) | ⚠️ **INCREASED** |
| **Filename length** | Short (UUID) | Long (64-char hex) | ⚠️ **INCREASED** (acceptable) |

**Overall Operational Delta:** ⚠️ **NEUTRAL** — Increased complexity offset by improved security.

**Filename Length Impact:**
- Full SHA256: 64 hex characters
- Filesystem limits: Most filesystems support 255+ character filenames
- **Decision:** Acceptable (no filesystem compatibility issues expected)

### 5.3 Governance Compliance (Updated)

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
| **No float ambiguity** | ✅ PASS | Floats disallowed in canonical encoding |

**Overall Governance Delta:** ✅ **COMPLIANT** — No violations introduced.

### 5.4 Breaking Changes Summary (Updated)

| Change | Breaking? | Impact | Migration |
|--------|-----------|--------|-----------|
| **Signature format** | ⚠️ Yes | Protocol version in signed material | Dual format support + migration script |
| **File naming** | ⚠️ Yes | Content-addressed (full SHA256) | Migration script converts filenames |
| **Replay state** | ⚠️ Yes | JSON → SQLite with replay_key | Migration script imports cache |
| **Canonical encoding** | ⚠️ Yes | Strict type validation (no floats) | v0 envelopes may contain floats (handle gracefully) |

**Migration Strategy:**
1. **Dual Format Support:** v0.1 code reads both v0 and v0.1 formats
2. **Migration Script:** `tools/migrate_mailbox_v0_to_v0.1.py`
3. **Graceful Degradation:** v0 envelopes with floats handled (converted to int if possible)

---

## 6. Updated Implementation Plan

### Phase 1: Threat Model & Schema (Non-Breaking)
1. Create `docs/calyx_mail_protocol_threat_model_v0.1.md`
   - Explicit replay definition
   - Replay key formula specification
   - Full SHA256 hash justification
2. Create `spec/mail/` directory
3. Create `spec/mail/envelope_v0.1.json`
4. Create `spec/mail/receipt_v0.1.json`
5. Create `spec/mail/replay_state_v0.1.md` (replay key specification)
6. Create `spec/mail/signed_payload_v0.1.md`
7. Create `spec/mail/canonical_encoding_v0.1.md` (formal encoding contract)

### Phase 2: Codec Module (Breaking - Signature Format)
1. Create `calyx/mail/codec.py`
2. Implement canonical encoding with strict type validation
3. Implement version detection
4. Implement v0.1 canonical encoding/decoding
5. Implement v0 legacy support (handle floats gracefully)
6. Add property tests for canonicalization

### Phase 3: Replay Protection Upgrade (Breaking - State Format)
1. Design SQLite schema with `replay_key` (full SHA256)
2. Implement `calyx/mail/replay.py` module
3. Replace JSON cache with SQLite
4. Add integrity protection (content-addressed hash)
5. Implement 24-hour pruning
6. Add migration script

### Phase 4: Mailbox Hardening (Breaking - File Naming)
1. Refactor `mailbox.py` for content-addressed filenames (full SHA256)
2. Add atomic write functions
3. Add symlink protection
4. Add file substitution detection (hash verification)
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
5. Test canonical encoding property tests

---

## 7. Governance Compliance Verification (Final)

### 7.1 Constraint Checklist (Updated)

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
| **No float ambiguity** | ✅ PASS | Floats disallowed in canonical encoding |
| **Full hash integrity** | ✅ PASS | Full SHA256 (no truncation) |

### 7.2 Anti-Drift Verification (Updated)

| Risk | Status | Mitigation |
|------|--------|------------|
| **Agent execution semantics** | ✅ AVOIDED | No command payload types |
| **Mail as control plane** | ✅ AVOIDED | Content remains read-only |
| **Remote identity discovery** | ✅ AVOIDED | No network code added |
| **Key exchange automation** | ✅ AVOIDED | Manual key exchange remains |
| **Background daemons** | ✅ AVOIDED | No daemon code added |
| **Hash collision risk** | ✅ MITIGATED | Full SHA256 (no truncation) |
| **Canonical ambiguity** | ✅ MITIGATED | Strict type validation (no floats) |

---

## 8. Approval Checklist (Updated)

**Before implementation, confirm:**

1. ✅ Full SHA256 hash (no truncation) — **ADDRESSED**
2. ✅ Explicit replay identity formalization — **ADDRESSED**
3. ✅ Formal canonical encoding contract — **ADDRESSED**
4. ✅ Replay pruning policy justification — **ADDRESSED**
5. ✅ Updated risk delta — **ADDRESSED**
6. ✅ Governance invariants remain intact — **VERIFIED**

**Status:** ✅ **ALL CLARIFICATIONS ADDRESSED**

---

## 9. Summary of Changes from Original Plan

| Aspect | Original | Revised | Reason |
|--------|----------|---------|--------|
| **Hash length** | 16 hex chars (truncated) | 64 hex chars (full SHA256) | Collision risk mitigation |
| **Replay key** | Ambiguous (msg_id vs hash) | Explicit: `SHA256(canonical_envelope)` | Clarity + security |
| **Canonical encoding** | Informal JSON | Formal spec + strict validation | Ambiguity elimination |
| **Float handling** | Not specified | Explicitly disallowed | Canonical ambiguity |
| **Replay pruning** | 24 hours (not justified) | 24 hours (justified) | Policy clarity |

---

**Plan Status:** ✅ **REVISED AND READY**  
**Governance Status:** ✅ **COMPLIANT**  
**Risk Level:** ⚠️ **MEDIUM** (breaking changes with migration path)  
**Clarifications:** ✅ **ALL ADDRESSED**

---

*Revised plan generated 2026-02-12. All architectural tightenings addressed. Ready for implementation approval.*
