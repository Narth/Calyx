# Calyx Mail Protocol State Machine v0.1
**Agent-Foundation Edition**

**Date:** 2026-02-12  
**Version:** 0.1.0

**⚠️ Protocol Stability:** This specification is frozen for v0.1. Future changes require version bump.

---

## 1. Overview

This document defines the explicit protocol state machine for Calyx Mail Protocol Layer v0.1. The state machine describes valid states of a message and legal transitions between states.

**Purpose:** Formalize protocol semantics, prevent invalid state transitions, enable test coverage.

---

## 2. Message States

### 2.1 State Definitions

| State | Description | Observable Properties |
|-------|-------------|----------------------|
| **Created** | Envelope structure created (not yet signed) | Has `header`, `ciphertext`; no `signature` |
| **Signed** | Signature computed and attached | Has `signature` field; signature valid |
| **Encrypted** | Plaintext encrypted (sealed box) | Has `ciphertext` field; ciphertext decryptable |
| **Delivered** | Written to recipient's inbox | File exists in `runtime/mailbox/inbox/` |
| **Opened** | Recipient decrypted and verified | Receipt status: "delivered" |
| **Read** | Recipient opened message | Receipt status: "read" |
| **Failed** | Decryption/verification failed | Receipt status: "failed" |

### 2.2 State Transitions

**Valid Transitions:**

```
Created → Signed → Encrypted → Delivered → Opened → Read
                              ↓
                           Failed
```

**Invalid Transitions:**

- ❌ Cannot skip "Signed" → "Encrypted" (signature required before encryption verification)
- ❌ Cannot decrypt without signature verification
- ❌ Cannot issue receipt without delivery
- ❌ Cannot transition from "Failed" to "Opened" (must retry from "Delivered")

---

## 3. State Machine Implementation

### 3.1 State Detection

**Function:** `detect_envelope_state(envelope: dict, runtime_dir: Path) -> str`

```python
def detect_envelope_state(envelope: dict, runtime_dir: Path) -> str:
    """
    Detect current state of envelope.
    
    Returns:
        State string: "created", "signed", "encrypted", "delivered", "opened", "read", "failed"
    """
    # Check if signed
    if "signature" not in envelope:
        return "created"
    
    # Check if encrypted
    if "ciphertext" not in envelope:
        return "created"
    
    # Check if delivered (file exists in inbox)
    content_hash = compute_envelope_hash(envelope)
    inbox_path = runtime_dir / "mailbox" / "inbox" / f"{content_hash}.json"
    if not inbox_path.exists():
        return "encrypted"  # Signed and encrypted, but not delivered
    
    # Check receipt status
    receipt_status = get_receipt_status(envelope["header"]["msg_id"], runtime_dir)
    if receipt_status == "read":
        return "read"
    elif receipt_status == "delivered":
        return "opened"
    elif receipt_status == "failed":
        return "failed"
    
    return "delivered"
```

### 3.2 Transition Validation

**Function:** `validate_state_transition(from_state: str, to_state: str) -> bool`

```python
VALID_TRANSITIONS = {
    "created": ["signed"],
    "signed": ["encrypted"],
    "encrypted": ["delivered", "failed"],
    "delivered": ["opened", "failed"],
    "opened": ["read"],
    "read": [],  # Terminal state
    "failed": [],  # Terminal state
}

def validate_state_transition(from_state: str, to_state: str) -> bool:
    """Validate that state transition is legal."""
    return to_state in VALID_TRANSITIONS.get(from_state, [])
```

---

## 4. State-Specific Operations

### 4.1 Created → Signed

**Operation:** `create_envelope()` → `sign_envelope()`

**Requirements:**
- Envelope structure exists
- Header, ciphertext present
- Signature computation succeeds

**Invalid:** Cannot skip signature (signature required for verification)

### 4.2 Signed → Encrypted

**Operation:** Signature verification succeeds

