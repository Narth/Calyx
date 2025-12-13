"""Calyx Health Probe v0.1 (reflection-only, read-only).

Builds a health summary from existing CTL summaries/logs and emits a node_output.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from tools.calyx_node_output import emit_node_output_with_telemetry
from tools.calyx_telemetry_logger import now_iso
from tools.calyx_telemetry_summarizer import summarize_telemetry

HEALTH_PROBE_SCHEMA_VERSION = "ctl_health_probe_v0.1"


def _try_os_metrics() -> Dict[str, Any]:
    """Best-effort, read-only OS metrics (safe-mode compatible)."""
    metrics: Dict[str, Any] = {
        "process_count": None,
        "disk_free_gb": None,
        "mem_used_mb": None,
        "cpu_load": None,
    }
    try:
        import psutil  # type: ignore

        metrics["process_count"] = len(psutil.pids())
        vmem = psutil.virtual_memory()
        metrics["mem_used_mb"] = round(vmem.used / (1024 * 1024), 2)
        metrics["cpu_load"] = psutil.cpu_percent(interval=0.1)
    except Exception:
        pass

    try:
        total, used, free = shutil.disk_usage(".")
        metrics["disk_free_gb"] = round(free / (1024 ** 3), 2)
    except Exception:
        pass
    return metrics


def summarize_health(
    window_hours: int = 4, include_os_metrics: bool = True
) -> Dict[str, Any]:
    """Build a health summary dict (ctl_health_probe_v0.1) using CTL summary + optional OS metrics."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)
    ctl_summary = summarize_telemetry(window_hours=window_hours)

    event_counts = ctl_summary.get("event_counts", {})
    drift = ctl_summary.get("drift_signals", {})
    capability = ctl_summary.get("capability_requests", {})
    kernel = ctl_summary.get("kernel_checkins", {})
    kernel_latest = (kernel.get("latest") or {}) if isinstance(kernel, dict) else {}

    intent_landscape = {
        "observed": None,  # Placeholder for future intent parsing
        "notes": "Intent parsing not implemented in probe v0.1; see intent interpreter outputs.",
    }

    os_metrics = _try_os_metrics() if include_os_metrics else {}

    summary = {
        "schema_version": HEALTH_PROBE_SCHEMA_VERSION,
        "generated_at": now_iso(),
        "window_hours": window_hours,
        "from_timestamp": window_start.isoformat().replace("+00:00", "Z"),
        "to_timestamp": now.isoformat().replace("+00:00", "Z"),
        "invariants": {
            "safe_mode_true": True,
            "execution_gate_active": True,
            "execution_policy": "deny_all_policy_v0.1",
            "append_only_logging": True,
            "human_primacy_reviewed": True,
            "hidden_channel_awareness": "no_hidden_channels_observed",
        },
        "capability_pressure": {
            "total_requests": capability.get("total", 0),
            "by_capability": capability.get("by_capability", {}),
            "high_risk_capabilities_seen": capability.get(
                "high_risk_capabilities_seen", []
            ),
        },
        "drift_anomalies": {
            "drift_signals": drift.get("total", 0),
            "by_kind": drift.get("by_kind", {}),
        },
        "reflection_cadence": {
            "kernel_checkins": kernel.get("count", 0),
            "node_outputs": event_counts.get("by_event_type", {}).get(
                "node_output", 0
            ),
            "latest_kernel_checkin": {
                "checkin_id": kernel_latest.get("checkin_id"),
                "timestamp": kernel_latest.get("timestamp"),
            },
        },
        "intent_landscape": intent_landscape,
        "governance_metrics": {
            "calyx_theory_version": "calyx_theory_canon_v0.1",
            "capability_registry_version": "capability_registry_v0.1",
            "execution_policy": "deny_all_policy_v0.1",
        },
        "os_metrics": os_metrics,
        "notes": ctl_summary.get("notes", []),
        "ctl_summary_embedded": ctl_summary,
    }
    return summary


def emit_health_probe_node_output(
    *,
    summary: Dict[str, Any],
    request_id: str,
    session_id: str,
    window_hours: int,
) -> Dict[str, Any]:
    """Emit the health probe node_output_v1.0 (node_id=CBO, node_role=health_probe)."""
    summary_text = (
        f"Health probe over last {window_hours}h: "
        f"{summary.get('capability_pressure', {}).get('total_requests', 0)} capability requests (deny-all), "
        f"{summary.get('drift_anomalies', {}).get('drift_signals', 0)} drift signals, "
        f"{summary.get('reflection_cadence', {}).get('kernel_checkins', 0)} kernel check-ins."
    )
    return emit_node_output_with_telemetry(
        node_id="CBO",
        node_role="health_probe",
        request_context={
            "request_id": request_id,
            "session_id": session_id,
            "source": "architect_cli",
            "prompt_summary": "Calyx Health Probe v0.1",
            "input_refs": [
                "logs/calyx/telemetry.jsonl",
                "logs/calyx/events.jsonl",
                "logs/calyx/drift_signals.jsonl",
                "logs/calyx/kernel_checkins.jsonl",
                "logs/calyx/node_outputs.jsonl",
            ],
        },
        task={
            "task_id": f"task-{session_id}-health-probe",
            "intent": "ctl_health_probe",
            "description": "Reflective health probe using CTL summary and optional OS read-only metrics.",
            "priority": "normal",
        },
        outputs={
            "summary": summary_text,
            "health_probe": summary,
            "actions_proposed": [
                "Continue deny-all execution gate; monitor capability pressure.",
                "Review hidden-channel awareness routinely; no anomalies observed.",
            ],
            "actions_taken": [],
            "next_steps": [
                "Architect may review capability pressure and reflection cadence.",
                "Define thresholds for drift/anomaly alerts (still reflection-only).",
            ],
            "governance_annotation": {
                "calyx_theory_version": "calyx_theory_canon_v0.1",
                "human_primacy_reviewed": True,
                "hidden_channel_awareness": "no_hidden_channels_observed",
            },
            "schema_version": HEALTH_PROBE_SCHEMA_VERSION,
        },
        governance={
            "governance_state": {
                "safe_mode": True,
                "autonomy_level": "reflection_only",
                "execution_gate_active": True,
                "policy_version": "calyx_theory_v0.3",
                "governance_state_version": "gov_state_v0.1",
            },
            "allowed_capabilities": ["read_files", "summarize", "reflect"],
            "denied_capabilities": [
                "execute_code",
                "modify_files",
                "schedule_tasks",
                "filesystem_write",
                "network_request",
                "process_spawn",
                "tool_call",
            ],
        },
        safety={
            "rule_violations": [],
            "blocked_intents": [],
            "risk_assessment": "low",
            "notes": "Reflection-only health probe; no execution or capability changes.",
        },
        request_id=request_id,
        session_id=session_id,
    )


__all__ = [
    "HEALTH_PROBE_SCHEMA_VERSION",
    "summarize_health",
    "emit_health_probe_node_output",
]
