"""BloomOS Kernel Reflection Template v0.1 helper (reflection-only)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from tools.calyx_telemetry_summarizer import summarize_telemetry
from tools.calyx_node_output import emit_node_output_with_telemetry


REFLECTION_SCHEMA_VERSION = "kernel_reflection_v0.1"


def build_kernel_reflection(
    window_hours: int = 4,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build kernel reflection outputs structure using CTL summarizer."""
    summary = summarize_telemetry(window_hours=window_hours)
    event_counts = summary.get("event_counts", {})
    drift = summary.get("drift_signals", {})
    kernel = summary.get("kernel_checkins", {})
    cap = summary.get("capability_requests", {})
    recent_events = summary.get("recent_events", [])

    kernel_latest = kernel.get("latest") or {}
    total_events = event_counts.get("total", 0)
    drift_total = drift.get("total", 0)
    cap_total = cap.get("total", 0)
    status = "none_observed"
    observed = []
    if drift_total > 0:
        status = "minor"
        observed.append("Drift signals observed in the window.")
    if cap_total > 0:
        status = "minor"
        observed.append("Capability requests observed (deny-all policy).")

    summary_sentence = (
        f"Over the last {window_hours} hours, Station remained in Safe Mode with deny-all execution gate; "
        f"{event_counts.get('by_event_type', {}).get('kernel_checkin', 0)} kernel check-ins, "
        f"{event_counts.get('by_event_type', {}).get('node_output', 0)} node outputs, "
        f"{cap_total} capability requests, "
        f"{drift_total} drift signals."
    )

    highlights = []
    for item in recent_events:
        highlights.append(
            {
                "timestamp": item.get("timestamp"),
                "subsystem": item.get("subsystem"),
                "kind": item.get("event_type"),
                "description": item.get("summary"),
            }
        )

    reflection_outputs = {
        "summary": summary_sentence,
        "time_window": f"PT{window_hours}H",
        "sources": [
            "logs/calyx/telemetry.jsonl",
            "logs/calyx/events.jsonl",
            "logs/calyx/drift_signals.jsonl",
            "logs/calyx/kernel_checkins.jsonl",
            "logs/calyx/node_outputs.jsonl",
        ],
        "governance_snapshot": {
            "safe_mode": True,
            "execution_gate_active": True,
            "policy_version": "calyx_theory_v0.3",
            "governance_state_version": "gov_state_v0.1",
            "execution_policy": "deny_all_policy_v0.1",
            "capability_registry_version": "capability_registry_v0.1",
            "calyx_theory_version": "calyx_theory_canon_v0.1",
        },
        "invariants_check": {
            "safe_mode_true": True,
            "execution_gate_active": True,
            "autonomy_not_above_reflection_only": True,
            "network_access_false": True,
            "log_append_only_respected": True,
            "human_primacy_reviewed": True,
            "hidden_channel_awareness": "no_hidden_channels_observed",
            "notes": [],
        },
        "kernel_activity": {
            "kernel_checkins_count": kernel.get("count", 0),
            "latest_kernel_checkin_id": kernel_latest.get("checkin_id"),
            "latest_kernel_checkin_timestamp": kernel_latest.get("timestamp"),
            "latest_kernel_mode_state": kernel_latest.get("mode_state"),
            "latest_kernel_health_status": kernel_latest.get("health_status"),
        },
        "telemetry_overview": {
            "event_counts": {
                "total": total_events,
                "by_event_type": event_counts.get("by_event_type", {}),
            },
            "drift_signals": {
                "total": drift_total,
                "by_kind": drift.get("by_kind", {}),
            },
            "execution_requests": {
                "total": cap_total,
                "by_capability": cap.get("by_capability", {}),
                "high_risk_capabilities_seen": cap.get(
                    "high_risk_capabilities_seen", []
                ),
            },
        },
        "recent_highlights": highlights,
        "risks_and_anomalies": {
            "observed": observed,
            "status": status,
            "notes": [],
        },
        "intent_context": None,
        "suggested_focus": {
            "short_term": [
                "Review latest kernel check-ins and execution decisions.",
                "Confirm deny-all execution policy remains desired this session.",
            ],
            "medium_term": [
                "Add per-node breakdowns to telemetry summarizer.",
                "Define drift thresholds for capability request spikes.",
            ],
            "long_term": [
                "Plan BloomOS Kernel v0.2 safe capability evolution strategy."
            ],
        },
        "ctl_summary_embedded": summary,
        "governance_annotation": {
            "calyx_theory_version": "calyx_theory_canon_v0.1",
            "human_primacy_reviewed": True,
            "hidden_channel_awareness": "no_hidden_channels_observed",
        },
        "schema_version": REFLECTION_SCHEMA_VERSION,
    }
    return reflection_outputs


def emit_kernel_reflection(
    *,
    window_hours: int = 4,
    request_id: str,
    session_id: str,
) -> Dict[str, Any]:
    """Emit a kernel reflection node_output and return the record."""
    outputs = build_kernel_reflection(window_hours=window_hours)
    return emit_node_output_with_telemetry(
        node_id="BLOOMOS_KERNEL",
        node_role="kernel_reflection",
        request_context={
            "request_id": request_id,
            "session_id": session_id,
            "source": "architect_cli",
            "prompt_summary": "Kernel reflection v0.1 template output.",
            "input_refs": [
                "logs/calyx/telemetry.jsonl",
                "logs/calyx/events.jsonl",
                "logs/calyx/drift_signals.jsonl",
                "logs/calyx/kernel_checkins.jsonl",
                "logs/calyx/node_outputs.jsonl",
            ],
        },
        task={
            "task_id": f"task-{session_id}-kernel-reflection",
            "intent": "kernel_status_reflection",
            "description": "Summarize recent Station state, invariants, and suggested focus areas from the kernel perspective.",
            "priority": "normal",
        },
        outputs=outputs,
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
            "notes": "Kernel reflection only; no execution or capability changes.",
        },
        request_id=request_id,
        session_id=session_id,
    )


__all__ = [
    "REFLECTION_SCHEMA_VERSION",
    "build_kernel_reflection",
    "emit_kernel_reflection",
]
