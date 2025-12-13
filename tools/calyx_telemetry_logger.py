"""Calyx Telemetry Layer (CTL) v0.1.1 helper utilities.

This module provides a minimal, append-only logger for writing CTL-compliant
records to the Calyx telemetry streams. It performs no scheduling or background
execution; callers must invoke these functions explicitly.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union


SCHEMA_VERSION = "ctl_v0.1"
BASE_LOG_DIR = Path("logs") / "calyx"
DEFAULT_TELEMETRY_PATH = BASE_LOG_DIR / "telemetry.jsonl"
STREAM_PATHS: Dict[str, Path] = {
    "telemetry": DEFAULT_TELEMETRY_PATH,
    "events": BASE_LOG_DIR / "events.jsonl",
    "drift_signals": BASE_LOG_DIR / "drift_signals.jsonl",
    "kernel_checkins": BASE_LOG_DIR / "kernel_checkins.jsonl",
    "node_outputs": BASE_LOG_DIR / "node_outputs.jsonl",
}
VALID_SEVERITIES = {"debug", "info", "warning", "error", "critical"}
VALID_EVENT_TYPES = {
    "agent_output",
    "agent_error",
    "governance_decision",
    "ingestion_event",
    "schema_validation",
    "health_signal",
    "nightfall_start",
    "nightfall_end",
    "session_started",
    "session_ended",
    "directive_issued",
    "directive_completed",
    "preference_drift_suspected",
    "behavior_drift_suspected",
    "autonomy_pressure_detected",
    "kernel_checkin",
    # Extensions maintained for existing helpers and log streams.
    "node_output",
    "log_integrity_breach",
    "execution_request",
    "execution_decision",
}
DEFAULT_GOVERNANCE_STATE: Dict[str, Any] = {
    "safe_mode": True,
    "autonomy_level": "reflection_only",
    "execution_gate_active": True,
    "policy_version": "calyx_theory_v0.3",
    "governance_state_version": "gov_state_v0.1",
}
DEFAULT_SAFETY_STATUS: Dict[str, Any] = {
    "violation_detected": False,
    "violation_type": None,
    "mitigation_action": None,
}


def now_iso() -> str:
    """Return current UTC time as ISO 8601 with milliseconds and 'Z' suffix."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def new_request_id(source: str = "architect_cli") -> str:
    """Generate a request_id with timestamp and short UUID for correlation."""
    return f"{now_iso()}_{source}_{uuid.uuid4().hex[:8]}"


def new_session_id(kind: str = "work_session") -> str:
    """Generate a session_id with timestamp, kind, and short UUID."""
    sanitized_timestamp = now_iso().replace(":", "").replace("-", "")
    return f"session-{sanitized_timestamp}-{kind}-{uuid.uuid4().hex[:8]}"


def standard_refusal_snippet() -> str:
    """Provide a consistent, human-first refusal/reframe message."""
    return (
        "Safe Mode and deny-all Execution Gate are active. No hidden channels; "
        "use official lanes (governance_cli / CTL) for any requests. "
        "Human review required for all capability changes."
    )

