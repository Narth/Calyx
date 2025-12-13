"""Station Routine v0.2 (manual, reflection-only).

Modes:
- basic: v0.1 behavior (integrity check, kernel check-in, session_started, CBO reflection)
- extended: basic + CTL summarizer node_output + kernel reflection node_output + optional intent embedding.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from tools.bloomos_kernel_checkin import run_kernel_checkin
from tools.bloomos_kernel_reflection import emit_kernel_reflection
from tools.calyx_intent_interpreter import interpret_intent
from tools.calyx_node_output import emit_node_output_with_telemetry
from tools.calyx_telemetry_logger import (
    log_event,
    log_telemetry,
    new_request_id,
    new_session_id,
)
from tools.calyx_telemetry_logger import check_log_integrity
from tools.calyx_telemetry_summarizer import (
    emit_summary_node_output,
    summarize_telemetry,
)


def run_station_routine(
    *,
    mode: str = "extended",
    hours: int = 4,
    intent_text: Optional[str] = None,
    run_health_probe: bool = False,
    include_os_metrics: bool = True,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute Station Routine v0.2 (basic or extended) and return key artifacts."""
    mode = mode or "extended"
    session_id = session_id or new_session_id("work_session")
    request_id = request_id or new_request_id("station_routine")

    integrity_result = check_log_integrity(
        request_id=request_id, session_id=session_id
    )
    integrity_check_run = True
    integrity_breaches_detected = bool(integrity_result.get("breaches"))

    checkin_record = run_kernel_checkin(
        request_id=request_id, session_id=session_id
    )
    checkin_id = checkin_record["checkin_id"]

    log_event(
        event_type="session_started",
        subsystem="CBO",
        severity="info",
        payload={
            "routine": "station_routine_v0.2",
            "kernel_checkin_id": checkin_id,
            "integrity_check_run": integrity_check_run,
            "integrity_breaches_detected": integrity_breaches_detected,
            "mode": mode,
            "window_hours": hours,
        },
        request_id=request_id,
        session_id=session_id,
    )

    summary = (
        f"Kernel check-in {checkin_id} completed in safe mode. "
        f"Integrity breaches detected: {integrity_breaches_detected}."
    )

    intent_obj = None
    if intent_text:
        intent_obj = interpret_intent(
            intent_text,
            channel="station_routine",
            session_id=session_id,
            request_id=request_id,
            actor="architect",
        )

    overseer_outputs = {
        "summary": summary,
        "actions_proposed": [],
        "actions_taken": [],
        "next_steps": [
            "Review latest kernel check-in for any anomalies.",
            "Survey drift_signals.jsonl for integrity breaches.",
            "Set session goals and directives for the work window.",
        ],
        "governance_annotation": {
            "calyx_theory_version": "calyx_theory_canon_v0.1",
            "human_primacy_reviewed": True,
            "hidden_channel_awareness": "no_hidden_channels_observed",
        },
        "human_primacy_note": "Human oversight required for any action; reflection-only session framing.",
    }
    if intent_obj:
        overseer_outputs["intent"] = intent_obj

    node_output = emit_node_output_with_telemetry(
        node_id="CBO",
        node_role="overseer_reflection",
        request_context={
            "request_id": request_id,
            "session_id": session_id,
            "source": "station_routine",
            "prompt_summary": "Station Routine v0.2 session initialization reflection.",
            "input_refs": [
                "logs/calyx/kernel_checkins.jsonl",
                "logs/calyx/telemetry.jsonl",
            ],
        },
        task={
            "task_id": f"task-{session_id}-station-routine",
            "intent": "session_initialization_reflection",
            "description": "Provide a snapshot of Station state at the start of this work session and suggest next steps.",
            "priority": "normal",
        },
        outputs=overseer_outputs,
        governance=None,
        safety={
            "rule_violations": [],
            "blocked_intents": [],
            "risk_assessment": "low",
            "notes": "Routine confined to reflection-only logging; no execution or scheduling.",
        },
        request_id=request_id,
        session_id=session_id,
    )

    result: Dict[str, Any] = {
        "session_id": session_id,
        "request_id": request_id,
        "integrity_check_run": integrity_check_run,
        "integrity_breaches_detected": integrity_breaches_detected,
        "checkin_id": checkin_id,
        "node_output": node_output,
        "intent": intent_obj,
    }

    if mode == "extended":
        summary_dict = summarize_telemetry(window_hours=hours)
        summary_node_output = emit_summary_node_output(
            summary=summary_dict,
            window_hours=hours,
            request_id=request_id,
            session_id=session_id,
        )
        kernel_reflection = emit_kernel_reflection(
            window_hours=hours,
            request_id=request_id,
            session_id=session_id,
        )
        governance_metrics = {
            "calyx_theory_version": "calyx_theory_canon_v0.1",
            "safe_mode": True,
            "execution_gate_active": True,
            "execution_policy": "deny_all_policy_v0.1",
            "capability_registry_version": "capability_registry_v0.1",
            "event_counts_total": summary_dict.get("event_counts", {}).get("total", 0),
            "drift_signals": summary_dict.get("drift_signals", {}).get("total", 0),
            "capability_requests": summary_dict.get("capability_requests", {}).get(
                "total", 0
            ),
        }
        result.update(
            {
                "summary": summary_dict,
                "summary_node_output": summary_node_output,
                "kernel_reflection": kernel_reflection,
                "governance_metrics": governance_metrics,
            }
        )
        if run_health_probe:
            from tools.health_probe import (
                emit_health_probe_node_output,
                summarize_health,
            )

            health_summary = summarize_health(
                window_hours=hours, include_os_metrics=include_os_metrics
            )
            health_probe = emit_health_probe_node_output(
                summary=health_summary,
                request_id=request_id,
                session_id=session_id,
                window_hours=hours,
            )
            result["health_probe"] = health_probe

    return result


__all__ = ["run_station_routine"]
