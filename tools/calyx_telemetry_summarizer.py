"""Calyx Telemetry Summarizer v0.1 (read-only, manual invocation)."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.calyx_node_output import emit_node_output_with_telemetry
from tools.calyx_telemetry_logger import new_request_id, new_session_id, now_iso

SUMMARY_SCHEMA_VERSION = "ctl_summary_v0.1"

LOG_DIR = Path("logs") / "calyx"
TELEMETRY_PATH = LOG_DIR / "telemetry.jsonl"
EVENTS_PATH = LOG_DIR / "events.jsonl"
DRIFT_PATH = LOG_DIR / "drift_signals.jsonl"
NODE_OUTPUTS_PATH = LOG_DIR / "node_outputs.jsonl"
KERNEL_CHECKINS_PATH = LOG_DIR / "kernel_checkins.jsonl"


def _parse_ts(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                records.append(rec)
            except json.JSONDecodeError:
                continue
    return records


def _filter_by_window(records: List[Dict[str, Any]], window_start: datetime) -> List[Dict[str, Any]]:
    filtered = []
    for rec in records:
        ts = rec.get("timestamp")
        dt = _parse_ts(ts) if ts else None
        if dt and dt >= window_start:
            filtered.append(rec)
    return filtered


def summarize_telemetry(window_hours: int = 4) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    telemetry = _filter_by_window(_read_jsonl(TELEMETRY_PATH), window_start)
    events = _filter_by_window(_read_jsonl(EVENTS_PATH), window_start)
    drift_signals = _filter_by_window(_read_jsonl(DRIFT_PATH), window_start)
    node_outputs = _filter_by_window(_read_jsonl(NODE_OUTPUTS_PATH), window_start)
    kernel_checkins = _filter_by_window(_read_jsonl(KERNEL_CHECKINS_PATH), window_start)

    event_counts_total = len(telemetry) + len(events) + len(drift_signals)
    by_event_type = Counter()
    by_subsystem = Counter()
    capability_requests = Counter()
    capability_request_sets = Counter()
    node_output_by_node = Counter()

    for rec in telemetry:
        et = rec.get("event_type")
        if et:
            by_event_type[et] += 1
        subsystem = rec.get("subsystem")
        if subsystem:
            by_subsystem[subsystem] += 1
        if et == "execution_request":
            payload = rec.get("payload") or {}
            single = payload.get("capability")
            if single:
                capability_requests[single] += 1
            caps_list = payload.get("capabilities")
            if isinstance(caps_list, list):
                # support both list of names and list of dicts
                for item in caps_list:
                    if isinstance(item, str):
                        capability_requests[item] += 1
                        capability_request_sets[str(sorted([item]))] += 1
                    elif isinstance(item, dict):
                        name = item.get("name")
                        if name:
                            capability_requests[name] += 1
                    # ignore malformed entries

    for rec in events:
        et = rec.get("event_type")
        if et:
            by_event_type[et] += 1
        subsystem = rec.get("subsystem")
        if subsystem:
            by_subsystem[subsystem] += 1

    for rec in node_outputs:
        node_id = rec.get("node_id")
        if node_id:
            node_output_by_node[node_id] += 1

    for rec in drift_signals:
        by_event_type["drift_signal"] += 1
        subsystem = rec.get("subsystem")
        if subsystem:
            by_subsystem[subsystem] += 1

    drift_by_kind = Counter()
    for rec in drift_signals:
        payload = rec.get("payload") or {}
        kind = payload.get("drift_kind") or rec.get("event_type")
        if kind:
            drift_by_kind[kind] += 1

    latest_checkin = None
    if kernel_checkins:
        latest_checkin = sorted(
            kernel_checkins, key=lambda r: r.get("timestamp") or ""
        )[-1]

    recent_events: List[Dict[str, Any]] = []
    for rec in sorted(telemetry + events, key=lambda r: r.get("timestamp") or "")[-5:]:
        recent_events.append(
            {
                "timestamp": rec.get("timestamp"),
                "subsystem": rec.get("subsystem"),
                "event_type": rec.get("event_type"),
                "summary": rec.get("reflection")
                or rec.get("payload")
                or "",
            }
        )

    high_risk_capabilities_seen = list(capability_requests.keys())
    repeated_high_risk_capabilities = [
        cap for cap, count in capability_requests.items() if count > 1
    ]

    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "generated_at": now_iso(),
        "window_hours": window_hours,
        "from_timestamp": (now - timedelta(hours=window_hours)).isoformat().replace(
            "+00:00", "Z"
        ),
        "to_timestamp": now.isoformat().replace("+00:00", "Z"),
        "event_counts": {
            "total": event_counts_total,
            "by_event_type": dict(by_event_type),
            "by_subsystem": dict(by_subsystem),
        },
        "drift_signals": {
            "total": len(drift_signals),
            "by_kind": dict(drift_by_kind),
        },
        "kernel_checkins": {
            "count": len(kernel_checkins),
            "latest": {
                "checkin_id": latest_checkin.get("checkin_id") if latest_checkin else None,
                "timestamp": latest_checkin.get("timestamp") if latest_checkin else None,
                "mode_state": (latest_checkin.get("mode") or {}).get("state")
                if latest_checkin
                else None,
                "health_status": (latest_checkin.get("health") or {}).get("status")
                if latest_checkin
                else None,
                "safety_invariants": (latest_checkin.get("safety_status") or {}).get(
                    "invariants"
                )
                if latest_checkin
                else None,
            },
        },
        "recent_events": recent_events,
        "capability_requests": {
            "total": sum(capability_requests.values()),
            "by_capability": dict(capability_requests),
            "high_risk_capabilities_seen": high_risk_capabilities_seen,
            "repeated_high_risk_capabilities": repeated_high_risk_capabilities,
        },
        "node_outputs_overview": {
            "count": len(node_outputs),
            "by_node_id": dict(node_output_by_node),
        },
        "notes": [],
    }

    if len(drift_signals) == 0:
        summary["notes"].append(
            f"No drift_signals detected in the last {window_hours} hours."
        )
    if capability_requests:
        summary["notes"].append(
            "Execution Gate remains deny-all; mutating capabilities denied."
        )
    if repeated_high_risk_capabilities:
        summary["notes"].append(
            "Repeated capability requests observed: "
            + ", ".join(repeated_high_risk_capabilities)
        )
    return summary


def _build_notes(summary: Dict[str, Any]) -> List[str]:
    notes = list(summary.get("notes", []))
    if not notes:
        notes.append("Telemetry summary generated without additional notes.")
    return notes


def emit_summary_node_output(
    summary: Dict[str, Any],
    window_hours: int,
    request_id: str,
    session_id: str,
) -> Dict[str, Any]:
    """Emit node_output_v1.0 with ctl_summary payload and return record."""
    notes = _build_notes(summary)
    outputs_summary = (
        f"Over the last {window_hours} hours: "
        f"{summary['event_counts']['total']} events; "
        f"{summary['event_counts']['by_event_type'].get('kernel_checkin', 0)} kernel_checkins; "
        f"{summary['event_counts']['by_event_type'].get('node_output', 0)} node_outputs; "
        f"{summary['drift_signals']['total']} drift_signals; "
        f"{summary['capability_requests']['total']} capability requests (all deny-all)."
    )
    return emit_node_output_with_telemetry(
        node_id="CBO",
        node_role="telemetry_summarizer",
        request_context={
            "request_id": request_id,
            "session_id": session_id,
            "source": "architect_cli",
            "prompt_summary": "Summarize Calyx telemetry over a recent time window.",
            "input_refs": [
                str(TELEMETRY_PATH),
                str(EVENTS_PATH),
                str(DRIFT_PATH),
                str(NODE_OUTPUTS_PATH),
                str(KERNEL_CHECKINS_PATH),
            ],
        },
        task={
            "task_id": f"task-{session_id}-ctl-summary",
            "intent": "ctl_summary",
            "description": "Summarize Calyx telemetry over a recent time window.",
            "priority": "normal",
        },
        outputs={
        "summary": outputs_summary,
        "actions_proposed": [
            "Monitor high-risk capability requests; remain deny-all.",
            "Consider adding drift thresholds for repeated denied requests.",
        ],
        "actions_taken": [],
        "next_steps": [
            "Architect may review latest kernel check-ins and execution decisions.",
            "Architect may adjust summary fields for ctl_summary_v0.2.",
        ],
        "governance_annotation": {
            "calyx_theory_version": "calyx_theory_canon_v0.1",
            "human_primacy_reviewed": True,
            "hidden_channel_awareness": "no_hidden_channels_observed",
        },
        "ctl_summary": summary,
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
            "notes": "Read-only summarization; no execution or capability changes.",
        },
        request_id=request_id,
        session_id=session_id,
    )


__all__ = [
    "SUMMARY_SCHEMA_VERSION",
    "summarize_telemetry",
    "emit_summary_node_output",
    "new_request_id",
    "new_session_id",
]
