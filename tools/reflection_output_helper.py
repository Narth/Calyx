"""Helper to emit reflections that comply with Reflection Expectation Schema v0.1."""

from __future__ import annotations

from typing import Any, Dict, Optional

from tools.calyx_node_output import emit_node_output_with_telemetry
from tools.calyx_telemetry_logger import new_request_id, new_session_id


def emit_reflection_node_output(
    *,
    reflection_type: str,
    summary: str,
    analysis: Dict[str, Any],
    advisories: Optional[list] = None,
    drift_signals: Optional[list] = None,
    human_primacy_respected: bool = True,
    input_reference: Optional[str] = None,
    proposed_actions: Optional[Any] = None,
    node_id: str = "CBO",
    node_role: str = "governance_interpreter",
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    source: str = "governance_reflection",
) -> Dict[str, Any]:
    req_id = request_id or new_request_id("reflection")
    sess_id = session_id or new_session_id("work_session")
    outputs = {
        "reflection_type": reflection_type,
        "input_reference": input_reference,
        "safe_mode": True,
        "execution_gate_state": "deny_all",
        "summary": summary,
        "analysis": analysis,
        "advisories": advisories or [],
        "drift_signals": drift_signals or [],
        "proposed_actions": proposed_actions,
        "human_primacy_respected": human_primacy_respected,
        "schema_version": "reflection_v0.1",
    }
    return emit_node_output_with_telemetry(
        node_id=node_id,
        node_role=node_role,
        request_context={
            "request_id": req_id,
            "session_id": sess_id,
            "source": source,
            "input_reference": input_reference,
        },
        task={
            "task_id": f"reflection-{reflection_type}-{sess_id}",
            "intent": "reflection_output",
            "description": "Emit reflection in compliance with RES v0.1.",
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
            "notes": "Reflection-only; no capability changes.",
        },
        request_id=req_id,
        session_id=sess_id,
    )


__all__ = ["emit_reflection_node_output"]