**Requirements:**
- Signature present and valid
- Ciphertext present and decryptable

**Invalid:** Cannot decrypt without signature verification

### 4.3 Encrypted → Delivered

**Operation:** `deliver_to_inbox()`

**Requirements:**
- Envelope verified and decrypted
- Allowlist check passed
- Timestamp window check passed
- Replay check passed
- File written to inbox

**Invalid:** Cannot issue receipt without delivery

### 4.4 Delivered → Opened

**Operation:** `verify_and_open_envelope()` succeeds

**Requirements:**
- Envelope file exists in inbox
- Signature verification succeeds
- Decryption succeeds
- Receipt status: "delivered"

**Invalid:** Cannot transition from "Failed" to "Opened"

### 4.5 Opened → Read

**Operation:** Recipient opens message

**Requirements:**
- Receipt status: "read"

**Invalid:** Cannot skip "Opened" → "Read"

---

## 5. Invalid Transition Handling

### 5.1 Error Types

| Error | Cause | Handling |
|-------|-------|----------|
| **StateTransitionError** | Illegal state transition | Raise exception, reject operation |
| **MissingStateError** | Required state not reached | Raise exception, reject operation |

### 5.2 Example

```python
def open_envelope(envelope: dict, runtime_dir: Path):
    """Open envelope (must be in 'delivered' state)."""
    current_state = detect_envelope_state(envelope, runtime_dir)
    
    if current_state not in ["delivered", "opened"]:
        raise StateTransitionError(
            f"Cannot open envelope in state '{current_state}'. "
            f"Expected: 'delivered' or 'opened'"
        )
    
    # Proceed with opening
    ...
```

---

## 6. Test Coverage

### 6.1 State Machine Tests

**Test:** Valid transitions
```python
def test_valid_transitions():
    assert validate_state_transition("created", "signed")
    assert validate_state_transition("signed", "encrypted")
    assert validate_state_transition("encrypted", "delivered")
    assert validate_state_transition("delivered", "opened")
    assert validate_state_transition("opened", "read")
```

**Test:** Invalid transitions
```python
def test_invalid_transitions():
    assert not validate_state_transition("created", "encrypted")  # Skip signed
    assert not validate_state_transition("failed", "opened")  # Cannot recover
    assert not validate_state_transition("read", "opened")  # Terminal state
```

**Test:** State detection
```python
def test_state_detection():
    envelope = create_envelope(...)
    assert detect_envelope_state(envelope, runtime_dir) == "encrypted"
    
    deliver_to_inbox(envelope, runtime_dir, ...)
    assert detect_envelope_state(envelope, runtime_dir) == "delivered"
```

---

## 7. Protocol Invariants

### 7.1 State Invariants

| State | Invariant |
|-------|-----------|
| **Created** | No signature present |
| **Signed** | Signature present and verifiable |
| **Encrypted** | Ciphertext present and decryptable |
| **Delivered** | File exists in inbox |
| **Opened** | Receipt status: "delivered" |
| **Read** | Receipt status: "read" |
| **Failed** | Receipt status: "failed" |

### 7.2 Transition Invariants

- **No skipping:** Cannot skip required states
- **No recovery:** Cannot recover from "Failed" state
- **No regression:** Cannot go backwards (e.g., "Read" → "Opened")

---

## 8. Future Considerations

### 8.1 Agent Execution (Future)

If agent execution is added in future versions:
- New state: "Executed"
- Transition: "Opened" → "Executed"
- Requires explicit governance gate

### 8.2 Network Transport (Future)

If network transport is added:
- New state: "Transmitted"
- Transition: "Encrypted" → "Transmitted" → "Delivered"
- Requires additional threat model updates

---

**State Machine Status:** ✅ Complete  
**Implementation:** State detection and transition validation in `calyx/mail/envelope.py`

---

*State machine specification generated 2026-02-12. Explicit protocol states and transitions defined.*
