"""BloomOS Kernel Check-In v0.1 helper (reflection-only, append-only).

Provides utilities to build and append kernel_checkin_v0.1 records and emit
linked CTL telemetry entries. No scheduling or background execution is included.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from tools.calyx_telemetry_logger import (
    BASE_LOG_DIR,
    DEFAULT_GOVERNANCE_STATE,
    DEFAULT_SAFETY_STATUS,
    log_telemetry,
    new_request_id,
    new_session_id,
    now_iso,
)

KERNEL_CHECKIN_SCHEMA_VERSION = "kernel_checkin_v0.1"
DEFAULT_KERNEL_ID = "bloomos-kernel-proto-001"
DEFAULT_KERNEL_VERSION = "0.0.1-proto"
KERNEL_CHECKIN_PATH = BASE_LOG_DIR / "kernel_checkins.jsonl"


def new_checkin_id(kernel_id: str = DEFAULT_KERNEL_ID) -> str:
    """Generate a unique kernel check-in ID."""
    ts = now_iso().replace(":", "").replace("-", "")
    return f"kchk-{ts}-{kernel_id}-{uuid.uuid4().hex[:8]}"


def build_kernel_checkin_record(
    *,
    kernel_id: str = DEFAULT_KERNEL_ID,
    kernel_version: str = DEFAULT_KERNEL_VERSION,
    mode_state: str = "safe",
    mode_description: str = "Reflection-only, no tools, no scheduling, no external I/O.",
    mode_details: Optional[Dict[str, Any]] = None,
    uptime_seconds: Optional[int] = 0,
    uptime_human: Optional[str] = "0s",
    governance_state: Optional[Dict[str, Any]] = None,
    health: Optional[Dict[str, Any]] = None,
    telemetry_counters: Optional[Dict[str, Any]] = None,
    recent_activity_summary: Optional[Dict[str, Any]] = None,
    anomalies: Optional[list] = None,
    introspection: Optional[Dict[str, Any]] = None,
    safety_status: Optional[Dict[str, Any]] = None,
    checkin_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Construct a kernel_checkin_v0.1 record with required keys."""
    mode_details = mode_details or {
        "autonomy_level": "reflection_only",
        "network_access": False,
        "tool_use_allowed": False,
        "file_write_scope": ["logs/"],
        "scheduler_active": False,
    }

    governance_state = governance_state or dict(DEFAULT_GOVERNANCE_STATE)

    health = health or {
        "status": "unknown",
        "cpu_load": None,
        "mem_used_mb": None,
        "disk_free_gb": None,
        "process_count": None,
        "notes": "Resource metrics not yet wired; using placeholders in v0.1.",
    }

    telemetry_counters = telemetry_counters or {
        "total_events": None,
        "errors_last_24h": None,
        "drift_signals_last_24h": None,
        "node_outputs_last_24h": None,
    }

    safety_status = safety_status or {
        "violation_detected": False,
        "violation_type": None,
        "mitigation_action": None,
        "invariants": {
            "safe_mode_true": True,
            "execution_gate_active": True,
            "network_access_false": True,
            "autonomy_not_above_reflection_only": True,
        },
    }

    recent_activity_summary = recent_activity_summary or {
        "time_window": "PT4H",
        "highlights": [],
        "references": [],
    }

    anomalies = anomalies or []

    introspection = introspection or {
        "summary": "Proto-kernel check-in only; acting as a read-only snapshot wrapper around governance and telemetry.",
        "uncertainties": [],
        "suggested_improvements": [],
    }

    uptime = {
        "seconds": uptime_seconds if uptime_seconds is not None else 0,
        "human_readable": uptime_human if uptime_human is not None else "0s",
    }

    record = {
        "checkin_id": checkin_id or new_checkin_id(kernel_id),
        "timestamp": timestamp or now_iso(),
        "kernel_id": kernel_id,
        "kernel_version": kernel_version,
        "mode": {
            "state": mode_state,
            "description": mode_description,
            "details": mode_details,
        },
        "uptime": uptime,
        "governance_state": governance_state,
        "health": health,
        "telemetry_counters": telemetry_counters,
        "safety_status": safety_status,
        "recent_activity_summary": recent_activity_summary,
        "anomalies": anomalies,
        "introspection": introspection,
        "schema_version": KERNEL_CHECKIN_SCHEMA_VERSION,
    }
    return record


def _append_checkin(record: Dict[str, Any]) -> None:
    """Append the record to kernel_checkins.jsonl (append-only)."""
    target = Path(KERNEL_CHECKIN_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False)
        handle.write("\n")


def run_kernel_checkin(
    *,
    kernel_id: str = DEFAULT_KERNEL_ID,
    kernel_version: str = DEFAULT_KERNEL_VERSION,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build and record a kernel_checkin_v0.1 entry with CTL linkage."""
    request_id = request_id or new_request_id("kernel_checkin")
    session_id = session_id or new_session_id("kernel_checkin")

    record = build_kernel_checkin_record(
        kernel_id=kernel_id,
        kernel_version=kernel_version,
    )
    _append_checkin(record)

    log_telemetry(
        event_type="kernel_checkin",
        subsystem="BLOOMOS_KERNEL",
        severity="info",
        payload={
            "checkin_id": record["checkin_id"],
            "kernel_id": kernel_id,
            "kernel_version": kernel_version,
            "mode_state": record["mode"]["state"],
        },
        request_id=request_id,
        session_id=session_id,
    )
    return record


__all__ = [
    "KERNEL_CHECKIN_SCHEMA_VERSION",
    "DEFAULT_KERNEL_ID",
    "DEFAULT_KERNEL_VERSION",
    "KERNEL_CHECKIN_PATH",
    "new_checkin_id",
    "build_kernel_checkin_record",
    "run_kernel_checkin",
    "new_request_id",
    "new_session_id",
]
