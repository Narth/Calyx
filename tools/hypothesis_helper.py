"""Helpers to emit hypothesis-oriented node outputs (reflection-only).

These are read-only, human-invoked utilities to capture hypotheses,
evidence, and proposed test plans as node_output_v1.0 records. They do not
execute actions or request capabilities; all activity stays within Safe Mode
and deny-all governance.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from tools.calyx_node_output import emit_node_output_with_telemetry
from tools.calyx_telemetry_logger import new_request_id, new_session_id


def emit_hypothesis_node_output(
    *,
    hypothesis: str,
    evidence: Optional[List[str]] = None,
    proposed_tests: Optional[List[str]] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    source: str = "architect_cli",
    scope: str = "station_health",
) -> Dict[str, Any]:
    """Record a hypothesis node output (reflection-only)."""
    req_id = request_id or new_request_id("hypothesis")
    sess_id = session_id or new_session_id("work_session")

    outputs = {
        "summary": f"Hypothesis captured for scope '{scope}': {hypothesis}",
        "actions_proposed": proposed_tests or [],
        "actions_taken": [],
        "next_steps": proposed_tests or [],
        "hypothesis": {
            "text": hypothesis,
            "evidence": evidence or [],
            "proposed_tests": proposed_tests or [],
            "schema_version": "hypothesis_v0.1",
        },
    }

    return emit_node_output_with_telemetry(
        node_id="CBO",
        node_role="hypothesis_recorder",
        request_context={
            "request_id": req_id,
            "session_id": sess_id,
            "source": source,
        },
        task={
            "task_id": f"hypothesis-{scope}",
            "intent": "hypothesis_record",
            "description": "Capture a hypothesis, evidence, and proposed tests (reflection-only).",
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
            "notes": "Reflection-only hypothesis capture; no execution or capability changes.",
        },
        request_id=req_id,
        session_id=sess_id,
    )


__all__ = ["emit_hypothesis_node_output"]
