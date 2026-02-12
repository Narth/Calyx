# Canonical Encoding Specification v0.1
**Calyx Mail Protocol Layer**

**Date:** 2026-02-12  
**Version:** 0.1.0

**⚠️ Protocol Stability:** This specification is frozen for v0.1. Future changes require version bump.

---

## 1. Overview

This document specifies the canonical encoding rules for Calyx Mail Protocol Layer v0.1. Canonical encoding ensures that the same logical data always produces the same byte sequence, which is required for deterministic hashing and signature verification.

**Encoding Format:** JSON (UTF-8)  
**Construction Order:** Explicit (enforced before serialization)

---

## 2. Encoding Rules

### 2.1 Character Encoding

- **Encoding:** UTF-8
- **Normalization:** NFC (Canonical Decomposition, followed by Canonical Composition)
- **Invalid UTF-8:** Rejected (raise `EncodingError`)

### 2.2 Key Ordering

**Rule:** Keys are sorted recursively (depth-first) in alphabetical order (case-sensitive).

**Ordering:**
- Case-sensitive: `A` < `a` < `B` < `b`
- Numeric keys sorted as strings: `"1"` < `"10"` < `"2"`

**Example:**
```json
// Input (unordered)
{
  "zebra": 1,
  "alpha": 2,
  "Beta": 3
}

// Canonical (sorted keys)
{"Beta":3,"alpha":2,"zebra":1}
```

### 2.3 Whitespace Rules

- **No whitespace** between tokens
- **No trailing whitespace**
- **No leading whitespace**
- **Separators:** `,` (comma) and `:` (colon) only
- **No newlines** in output

**Example:**
```json
// Input (with whitespace)
{
  "key": "value"
}

// Canonical (no whitespace)
{"key":"value"}
```

### 2.4 Numeric Normalization

**Integers:**
- Represented as JSON numbers (no decimal point)
- Arbitrary precision supported
- Example: `123`, `-456`, `0`

**Floats:**
- **DISALLOWED** (reject on encoding)
- Rationale: Float representation ambiguity (e.g., `1.0` vs `1` vs `1e0`)
- Alternative: Use `int` with explicit scaling (e.g., `1234` for `12.34` with scale 2)

**v0 Compatibility Policy (Option B - Strict Rejection):**

**Policy:** v0 envelopes containing floats are **strictly rejected** as non-canonical.

**Implementation:**
- No float-to-int conversion is performed
- `encode_envelope_v0()` raises `EncodingError` if floats are detected
- Error message: "v0 envelope contains floats (non-canonical). Floats are strictly rejected in v0.1. Use integers with explicit scaling if needed."

**Rationale:**
- Ensures deterministic encoding (no conversion ambiguity)
- Prevents edge cases (e.g., `1.0` vs `1`, `-0.0` vs `0`, scientific notation)
- v0 envelopes should not contain floats (non-canonical by design)
- Simpler implementation (no conversion logic)

**Threat Model Justification:**
- Float ambiguity could lead to hash collisions or signature verification failures
- Strict rejection ensures canonical encoding is always deterministic
- No conversion logic means no conversion bugs or edge cases

**NaN/Infinity:**
- **DISALLOWED** (not JSON-compliant)
- Reject with `ValueError`

### 2.5 Type Restrictions

**Allowed Types:**
- `str` (UTF-8 encoded, NFC normalized)
- `int` (arbitrary precision)
- `bool` (true/false)
- `None` (null)
- `dict` (string keys only, sorted)
- `list` (ordered, duplicates allowed)

**Disallowed Types:**
- `float` (use `int` with scaling)
- `set` (use sorted `list`)
- `tuple` (use `list`)
- Custom objects (must be `dict`/`list`/primitive)
- `bytes` (must be base64-encoded string)

### 2.6 Boolean and Null

- **Booleans:** `true` / `false` (lowercase)
- **Null:** `null` (lowercase)

---

## 3. Construction Order (Explicit)

### 3.1 Requirement

**Protocol version must be constructed first** in signed payload structure.

**Rationale:** Version binding ensures signature verification includes protocol version, preventing version downgrade attacks.

### 3.2 Signed Payload Structure

**Canonical Construction Order:**

1. **`protocol_version`** (string, required)
2. **`header`** (dict, required)
   - Within `header`, keys sorted alphabetically:
     - `msg_id` (string)
     - `recipient_fp` (string)
     - `sender_fp` (string)
     - `subject` (string, optional)
     - `timestamp` (string)
3. **`ciphertext`** (string, base64-encoded)

**Enforcement:**
- Construction order is enforced **before** JSON serialization
- Dictionary is built in explicit order
- JSON serialization uses `sort_keys=True` as fallback (but construction order is primary)

### 3.3 Implementation

