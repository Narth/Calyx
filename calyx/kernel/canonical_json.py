"""
WO_CANONICAL_RESPONSE_HASH_V1 — Stable JSON encoding for canonical bundles.
Ensures: UTF-8, LF newlines, sorted keys, no trailing whitespace, stable numeric encoding.
"""
from __future__ import annotations

import json


def canonical_dumps(obj: dict) -> str:
    """
    Serialize dict to canonical JSON string.
    - UTF-8
    - LF newlines (no CRLF)
    - Sorted keys (recursive)
    - No trailing whitespace
    - Stable numeric encoding (no scientific notation for integers)
    """
    return json.dumps(
        _sort_keys_deep(obj),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sort_keys_deep(obj: object) -> object:
    """Recursively sort dict keys for stable output."""
    if isinstance(obj, dict):
        return {k: _sort_keys_deep(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_sort_keys_deep(v) for v in obj]
    return obj
