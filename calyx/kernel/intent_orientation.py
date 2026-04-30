"""
WO_REQUEST_ORIENTATION_PROTOCOL_V1/V2 — Human-Sovereign Entry Gate.
Deterministic intent classification. No LLM. Must run before any tool, synthesis, or model.
V2: INTENT_FAILURE_EVENT_QUERY, INTENT_COMPOUND_QUERY, compound target parsing.
"""
from __future__ import annotations

import re
from typing import Literal

IntentType = Literal[
    "INTENT_HEARTBEAT",
    "INTENT_FILE_LOCATION",
    "INTENT_CONFIRMATION",
    "INTENT_EXECUTE",
    "INTENT_STATE_QUERY",
    "INTENT_FAILURE_EVENT_QUERY",
    "INTENT_COMPOUND_QUERY",
    "INTENT_FREE_CHAT",
    "INTENT_UNKNOWN",
]


def parse_compound_targets(user_text: str) -> tuple[str | None, str | None]:
    """
    Extract search target X and file-location target Y from compound query.
    Pattern: "search for X and tell me which file defines Y" or "find X and show Y".
    Returns (X, Y) or (None, None) if not compound.
    """
    lower = (user_text or "").lower()
    x, y = None, None
    # "search for X" or "search the Station repo for X"
    m = re.search(r"search\s+(?:the\s+station\s+repo\s+)?for\s+([^.?!]+?)(?:\s+and\s+|\s*\.|$)", lower, re.IGNORECASE)
    if m:
        x = m.group(1).strip()
    if not x and re.search(r"find\s+([^.?!]+?)(?:\s+and\s+|\s*\.|$)", lower):
        m = re.search(r"find\s+([^.?!]+?)(?:\s+and\s+|\s*\.|$)", lower)
        if m:
            x = m.group(1).strip()
    # "which file defines Y" or "defines the Y function"
    m = re.search(r"which\s+file\s+defines\s+(?:the\s+)?([^.?!]+?)(?:\s+function)?(?:\s*\.|$)", lower, re.IGNORECASE)
    if m:
        y = m.group(1).strip()
    if not y and "defines" in lower and "emit" in lower:
        y = "emit"
    if not y and "defines" in lower and "event_ledger" in lower:
        y = "event_ledger"
    return (x, y) if (x and y) else (None, None)


def is_compound_query(user_text: str) -> bool:
    """True if search target X and file-location target Y both present and X != Y."""
    x, y = parse_compound_targets(user_text)
    if not x or not y:
        return False
    x_norm = x.lower().replace("_", " ").replace("-", " ")
    y_norm = y.lower().replace("_", " ").replace("-", " ")
    if x_norm == y_norm:
        return False
    if ("event_ledger" in x_norm or "event ledger" in x_norm) and "emit" in y_norm:
        return False
    return True


def classify_intent(user_text: str) -> IntentType:
    """
    Deterministic intent classification. No LLM.
    Order matters: more specific intents checked first.
    """
    t = (user_text or "").strip()
    if not t or len(t) > 2000:
        return "INTENT_UNKNOWN"
    lower = t.lower()

    # INTENT_CONFIRMATION — simple acknowledgments
    if _is_confirmation(lower, t):
        return "INTENT_CONFIRMATION"

    # INTENT_HEARTBEAT — produce latest Station heartbeat
    if "heartbeat" in lower:
        return "INTENT_HEARTBEAT"
    if "produce" in lower and "station" in lower and ("heartbeat" in lower or "state" in lower):
        return "INTENT_HEARTBEAT"

    # INTENT_COMPOUND_QUERY — search for X and which file defines Y, X != Y (V2, check before failure event)
    if is_compound_query(t):
        return "INTENT_COMPOUND_QUERY"

    # INTENT_FAILURE_EVENT_QUERY — what does a failure event look like (V2)
    if _is_failure_event_query(lower):
        return "INTENT_FAILURE_EVENT_QUERY"

    # INTENT_FILE_LOCATION — where is X defined / which file defines X (only if NOT compound)
    if _is_file_location(lower):
        return "INTENT_FILE_LOCATION"

    # INTENT_EXECUTE — structured task
    if "execute" in lower:
        return "INTENT_EXECUTE"

    # INTENT_STATE_QUERY — state-related (but not heartbeat)
    if "state" in lower and "heartbeat" not in lower:
        return "INTENT_STATE_QUERY"

    return "INTENT_FREE_CHAT"


def _is_confirmation(lower: str, raw: str) -> bool:
    """Confirmation patterns — bypass LLM."""
    patterns = (
        "confirm receipt",
        "confirm receipt of",
        "acknowledge",
        "acknowledged",
        "no further action",
        "no action necessary",
        "got it",
        "received",
        "test message",
    )
    for p in patterns:
        if p in lower:
            return True
    if lower in ("cbo?", "cbo", "hello", "hi", "ping", "test"):
        return True
    return False


def _is_failure_event_query(lower: str) -> bool:
    """V2: failure event + (what | looks like | format | define | confirm)."""
    if "failure event" not in lower:
        return False
    return any(p in lower for p in ("what", "looks like", "format", "define", "confirm"))


def _is_file_location(lower: str) -> bool:
    """File location / definition queries."""
    # "where is" + (.py | emit | defined)
    if "where is" in lower:
        if ".py" in lower or "emit" in lower or "defined" in lower:
            return True
    # "which file" + defines + (emit | event_ledger)
    if "which file" in lower and ("defines" in lower or "define" in lower):
        if "emit" in lower or "event_ledger" in lower:
            return True
    # "event_ledger" + "emit" + (defined | define | file)
    if "event_ledger" in lower and "emit" in lower:
        if "defined" in lower or "define" in lower or "file" in lower:
            return True
    # "search" + "event_ledger" + "emit" (smoke test phrasing)
    if "search" in lower and "event_ledger" in lower and "emit" in lower:
        return True
    return False


def extract_file_path_from_hit(hit_line: str) -> str | None:
    """
    Extract file path from repo_search hit format: 'path:line:content'
    Handles Windows paths (C:\\path\\file.py:78:...). Returns path only, or None if unparseable.
    """
    if not hit_line or ":" not in hit_line:
        return None
    # Match path:digits: - path may contain colons (Windows C:\...)
    m = re.match(r"^(.+):\d+:", hit_line)
    if m:
        p = m.group(1).strip()
        if p:
            if "\\" in p:
                p = p.replace("\\", "/")
            return p
    # Fallback: split by :, take first part (fails for Windows)
    parts = hit_line.split(":", 2)
    if len(parts) >= 1 and parts[0].strip():
        p = parts[0].strip().replace("\\", "/")
        return p
    return None
