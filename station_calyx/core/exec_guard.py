"""Execution guard invoked by services to enforce ExecutionPolicy and record evidence.

Services must call exec_guard(intent_id, requested_capability, caller_identity, channel, risk)
before attempting any execution. The guard returns True if allowed, False if denied.
If REQ_APPROVAL is returned, the service must surface it to operator.
"""
from __future__ import annotations
from typing import Dict, Any
from .execution_policy import decide
from .system_mode import check_execution_allowed


def exec_guard(intent_id: str, requested_capability: str, caller_identity: Dict[str, Any], channel: str, risk: str = "LOW") -> Dict[str, Any]:
    # Check emergency deny
    if check_execution_allowed:
        try:
            # DECISION
            decision = decide(intent_id, requested_capability, caller_identity, channel, risk)
            return decision
        except Exception:
            return {"decision": "DENY", "rationale": "policy_error"}
    else:
        return {"decision": "DENY", "rationale": "execution_blocked_global"}
