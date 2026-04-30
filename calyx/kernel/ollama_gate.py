"""
Ollama Gate: rate limit, inflight cap, cooldown on failure.
Deny-by-default if caller_key missing. Emits receipts to runtime/receipts/perf/.
Stdlib only. Config via env. Reversible via OLLAMA_GATE_ENABLED=0.
WO_OLLAMA_GATE_V2: config receipt, slow inflight detector.
WO_OLLAMA_GATE_V3: service attribution, duration receipts, attempts_last_10s, spam_suspected.
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

WO_ID = "WO_OLLAMA_GATE_V3"
SLOW_INFLIGHT_MS = 10_000
SPAM_THRESHOLD = 20
ATTEMPTS_WINDOW_S = 10.0

_GATE_LOCK = threading.Lock()
_INFLIGHT: dict[str, int] = defaultdict(int)
_INFLIGHT_START: dict[str, tuple[float, str, str, str, str]] = {}  # key -> (start, fp, model_hint, service_name, endpoint)
_ATTEMPT_TIMESTAMPS: dict[str, list[float]] = defaultdict(list)
_LAST_CALL: dict[str, float] = {}
_FAILURE_COUNT: dict[str, int] = defaultdict(int)
_COOLDOWN_UNTIL: dict[str, float] = {}
_CONFIG_RECEIPT_WRITTEN = False


def _env_bool(key: str, default: bool) -> tuple[bool, str]:
    """Returns (value, source). source: env|default|invalid."""
    raw = os.environ.get(key, "")
    v = (raw or "").strip().lower()
    if not v:
        return default, "default"
    if v in ("0", "false", "no", "off"):
        return False, "env"
    if v in ("1", "true", "yes", "on"):
        return True, "env"
    return default, "invalid"


def _env_int(key: str, default: int) -> tuple[int, str]:
    """Returns (value, source). source: env|default|invalid."""
    raw = os.environ.get(key, "")
    if not raw or not str(raw).strip():
        return default, "default"
    try:
        val = max(0, int(str(raw).strip()))
        return val, "env"
    except ValueError:
        return default, "invalid"


def _get_config_with_source() -> tuple[dict[str, Any], dict[str, str], int]:
    """Returns (effective_values, source_map, invalid_count)."""
    enabled, s_enabled = _env_bool("OLLAMA_GATE_ENABLED", True)
    max_inflight, s_max = _env_int("OLLAMA_MAX_INFLIGHT", 1)
    min_interval_ms, s_min = _env_int("OLLAMA_MIN_INTERVAL_MS", 750)
    failure_cooldown_s, s_fail = _env_int("OLLAMA_FAILURE_COOLDOWN_S", 30)
    failure_threshold, s_thr = _env_int("OLLAMA_FAILURE_THRESHOLD", 3)
    source_map = {
        "OLLAMA_GATE_ENABLED": s_enabled,
        "OLLAMA_MAX_INFLIGHT": s_max,
        "OLLAMA_MIN_INTERVAL_MS": s_min,
        "OLLAMA_FAILURE_COOLDOWN_S": s_fail,
        "OLLAMA_FAILURE_THRESHOLD": s_thr,
    }
    invalid_count = sum(1 for s in source_map.values() if s == "invalid")
    effective = {
        "OLLAMA_GATE_ENABLED": enabled,
        "OLLAMA_MAX_INFLIGHT": max_inflight,
        "OLLAMA_MIN_INTERVAL_MS": min_interval_ms,
        "OLLAMA_FAILURE_COOLDOWN_S": failure_cooldown_s,
        "OLLAMA_FAILURE_THRESHOLD": failure_threshold,
    }
    return effective, source_map, invalid_count


def _get_config() -> dict[str, Any]:
    cfg, _, _ = _get_config_with_source()
    return {
        "enabled": cfg["OLLAMA_GATE_ENABLED"],
        "max_inflight": cfg["OLLAMA_MAX_INFLIGHT"],
        "min_interval_ms": cfg["OLLAMA_MIN_INTERVAL_MS"],
        "failure_cooldown_s": cfg["OLLAMA_FAILURE_COOLDOWN_S"],
        "failure_threshold": cfg["OLLAMA_FAILURE_THRESHOLD"],
    }


def _write_config_receipt() -> None:
    """Write config receipt once on first gate use."""
    global _CONFIG_RECEIPT_WRITTEN
    with _GATE_LOCK:
        if _CONFIG_RECEIPT_WRITTEN:
            return
        _CONFIG_RECEIPT_WRITTEN = True
    effective, source_map, invalid_count = _get_config_with_source()
    perf_dir = _resolve_perf_dir()
    perf_dir.mkdir(parents=True, exist_ok=True)
    node_id = "unknown"
    try:
        p = Path(__file__).resolve().parents[2] / "runtime" / "node_id.txt"
        if p.exists():
            node_id = p.read_text(encoding="utf-8").strip() or "unknown"
    except Exception:
        pass
    rec = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "node_id": node_id,
        "commit_sha": _commit_sha(),
        "effective_values": effective,
        "source_map": source_map,
        "invalid_count": invalid_count,
    }
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = perf_dir / f"ollama_gate_config__{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False, sort_keys=True)


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


def _record_attempt(key: str) -> tuple[int, bool]:
    """Record attempt, prune to last 10s, return (attempts_last_10s, spam_suspected)."""
    now = time.monotonic()
    cutoff = now - ATTEMPTS_WINDOW_S
    _ATTEMPT_TIMESTAMPS[key] = [t for t in _ATTEMPT_TIMESTAMPS[key] if t > cutoff]
    _ATTEMPT_TIMESTAMPS[key].append(now)
    count = len(_ATTEMPT_TIMESTAMPS[key])
    return count, count > SPAM_THRESHOLD


def _emit_gate_receipt(
    decision: str,
    reason: str,
    caller_key: str,
    inflight_now: int,
    last_call_age_ms: float,
    cooldown_remaining_s: float,
    request_fingerprint: str,
    *,
    service_name: str = "unknown",
    endpoint: str = "",
    attempts_last_10s: int = 0,
    spam_suspected: bool = False,
    allow_duration_ms: float | None = None,
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
        "service_name": service_name,
        "endpoint": endpoint or "",
        "attempts_last_10s": attempts_last_10s,
        "spam_suspected": spam_suspected,
    }
    if allow_duration_ms is not None and decision == "ALLOW":
        rec["allow_duration_ms"] = round(allow_duration_ms, 1)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")


def _emit_allow_complete(
    caller_key: str,
    allow_duration_ms: float,
    request_fingerprint: str,
    service_name: str,
    endpoint: str,
) -> None:
    """Emit ALLOW_COMPLETE line when release() is called."""
    perf_dir = _resolve_perf_dir()
    perf_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = perf_dir / f"ollama_gate__{ts}.jsonl"
    rec = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "decision": "ALLOW_COMPLETE",
        "caller_key": caller_key,
        "allow_duration_ms": round(allow_duration_ms, 1),
        "request_fingerprint": request_fingerprint,
        "service_name": service_name,
        "endpoint": endpoint or "",
        "wo_id": WO_ID,
        "commit_sha": _commit_sha(),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")


def _emit_slow_inflight(caller_key: str, duration_ms: float, fp: str, model_hint: str) -> None:
    """Append slow inflight receipt."""
    perf_dir = _resolve_perf_dir()
    perf_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = perf_dir / f"ollama_inflight_slow__{ts}.jsonl"
    rec = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "caller_key": caller_key,
        "inflight_duration_ms": round(duration_ms, 1),
        "request_fingerprint": fp,
        "model_hint": model_hint or "",
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
    _write_config_receipt()
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
            service_name="unknown",
            endpoint="",
            attempts_last_10s=0,
            spam_suspected=False,
        )
        return {"allowed": False, "reason": "deny_by_default", "retry_after_ms": None}

    key = str(caller_key).strip()
    meta = request_metadata or {}
    fp = _request_fingerprint(meta)
    service_name = str(meta.get("service_name") or "unknown").strip()
    if service_name not in ("cbo_core", "avatar_web", "telemetry_gateway", "dev_harness"):
        service_name = "unknown"
    endpoint = str(meta.get("endpoint") or "").strip()[:200]

    with _GATE_LOCK:
        now = time.monotonic()
        attempts_last_10s, spam_suspected = _record_attempt(key)
        inflight = _INFLIGHT[key]
        last = _LAST_CALL.get(key, 0)
        last_age_ms = (now - last) * 1000 if last else 999999
        cooldown_until = _COOLDOWN_UNTIL.get(key, 0)
        cooldown_s = max(0, cooldown_until - now) if cooldown_until > now else 0

        def _emit_deny(r: str):
            _emit_gate_receipt(
                decision="DENY",
                reason=r,
                caller_key=key,
                inflight_now=inflight,
                last_call_age_ms=last_age_ms,
                cooldown_remaining_s=cooldown_s if r == "cooldown" else 0,
                request_fingerprint=fp,
                service_name=service_name,
                endpoint=endpoint,
                attempts_last_10s=attempts_last_10s,
                spam_suspected=spam_suspected,
            )

        if cooldown_s > 0:
            _emit_deny("cooldown")
            return {"allowed": False, "reason": "cooldown", "retry_after_ms": int(cooldown_s * 1000)}

        if inflight >= cfg["max_inflight"]:
            _emit_deny("inflight_cap")
            return {"allowed": False, "reason": "inflight_cap", "retry_after_ms": int(cfg["min_interval_ms"])}

        if last_age_ms < cfg["min_interval_ms"]:
            _emit_deny("rate_limited")
            return {"allowed": False, "reason": "rate_limited", "retry_after_ms": int(cfg["min_interval_ms"] - last_age_ms)}

        _INFLIGHT[key] += 1
        _LAST_CALL[key] = now
        model_hint = str(meta.get("model") or "")
        _INFLIGHT_START[key] = (now, fp, model_hint, service_name, endpoint)

    _emit_gate_receipt(
        decision="ALLOW",
        reason="ok",
        caller_key=key,
        inflight_now=inflight + 1,
        last_call_age_ms=last_age_ms,
        cooldown_remaining_s=0,
        request_fingerprint=fp,
        service_name=service_name,
        endpoint=endpoint,
        attempts_last_10s=attempts_last_10s,
        spam_suspected=spam_suspected,
    )
    return {"allowed": True, "reason": "ok", "retry_after_ms": None}


def release(caller_key: str) -> None:
    """Release inflight slot after call completes. Emits slow inflight + allow_complete receipts."""
    if not caller_key:
        return
    key = str(caller_key).strip()
    with _GATE_LOCK:
        _INFLIGHT[key] = max(0, _INFLIGHT[key] - 1)
        entry = _INFLIGHT_START.pop(key, None)
        if entry:
            start_time, fp, model_hint, service_name, endpoint = entry
            duration_ms = (time.monotonic() - start_time) * 1000
            _emit_allow_complete(key, duration_ms, fp, service_name, endpoint)
            if duration_ms >= SLOW_INFLIGHT_MS:
                _emit_slow_inflight(key, duration_ms, fp, model_hint)


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
