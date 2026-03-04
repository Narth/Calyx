"""
Ollama Gate: rate limit, inflight cap, cooldown on failure.
Deny-by-default if caller_key missing. Emits receipts to runtime/receipts/perf/.
Stdlib only. Config via env. Reversible via OLLAMA_GATE_ENABLED=0.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WO_ID = "WO_OLLAMA_GATE_V1"

_GATE_LOCK = threading.Lock()
_INFLIGHT: dict[str, int] = defaultdict(int)
_LAST_CALL: dict[str, float] = {}
_FAILURE_COUNT: dict[str, int] = defaultdict(int)
_COOLDOWN_UNTIL: dict[str, float] = {}


def _env_bool(key: str, default: bool) -> bool:
    v = os.environ.get(key, "").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    if v in ("1", "true", "yes", "on"):
        return True
    return default


def _env_int(key: str, default: int) -> int:
    try:
        return max(0, int(os.environ.get(key, str(default)).strip() or default))
    except ValueError:
        return default


def _get_config() -> dict[str, Any]:
    return {
        "enabled": _env_bool("OLLAMA_GATE_ENABLED", True),
        "max_inflight": _env_int("OLLAMA_MAX_INFLIGHT", 1),
        "min_interval_ms": _env_int("OLLAMA_MIN_INTERVAL_MS", 750),
        "failure_cooldown_s": _env_int("OLLAMA_FAILURE_COOLDOWN_S", 30),
        "failure_threshold": _env_int("OLLAMA_FAILURE_THRESHOLD", 3),
    }


def _resolve_perf_dir() -> Path:
    try:
        from .paths import resolve_perf_receipts_dir, resolve_repo_root
        return resolve_perf_receipts_dir(resolve_repo_root())
    except ImportError:
        return Path.cwd() / "runtime" / "receipts" / "perf"


def _commit_sha() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=Path(__file__).resolve().parents[2],
        )
        return (r.stdout or "").strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def _request_fingerprint(metadata: dict[str, Any]) -> str:
    """SHA256 of canonicalized request metadata. Never log raw prompts."""
    canonical = json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _emit_gate_receipt(
    decision: str,
    reason: str,
    caller_key: str,
    inflight_now: int,
    last_call_age_ms: float,
    cooldown_remaining_s: float,
    request_fingerprint: str,
) -> None:
    perf_dir = _resolve_perf_dir()
    perf_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = perf_dir / f"ollama_gate__{ts}.jsonl"
    rec = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "reason": reason,
        "caller_key": caller_key,
        "inflight_now": inflight_now,
        "last_call_age_ms": round(last_call_age_ms, 1),
        "cooldown_remaining_s": round(cooldown_remaining_s, 1),
        "request_fingerprint": request_fingerprint,
        "wo_id": WO_ID,
        "commit_sha": _commit_sha(),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")


def check(
    caller_key: str,
    request_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Check if Ollama call is allowed. Returns {allowed: bool, reason: str, retry_after_ms: int|None}.
    Deny-by-default if caller_key missing or empty.
    """
    cfg = _get_config()
    if not cfg["enabled"]:
        return {"allowed": True, "reason": "gate_disabled", "retry_after_ms": None}

    if not caller_key or not str(caller_key).strip():
        _emit_gate_receipt(
            decision="DENY",
            reason="deny_by_default: caller_key missing",
            caller_key="",
            inflight_now=0,
            last_call_age_ms=0,
            cooldown_remaining_s=0,
            request_fingerprint="",
        )
        return {"allowed": False, "reason": "deny_by_default", "retry_after_ms": None}

    key = str(caller_key).strip()
    meta = request_metadata or {}
    fp = _request_fingerprint(meta)

    with _GATE_LOCK:
        now = time.monotonic()
        inflight = _INFLIGHT[key]
        last = _LAST_CALL.get(key, 0)
        last_age_ms = (now - last) * 1000 if last else 999999
        cooldown_until = _COOLDOWN_UNTIL.get(key, 0)
        cooldown_s = max(0, cooldown_until - now) if cooldown_until > now else 0

        if cooldown_s > 0:
            _emit_gate_receipt(
                decision="DENY",
                reason="cooldown",
                caller_key=key,
                inflight_now=inflight,
                last_call_age_ms=last_age_ms,
                cooldown_remaining_s=cooldown_s,
                request_fingerprint=fp,
            )
            return {"allowed": False, "reason": "cooldown", "retry_after_ms": int(cooldown_s * 1000)}

        if inflight >= cfg["max_inflight"]:
            _emit_gate_receipt(
                decision="DENY",
                reason="inflight_cap",
                caller_key=key,
                inflight_now=inflight,
                last_call_age_ms=last_age_ms,
                cooldown_remaining_s=0,
                request_fingerprint=fp,
            )
            return {"allowed": False, "reason": "inflight_cap", "retry_after_ms": int(cfg["min_interval_ms"])}

        if last_age_ms < cfg["min_interval_ms"]:
            _emit_gate_receipt(
                decision="DENY",
                reason="rate_limited",
                caller_key=key,
                inflight_now=inflight,
                last_call_age_ms=last_age_ms,
                cooldown_remaining_s=0,
                request_fingerprint=fp,
            )
            return {"allowed": False, "reason": "rate_limited", "retry_after_ms": int(cfg["min_interval_ms"] - last_age_ms)}

        _INFLIGHT[key] += 1
        _LAST_CALL[key] = now

    _emit_gate_receipt(
        decision="ALLOW",
        reason="ok",
        caller_key=key,
        inflight_now=inflight + 1,
        last_call_age_ms=last_age_ms,
        cooldown_remaining_s=0,
        request_fingerprint=fp,
    )
    return {"allowed": True, "reason": "ok", "retry_after_ms": None}


def release(caller_key: str) -> None:
    """Release inflight slot after call completes."""
    if not caller_key:
        return
    key = str(caller_key).strip()
    with _GATE_LOCK:
        _INFLIGHT[key] = max(0, _INFLIGHT[key] - 1)


def record_failure(caller_key: str) -> None:
    """Record failure; may trigger cooldown."""
    if not caller_key:
        return
    key = str(caller_key).strip()
    cfg = _get_config()
    with _GATE_LOCK:
        _FAILURE_COUNT[key] += 1
        if _FAILURE_COUNT[key] >= cfg["failure_threshold"]:
            _COOLDOWN_UNTIL[key] = time.monotonic() + cfg["failure_cooldown_s"]
            _FAILURE_COUNT[key] = 0


def record_success(caller_key: str) -> None:
    """Reset failure count on success."""
    if not caller_key:
        return
    key = str(caller_key).strip()
    with _GATE_LOCK:
        _FAILURE_COUNT[key] = 0