def _ensure_parent(path: Path) -> None:
    """Create parent directories for the target path if they do not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)


def _merge_defaults(
    provided: Optional[Dict[str, Any]], defaults: Dict[str, Any]
) -> Dict[str, Any]:
    """Copy defaults and update with provided values."""
    merged = dict(defaults)
    if provided:
        merged.update(provided)
    return merged


def _validate_record(record: Dict[str, Any]) -> None:
    """Validate severity and event_type against the CTL v0.1.1 taxonomy."""
    sev = record.get("severity")
    if sev not in VALID_SEVERITIES:
        raise ValueError(f"Invalid severity: {sev}")

    etype = record.get("event_type")
    if etype not in VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event_type: {etype}")


def log_telemetry(
    *,
    event_type: str,
    subsystem: str,
    severity: str,
    payload: Dict[str, Any],
    reflection: Optional[str] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    governance_state: Optional[Dict[str, Any]] = None,
    safety_status: Optional[Dict[str, Any]] = None,
    architect_id: str = "architect-local-001",
    station_id: str = "station-calyx-local-001",
    path: Union[str, Path] = DEFAULT_TELEMETRY_PATH,
) -> None:
    """Append a CTL v0.1 record to the specified .jsonl path."""
    target = Path(path)
    _ensure_parent(target)

    record = {
        "timestamp": now_iso(),
        "subsystem": subsystem,
        "event_type": event_type,
        "severity": severity,
        "architect_id": architect_id,
        "station_id": station_id,
        "request_id": request_id,
        "session_id": session_id,
        "governance_state": _merge_defaults(
            governance_state, DEFAULT_GOVERNANCE_STATE
        ),
        "safety_status": _merge_defaults(safety_status, DEFAULT_SAFETY_STATUS),
        "payload": payload,
        "reflection": reflection,
        "schema_version": SCHEMA_VERSION,
    }
    _validate_record(record)

    with target.open("a", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False)
        handle.write("\n")


def log_event(
    *,
    event_type: str,
    subsystem: str,
    severity: str,
    payload: Dict[str, Any],
    reflection: Optional[str] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    governance_state: Optional[Dict[str, Any]] = None,
    safety_status: Optional[Dict[str, Any]] = None,
    architect_id: str = "architect-local-001",
    station_id: str = "station-calyx-local-001",
) -> None:
    """Append a record to events.jsonl using the shared CTL envelope."""
    log_telemetry(
        event_type=event_type,
        subsystem=subsystem,
        severity=severity,
        payload=payload,
        reflection=reflection,
        request_id=request_id,
        session_id=session_id,
        governance_state=governance_state,
        safety_status=safety_status,
        architect_id=architect_id,
        station_id=station_id,
        path=BASE_LOG_DIR / "events.jsonl",
    )


def log_drift_signal(
    *,
    event_type: str,
    subsystem: str,
    severity: str,
    payload: Dict[str, Any],
    reflection: Optional[str] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    governance_state: Optional[Dict[str, Any]] = None,
    safety_status: Optional[Dict[str, Any]] = None,
    architect_id: str = "architect-local-001",
    station_id: str = "station-calyx-local-001",
) -> None:
    """Append a record to drift_signals.jsonl using the shared CTL envelope."""
    log_telemetry(
        event_type=event_type,
        subsystem=subsystem,
        severity=severity,
        payload=payload,
        reflection=reflection,
        request_id=request_id,
        session_id=session_id,
        governance_state=governance_state,
        safety_status=safety_status,
        architect_id=architect_id,
        station_id=station_id,
        path=BASE_LOG_DIR / "drift_signals.jsonl",
    )


def log_kernel_checkin(
    *,
    subsystem: str,
    severity: str,
    payload: Dict[str, Any],
    reflection: Optional[str] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    governance_state: Optional[Dict[str, Any]] = None,
    safety_status: Optional[Dict[str, Any]] = None,
    architect_id: str = "architect-local-001",
    station_id: str = "station-calyx-local-001",
) -> None:
    """Append a kernel_checkin record to kernel_checkins.jsonl."""
    log_telemetry(
        event_type="kernel_checkin",
        subsystem=subsystem,
        severity=severity,
        payload=payload,
        reflection=reflection,
        request_id=request_id,
        session_id=session_id,
        governance_state=governance_state,
        safety_status=safety_status,
        architect_id=architect_id,
        station_id=station_id,
        path=BASE_LOG_DIR / "kernel_checkins.jsonl",
    )


def log_node_output(
    *,
    subsystem: str,
    severity: str,
    payload: Dict[str, Any],
    reflection: Optional[str] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    governance_state: Optional[Dict[str, Any]] = None,
    safety_status: Optional[Dict[str, Any]] = None,
    architect_id: str = "architect-local-001",
    station_id: str = "station-calyx-local-001",
) -> None:
    """Append a node output record to node_outputs.jsonl."""
    log_telemetry(
        event_type="node_output",
        subsystem=subsystem,
        severity=severity,
        payload=payload,
        reflection=reflection,
        request_id=request_id,
        session_id=session_id,
        governance_state=governance_state,
        safety_status=safety_status,
        architect_id=architect_id,
        station_id=station_id,
        path=BASE_LOG_DIR / "node_outputs.jsonl",
    )


def snapshot_log_sizes(
    snapshot_path: Union[str, Path] = BASE_LOG_DIR / "meta.json",
    log_files: Optional[Dict[str, Path]] = None,
) -> Dict[str, int]:
    """Persist a snapshot of log file sizes for later integrity checks."""
    targets = log_files or STREAM_PATHS
    current_sizes: Dict[str, int] = {}
    for name, path in targets.items():
        file_path = Path(path)
        current_sizes[name] = file_path.stat().st_size if file_path.exists() else 0

    snapshot = Path(snapshot_path)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    with snapshot.open("w", encoding="utf-8") as handle:
        json.dump(current_sizes, handle, ensure_ascii=False, indent=2, sort_keys=True)
    return current_sizes


def check_log_integrity(
    snapshot_path: Union[str, Path] = BASE_LOG_DIR / "meta.json",
    log_files: Optional[Dict[str, Path]] = None,
    *,
    subsystem: str = "CBO",
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Dict[str, int]]:
    """Detect shrinking log files and emit drift signals; does not auto-enforce."""
    targets = log_files or STREAM_PATHS
    snapshot = Path(snapshot_path)
    previous_sizes: Dict[str, int] = {}
    if snapshot.exists():
        with snapshot.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
            if isinstance(loaded, dict):
                previous_sizes = {k: int(v) for k, v in loaded.items()}

    current_sizes: Dict[str, int] = {}
    breaches = []
    for name, path in targets.items():
        file_path = Path(path)
        size_now = file_path.stat().st_size if file_path.exists() else 0
        size_before = previous_sizes.get(name, 0)
        current_sizes[name] = size_now

        if size_now < size_before:
            breaches.append(
                {
                    "name": name,
                    "path": str(file_path),
                    "old_size": size_before,
                    "new_size": size_now,
                }
            )
            log_drift_signal(
                event_type="log_integrity_breach",
                subsystem=subsystem,
                severity="warning",
                payload={
                    "file": str(file_path),
                    "old_size": size_before,
                    "new_size": size_now,
                },
                request_id=request_id,
                session_id=session_id,
            )

    snapshot_log_sizes(snapshot, targets)
    return {"current_sizes": current_sizes, "breaches": breaches}
