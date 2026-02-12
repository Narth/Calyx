# Signed Payload Structure v0.1
**Calyx Mail Protocol Layer**

**Date:** 2026-02-12  
**Version:** 0.1.0

---

## 1. Overview

This document specifies the exact structure of the signed payload for Calyx Mail Protocol Layer v0.1. The signed payload is the data structure over which the ed25519 signature is computed.

**Signature Algorithm:** ed25519  
**Encoding:** Canonical JSON (UTF-8, NFC normalized)

---

## 2. Signed Payload Structure

### 2.1 Fields

The signed payload contains exactly three fields, in this order:

1. **`protocol_version`** (string, required)
2. **`header`** (dict, required)
3. **`ciphertext`** (string, required)

### 2.2 Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `protocol_version` | string | Yes | Protocol version identifier (e.g., `"0.1"`) |
| `header` | dict | Yes | Envelope header (see below) |
| `ciphertext` | string | Yes | Base64-encoded x25519 sealed box ciphertext |

### 2.3 Header Structure

The `header` dict contains:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sender_fp` | string | Yes | Sender's ed25519 public key fingerprint (base64) |
| `recipient_fp` | string | Yes | Recipient's x25519 public key fingerprint (base64) |
| `msg_id` | string | Yes | Message ID (UUID v4) |
| `timestamp` | string | Yes | Message creation time (ISO 8601 UTC) |
| `subject` | string | No | Optional subject line (max 256 chars) |

**Header Key Ordering:** Keys are sorted alphabetically within the header dict.

---

## 3. Construction Order

### 3.1 Explicit Ordering

**The signed payload must be constructed in this order:**

1. `protocol_version` (first)
2. `header` (second, with keys sorted alphabetically)
3. `ciphertext` (third)

**Rationale:** Version binding ensures signature verification includes protocol version, preventing version downgrade attacks.

### 3.2 Implementation

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

---

## 4. Canonical Encoding

### 4.1 Encoding Rules

The signed payload is encoded using canonical JSON encoding (see `canonical_encoding_v0.1.md`):

1. **Type Validation:** Reject disallowed types (float, set, etc.)
2. **Key Sorting:** Sort all dict keys recursively (depth-first, alphabetical)
3. **Unicode Normalization:** Apply NFC normalization to all strings
4. **JSON Serialization:** `json.dumps()` with:
   - `sort_keys=True`
   - `separators=(',', ':')` (no whitespace)
   - `ensure_ascii=False` (allow UTF-8)
   - `allow_nan=False` (reject NaN/Infinity)
5. **UTF-8 Encoding:** Encode normalized string to UTF-8 bytes

### 4.2 Example

**Input:**
```python
payload = {
    "protocol_version": "0.1",
    "header": {
        "sender_fp": "abc123",
        "recipient_fp": "def456",
        "msg_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2026-02-12T10:30:00Z"
    },
    "ciphertext": "base64-ciphertext-here"
}
```

**Canonical JSON (before UTF-8 encoding):**
```json
{"ciphertext":"base64-ciphertext-here","header":{"msg_id":"550e8400-e29b-41d4-a716-446655440000","recipient_fp":"def456","sender_fp":"abc123","timestamp":"2026-02-12T10:30:00Z"},"protocol_version":"0.1"}
```

**Note:** JSON `sort_keys=True` sorts keys alphabetically, so `ciphertext` comes before `header` and `protocol_version`. However, **construction order** ensures `protocol_version` is first in the logical structure (before JSON serialization).

---

## 5. Signature Computation

### 5.1 Algorithm

1. **Build Signed Payload:** Construct payload with explicit order
2. **Canonical Encode:** Encode payload to canonical JSON bytes
3. **Sign:** Compute ed25519 signature over canonical bytes
4. **Base64 Encode:** Encode signature to base64 string

### 5.2 Implementation

```python
def sign_envelope(payload: dict, sender_signing_priv: bytes) -> bytes:
    """
    Sign envelope payload.
    
    Args:
        payload: Signed payload dict (with explicit construction order)
        sender_signing_priv: Sender's ed25519 private key (32 bytes)
        
    Returns:
        64-byte ed25519 signature
    """
    # Canonical encoding
    canonical_bytes = canonical_encode(payload)
    
    # Sign
    signature_bytes = sign(canonical_bytes, sender_signing_priv)
    
    return signature_bytes
```

---

## 6. Signature Verification

### 6.1 Algorithm

1. **Build Signed Payload:** Reconstruct payload from envelope (with explicit order)
2. **Canonical Encode:** Encode payload to canonical JSON bytes
3. **Verify:** Verify ed25519 signature against canonical bytes and sender's public key

### 6.2 Implementation

```python
def verify_envelope_signature(envelope: dict, sender_signing_pub: bytes) -> bool:
    """
    Verify envelope signature.
    
    Args:
        envelope: Envelope dict
        sender_signing_pub: Sender's ed25519 public key (32 bytes)
        
    Returns:
        True if signature is valid, False otherwise
    """
    # Extract signature
    signature_b64 = envelope["signature"]
    signature_bytes = base64.b64decode(signature_b64)
    
    # Build signed payload (with explicit order)
    payload = build_signed_payload(
        protocol_version=envelope["protocol_version"],
        header=envelope["header"],
        ciphertext=envelope["ciphertext"]
    )
    
    # Canonical encoding
    canonical_bytes = canonical_encode(payload)
    
    # Verify signature
    return verify(canonical_bytes, signature_bytes, sender_signing_pub)
```

---

## 7. Version Binding

### 7.1 Requirement

**Protocol version must be included in signed payload.**

**Rationale:**
- Prevents version downgrade attacks
- Ensures signature verification includes protocol version
- Allows future protocol versions to maintain compatibility

### 7.2 Version Format

- **Format:** String (e.g., `"0.1"`)
- **Semantics:** Major.Minor version number
- **Placement:** First field in signed payload (explicit construction order)

---

**Specification Status:** ✅ Complete  
**Implementation:** `calyx/mail/codec.py`, `calyx/mail/envelope.py`

---

*Signed payload specification generated 2026-02-12. Explicit construction order enforced.*
