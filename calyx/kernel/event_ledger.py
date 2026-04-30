"""
Station Event Ledger — append-only, human-legible, correlation-aware.
WO_STATION_EVENT_LEDGER_V1. Never throws upstream. Fallback to stderr on write failure.
WO_NERVOUS_SYSTEM_PHASE1: request-scoped corr_id via contextvars.
WO_CAUSAL_ENVELOPE_AUDIT_CLARITY_V1: causal envelope on every event.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_LEVELS = frozenset({"DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"})
LEDGER_SCHEMA_VERSION = "ledger.v1"
VALID_SYSTEM_PHASES = frozenset({"preflight", "boot", "runtime"})

# Request-scoped corr_id: set by middleware, used by emit() when corr_id not provided.
_corr_id_ctx: ContextVar[str | None] = ContextVar("event_ledger_corr_id", default=None)

# WO_CAUSAL_ENVELOPE_AUDIT_CLARITY_V1: Human auth context (set after governance check)
_request_id_ctx: ContextVar[str | None] = ContextVar("event_ledger_request_id", default=None)
_auth_mode_ctx: ContextVar[str | None] = ContextVar("event_ledger_auth_mode", default=None)
_auth_verified_ctx: ContextVar[bool | None] = ContextVar("event_ledger_auth_verified", default=None)
_signer_fingerprint_ctx: ContextVar[str | None] = ContextVar("event_ledger_signer_fingerprint", default=None)

# Task context: set at system.task.triggered, cleared at completion/failure
_task_corr_id_ctx: ContextVar[str | None] = ContextVar("event_ledger_task_corr_id", default=None)
_task_name_ctx: ContextVar[str | None] = ContextVar("event_ledger_task_name", default=None)
_schedule_id_ctx: ContextVar[str | None] = ContextVar("event_ledger_schedule_id", default=None)
_trigger_reason_ctx: ContextVar[str | None] = ContextVar("event_ledger_trigger_reason", default=None)

# System phase: preflight | boot | runtime (no tools/outbound allowed)
_system_phase_ctx: ContextVar[str | None] = ContextVar("event_ledger_system_phase", default=None)


def _resolve_ledger_dir() -> Path:
    try:
        from .paths import resolve_repo_root, resolve_ledger_dir
        return resolve_ledger_dir(resolve_repo_root())
    except ImportError:
        return Path.cwd() / "runtime" / "ledger"


def _ledger_path() -> Path:
    """Path: runtime/ledger/station_events__YYYYMMDD.jsonl"""
    d = _resolve_ledger_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"station_events__{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"


def get_ledger_dir() -> Path:
    """Resolved ledger directory (for station.service.identity). Never throws."""
    try:
        return _resolve_ledger_dir()
    except Exception:
        return Path.cwd() / "runtime" / "ledger"


def set_corr_id(corr_id: str | None) -> None:
    """Set request-scoped corr_id. Call from middleware. Never throws."""
    try:
        _corr_id_ctx.set(corr_id)
    except Exception:
        pass


def get_corr_id() -> str | None:
    """Get current request-scoped corr_id. Never throws."""
    try:
        return _corr_id_ctx.get()
    except Exception:
        return None


# --- WO_CAUSAL_ENVELOPE_AUDIT_CLARITY_V1: Task context ---


def set_task_context(
    task_corr_id: str,
    task_name: str,
    schedule_id: str,
    trigger_reason: str,
) -> None:
    """Set task-scoped context. Call at system.task.triggered. Never throws."""
    try:
        _task_corr_id_ctx.set(task_corr_id)
        _task_name_ctx.set(task_name)
        _schedule_id_ctx.set(schedule_id)
        _trigger_reason_ctx.set(trigger_reason)
    except Exception:
        pass


def clear_task_context() -> None:
    """Clear task context. Call at system.task.completed/failed. Never throws."""
    try:
        _task_corr_id_ctx.set(None)
        _task_name_ctx.set(None)
        _schedule_id_ctx.set(None)
        _trigger_reason_ctx.set(None)
    except Exception:
        pass


def get_task_context() -> dict[str, str] | None:
    """Get current task context. None if not in task. Never throws."""
    try:
        tid = _task_corr_id_ctx.get()
        if not tid:
            return None
        return {
            "task_corr_id": tid,
            "task_name": _task_name_ctx.get() or "",
            "schedule_id": _schedule_id_ctx.get() or "",
            "trigger_reason": _trigger_reason_ctx.get() or "",
        }
    except Exception:
        return None


# --- WO_CAUSAL_ENVELOPE_AUDIT_CLARITY_V1: System phase ---


def set_system_phase(phase: str) -> None:
    """Set system phase (preflight | boot | runtime). Never throws."""
    try:
        _system_phase_ctx.set(phase if phase in VALID_SYSTEM_PHASES else None)
    except Exception:
        pass


def clear_system_phase() -> None:
    """Clear system phase. Never throws."""
    try:
        _system_phase_ctx.set(None)
    except Exception:
        pass


def get_system_phase() -> str | None:
    """Get current system phase. Never throws."""
    try:
        return _system_phase_ctx.get()
    except Exception:
        return None


# --- WO_CAUSAL_ENVELOPE_AUDIT_CLARITY_V1: Human auth context ---


def set_human_auth_context(
    auth_mode: str | None = None,
    auth_verified: bool | None = None,
    signer_fingerprint: str | None = None,
    request_id: str | None = None,
) -> None:
    """Set human auth context after governance check. Never throws."""
    try:
        if auth_mode is not None:
            _auth_mode_ctx.set(auth_mode)
        if auth_verified is not None:
            _auth_verified_ctx.set(auth_verified)
        if signer_fingerprint is not None:
            _signer_fingerprint_ctx.set(signer_fingerprint)
        if request_id is not None:
            _request_id_ctx.set(request_id)
    except Exception:
        pass


def clear_human_auth_context() -> None:
    """Clear human auth context. Call at request end. Never throws."""
    try:
        _auth_mode_ctx.set(None)
        _auth_verified_ctx.set(None)
        _signer_fingerprint_ctx.set(None)
        _request_id_ctx.set(None)
    except Exception:
        pass


def _truncate_data(data: dict | None, max_keys: int = 20, max_val_len: int = 500) -> dict:
    """Keep data small. No large payloads."""
    if not data:
        return {}
    out = {}
    for i, (k, v) in enumerate(data.items()):
        if i >= max_keys:
            break
        if isinstance(v, str) and len(v) > max_val_len:
            v = v[:max_val_len] + "..."
        elif isinstance(v, (dict, list)) and len(str(v)) > max_val_len:
            v = str(v)[:max_val_len] + "..."
        out[str(k)[:64]] = v
    return out


def _emit_audit_signal(event: str, msg: str, data: dict | None = None) -> None:
    """Emit audit signal. Never throws. Avoids recursion by writing directly."""
    try:
        ts = datetime.now(timezone.utc).isoformat()
        rec = {
            "schema": LEDGER_SCHEMA_VERSION,
            "ts": ts,
            "ts_utc": ts,
            "level": "WARN",
            "component": "kernel",
            "event": event,
            "msg": msg,
            "data": data or {},
            "causal_envelope": {"causal_kind": "system", "system_phase": "audit"},
        }
        path = _ledger_path()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")
            f.flush()
    except Exception:
        pass


def with_causal_envelope(
    *,
    corr_id: str | None = None,
    task_corr_id: str | None = None,
    task_name: str | None = None,
    schedule_id: str | None = None,
    trigger_reason: str | None = None,
    auth_mode: str | None = None,
    auth_verified: bool | None = None,
    signer_fingerprint: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    Build causal envelope from context or explicit params.
    WO_CAUSAL_ENVELOPE_AUDIT_CLARITY_V1.
    Returns envelope dict. Emits audit signals for missing/ambiguous context.
    """
    _ctx_corr = None
    _ctx_task = None
    _ctx_phase = None
    try:
        _ctx_corr = _corr_id_ctx.get()
        _ctx_task = get_task_context()
        _ctx_phase = _system_phase_ctx.get()
    except Exception:
        pass

    has_corr = bool(corr_id or _ctx_corr)
    _tid = task_corr_id or (_ctx_task and _ctx_task.get("task_corr_id"))
    has_task = bool(_tid)
    has_system = bool(_ctx_phase)

    if has_corr and has_task:
        _emit_audit_signal("audit.context.ambiguous", "Both corr_id and task_corr_id set", data={"corr_id": (corr_id or _ctx_corr or "")[:32], "task_corr_id": (task_corr_id or (_ctx_task or {}).get("task_corr_id") or "")[:32]})
        has_task = False

    if has_task:
        tid = task_corr_id or (_ctx_task or {}).get("task_corr_id") or ""
        tname = task_name or (_ctx_task or {}).get("task_name") or ""
        sched = schedule_id or (_ctx_task or {}).get("schedule_id") or ""
        reason = trigger_reason or (_ctx_task or {}).get("trigger_reason") or ""
        return {
            "causal_kind": "task",
            "task_corr_id": tid[:64],
            "task_name": tname[:64],
            "schedule_id": sched[:64],
            "trigger_reason": reason[:64],
        }

    if has_corr:
        cid = (corr_id or _ctx_corr or "").strip()[:64]
        am = auth_mode or _auth_mode_ctx.get() or "gateway"
        av = auth_verified if auth_verified is not None else _auth_verified_ctx.get()
        if av is None:
            av = True
        sf = (signer_fingerprint or _signer_fingerprint_ctx.get() or "")[:128]
        rid = (request_id or _request_id_ctx.get() or cid)[:64]
        return {
            "causal_kind": "human",
            "corr_id": cid,
            "request_id": rid,
            "auth_mode": am[:32],
            "auth_verified": av,
            "signer_fingerprint": sf,
        }

    if has_system:
        return {
            "causal_kind": "system",
            "system_phase": _ctx_phase or "boot",
        }

    _emit_audit_signal("audit.context.missing", "Event emitted without causal context", data={})
    return {"causal_kind": "missing"}