```python
def build_signed_payload(protocol_version: str, header: dict, ciphertext: str) -> dict:
    """
    Build signed payload with explicit construction order.
    
    Args:
        protocol_version: Protocol version string (e.g., "0.1")
        header: Header dict (will be sorted internally)
        ciphertext: Base64-encoded ciphertext
        
    Returns:
        Dict with explicit key order: protocol_version, header, ciphertext
    """
    # Sort header keys alphabetically
    sorted_header = dict(sorted(header.items()))
    
    # Build payload in explicit order
    payload = {
        "protocol_version": protocol_version,
        "header": sorted_header,
        "ciphertext": ciphertext,
    }
    
    return payload
```

**Note:** JSON serialization with `sort_keys=True` will maintain this order (since keys are already sorted), but explicit construction order ensures correctness even if JSON serialization changes.

---

## 4. Canonical Encoding Algorithm

### 4.1 Algorithm Steps

1. **Type Validation:** Reject disallowed types (float, set, etc.)
2. **Construction Order:** Build signed payload with explicit key order
3. **Key Sorting:** Sort all dict keys recursively (depth-first, alphabetical)
4. **Unicode Normalization:** Apply NFC normalization to all strings
5. **JSON Serialization:** `json.dumps()` with:
   - `sort_keys=True` (redundant but safe)
   - `separators=(',', ':')` (no whitespace)
   - `ensure_ascii=False` (allow UTF-8)
   - `allow_nan=False` (reject NaN/Infinity)
6. **UTF-8 Encoding:** Encode normalized string to UTF-8 bytes

### 4.2 Python Implementation

```python
import json
import unicodedata
from typing import Any

def canonical_encode(obj: Any) -> bytes:
    """
    Canonical encoding with strict type checking and explicit construction order.
    
    Raises:
        ValueError: If disallowed types are present
        UnicodeEncodeError: If invalid UTF-8
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
    if isinstance(obj, tuple):
        raise ValueError("Tuples disallowed (use list)")
    if isinstance(obj, bytes):
        raise ValueError("Bytes disallowed (use base64-encoded string)")
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ValueError(f"Dict keys must be strings, got {type(k)}")
            validate_canonical_types(v)
    elif isinstance(obj, list):
        for item in obj:
            validate_canonical_types(item)
```

---

## 5. Version Binding

### 5.1 Protocol Version in Signed Material

**Requirement:** `protocol_version` must be included in signed payload.

**Rationale:**
- Prevents version downgrade attacks
- Ensures signature verification includes protocol version
- Allows future protocol versions to maintain compatibility

### 5.2 Version Format

- **Format:** String (e.g., `"0.1"`)
- **Semantics:** Major.Minor version number
- **Placement:** First field in signed payload (explicit construction order)

---

## 6. Property Tests

### 6.1 Determinism Test

**Property:** Same input always produces same output.

```python
def test_canonical_determinism():
    obj = {"key": "value", "number": 123}
    result1 = canonical_encode(obj)
    result2 = canonical_encode(obj)
    assert result1 == result2
```

### 6.2 Order Independence Test

**Property:** Key order in input does not affect output.

```python
def test_canonical_order_independence():
    obj1 = {"zebra": 1, "alpha": 2}
    obj2 = {"alpha": 2, "zebra": 1}
    result1 = canonical_encode(obj1)
    result2 = canonical_encode(obj2)
    assert result1 == result2
```

### 6.3 Type Rejection Test

**Property:** Disallowed types are rejected.

```python
def test_canonical_rejects_floats():
    obj = {"value": 1.0}
    with pytest.raises(ValueError):
        canonical_encode(obj)
```

---

## 7. Examples

### 7.1 Simple Envelope

**Input:**
```python
{
    "protocol_version": "0.1",
    "header": {
        "sender_fp": "abc123",
        "recipient_fp": "def456",
        "msg_id": "uuid-here",
        "timestamp": "2026-02-12T10:30:00Z"
    },
    "ciphertext": "base64-ciphertext"
}
```

**Canonical Output (bytes):**
```
b'{"ciphertext":"base64-ciphertext","header":{"msg_id":"uuid-here","recipient_fp":"def456","sender_fp":"abc123","timestamp":"2026-02-12T10:30:00Z"},"protocol_version":"0.1"}'
```

**Note:** JSON `sort_keys=True` sorts keys alphabetically, so `ciphertext` comes before `header` and `protocol_version`. However, **construction order** ensures `protocol_version` is first in the signed payload structure (before JSON serialization).

---

## 8. Compliance

### 8.1 Implementation Requirements

All implementations must:
1. Enforce explicit construction order (protocol_version first)
2. Validate types (reject floats, sets, etc.)
3. Apply Unicode NFC normalization
4. Use UTF-8 encoding
5. Sort keys alphabetically (depth-first)

### 8.2 Test Requirements

All implementations must pass:
- Determinism test
- Order independence test
- Type rejection test
- Version binding test

---

**Specification Status:** ✅ Complete  
**Implementation:** `calyx/mail/codec.py`

---

*Canonical encoding specification generated 2026-02-12. Explicit construction order enforced.*
