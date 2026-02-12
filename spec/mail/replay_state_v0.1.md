# Replay State Schema v0.1
**Calyx Mail Protocol Layer**

**Date:** 2026-02-12  
**Version:** 0.1.0

---

## 1. Overview

This document specifies the replay state database schema for Calyx Mail Protocol Layer v0.1. Replay state prevents duplicate processing of envelopes using content-addressed replay keys.

**Storage:** SQLite database (`runtime/mailbox/replay_state.db`)  
**Git Status:** Ignored (runtime artifact)

---

## 2. Replay Key Definition

### 2.1 Replay Key Formula

```
replay_key = SHA256(canonical_envelope_bytes)
```

Where `canonical_envelope_bytes` is the deterministic canonical encoding of the entire envelope (including `protocol_version`, `header`, `ciphertext`, `signature`).

### 2.2 Replay Key Properties

- **Length:** 64 hexadecimal characters (full SHA256 hash)
- **Deterministic:** Same envelope always produces same replay key
- **Tamper-Resistant:** Any modification to envelope changes replay key
- **Cryptographic:** 2^256 collision resistance

---

## 3. SQLite Schema

### 3.1 Table Definition

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

### 3.2 Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `replay_key` | TEXT (PRIMARY KEY) | Full SHA256 hash of canonical envelope (64 hex chars) |
| `msg_id` | TEXT (NOT NULL) | Original message ID (UUID v4) for correlation |
| `sender_fp` | TEXT (NOT NULL) | Sender fingerprint (for allowlist correlation) |
| `recipient_fp` | TEXT (NOT NULL) | Recipient fingerprint (for routing correlation) |
| `seen_at` | TIMESTAMP (NOT NULL) | When envelope was first seen (UTC, for pruning) |
| `envelope_timestamp` | TEXT (NOT NULL) | Original envelope timestamp (ISO 8601, for pruning) |

### 3.3 Indexes

- **Primary Key:** `replay_key` (unique, for fast lookup)
- **Index on `seen_at`:** For pruning queries (find entries older than 24 hours)
- **Index on `msg_id`:** For receipt correlation (find receipt by msg_id)

---

## 4. SQLite Hardening

### 4.1 Foreign Keys

```sql
PRAGMA foreign_keys = ON;
```

**Rationale:** Enables foreign key constraints (if future tables reference replay_state).

### 4.2 Write-Ahead Logging (WAL)

```sql
PRAGMA journal_mode = WAL;
```

**Rationale:**
- Better concurrency (multiple readers, single writer)
- Improved performance
- Atomic transactions

### 4.3 Transaction Atomicity

**All operations must be atomic:**

```python
with db.transaction():
    # Check replay_key
    if db.has_replay_key(replay_key):
        raise ReplayError("Duplicate envelope")
    
    # Insert replay_key
    db.insert_replay_key(replay_key, msg_id, sender_fp, recipient_fp, seen_at, envelope_timestamp)
```

---

## 5. Replay Detection Algorithm

### 5.1 Algorithm

1. **Compute Replay Key:**
   ```python
   canonical_bytes = codec.encode_envelope_v0_1(envelope)
   replay_key = hashlib.sha256(canonical_bytes).hexdigest()  # Full SHA256
   ```

2. **Check Replay State:**
   ```python
   if replay_db.has_replay_key(replay_key):
       raise ReplayError(f"Envelope already seen: {replay_key}")
   ```

3. **Add to Replay State:**
   ```python
   replay_db.insert_replay_key(
       replay_key=replay_key,
       msg_id=envelope["header"]["msg_id"],
       sender_fp=envelope["header"]["sender_fp"],
       recipient_fp=envelope["header"]["recipient_fp"],
       seen_at=datetime.now(timezone.utc),
       envelope_timestamp=envelope["header"]["timestamp"]
   )
   ```

### 5.2 Timestamp Dependency

**CRITICAL:** Replay detection assumes timestamp window enforcement (±5 minutes).

- Envelopes with invalid timestamps are rejected **before** replay check
- Replay state is consulted only for envelopes with valid timestamps
- 24-hour retention is for audit/logging, not validity enforcement

---

## 6. Pruning Policy

### 6.1 Retention Window

**Retention:** 24 hours

**Rationale:**
- Envelopes older than 5 minutes are already rejected by timestamp check
- 24-hour retention is for audit/logging purposes
- Prevents unbounded database growth

### 6.2 Pruning Algorithm

```python
def prune_replay_state(db, retention_hours=24):
    """
    Prune replay state entries older than retention_hours.
    
    Args:
        db: Replay state database connection
        retention_hours: Retention window in hours (default: 24)
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
    
    with db.transaction():
        db.execute(
            "DELETE FROM replay_state WHERE seen_at < ?",
            (cutoff_time,)
        )
```

### 6.3 Pruning Trigger

**When to prune:**
- On mailbox operations (periodic)
- On startup (optional)
- Manual trigger via CLI

**Frequency:** Once per day (or on-demand)

---

## 7. Database Location

**Path:** `runtime/mailbox/replay_state.db`

**Git Status:** Ignored (runtime artifact)

**Permissions:** 0600 (owner read/write only, where supported)

---

## 8. Migration from v0

**v0 Replay State:** JSON file (`runtime/mailbox/seen_cache.json`)

**Migration:**
1. Read JSON file (list of msg_ids)
2. For each msg_id, compute replay_key from envelope (if envelope exists)
3. Insert into SQLite database
4. Preserve original JSON file as backup

**Note:** v0 replay state only contains msg_ids, not full replay keys. Migration requires access to original envelopes.

---

**Schema Status:** ✅ Complete  
**Implementation:** `calyx/mail/replay.py`

---

*Replay state schema generated 2026-02-12. SQLite hardening specified.*