def emit(
    level: str,
    component: str,
    event: str,
    msg: str,
    data: dict | None = None,
    corr_id: str | None = None,
    run_id: str | None = None,
    artifact_refs: list | None = None,
    policy: str | None = None,
    decision: str | None = None,
    task_corr_id: str | None = None,
    task_name: str | None = None,
    schedule_id: str | None = None,
    trigger_reason: str | None = None,
) -> None:
    """
    Append event to station ledger. Never throws. Fallback to stderr on failure.
    WO_CAUSAL_ENVELOPE_AUDIT_CLARITY_V1: Every event includes causal_envelope.
    """
    level = (level or "INFO").strip().upper()
    if level not in VALID_LEVELS:
        level = "INFO"
    component = (component or "kernel").strip()[:64]
    event = (event or "unknown").strip()[:128]
    msg = (msg or "").strip()[:1024]
    run_id = (run_id or "").strip()[:64] or None
    artifact_refs = artifact_refs or []
    if isinstance(artifact_refs, list):
        artifact_refs = [a if isinstance(a, dict) else {"path": str(a)} for a in artifact_refs[:10]]
    policy = (policy or "").strip()[:128] or None
    decision = (decision or "").strip()[:64] or None

    envelope = with_causal_envelope(
        corr_id=corr_id,
        task_corr_id=task_corr_id,
        task_name=task_name,
        schedule_id=schedule_id,
        trigger_reason=trigger_reason,
    )

    ts_utc = datetime.now(timezone.utc).isoformat()
    corr_id_val = envelope.get("corr_id") if envelope.get("causal_kind") == "human" else (corr_id or "")
    if not corr_id_val and envelope.get("causal_kind") == "task":
        corr_id_val = envelope.get("task_corr_id", "")

    rec = {
        "schema": LEDGER_SCHEMA_VERSION,
        "ts": ts_utc,
        "ts_utc": ts_utc,
        "level": level,
        "component": component,
        "event": event,
        "msg": msg,
        "causal_envelope": envelope,
        "corr_id": corr_id_val[:64] if corr_id_val else None,
        "run_id": run_id,
        "data": _truncate_data(data),
        "artifact_refs": artifact_refs,
        "policy": policy,
        "decision": decision,
    }
    if rec["corr_id"] is None:
        del rec["corr_id"]
    line = json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n"
    try:
        path = _ledger_path()
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
    except Exception as e:
        try:
            print(f"[event_ledger] write failed: {e}\n{line}", file=sys.stderr)
        except Exception:
            pass
