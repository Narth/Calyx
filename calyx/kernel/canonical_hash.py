"""
WO_CANONICAL_RESPONSE_HASH_V1 — Cryptographic hashing for canonical bundles.
"""
from __future__ import annotations

import hashlib


def sha256_hex(data: bytes | str) -> str:
    """Return SHA-256 hex digest of bytes or UTF-8 encoded string."""
    if isinstance(data, str):
        data = data.encode("utf-8", errors="replace")
    return hashlib.sha256(data).hexdigest()
