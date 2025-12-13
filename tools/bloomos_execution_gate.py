"""BloomOS Execution Gate v0.1 (deny-all, reflective, logging-only).

Provides a single path for Action Requests. In v0.1, all requests are denied
under policy `deny_all_policy_v0.1`; no real actions are executed.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import uuid
from pathlib import Path

from tools.calyx_telemetry_logger import (
    DEFAULT_GOVERNANCE_STATE,
    DEFAULT_SAFETY_STATUS,
    log_telemetry,
    now_iso,
)
from tools.bloomos_capability_registry import annotate_action_request
from tools.refusal_snippets import standard_refusal

CAPABILITIES = {
    "filesystem_write",
    "filesystem_read_logs",
    "filesystem_read_sensitive",
    "network_request",
    "process_spawn",
    "hardware_io",
    "tool_call",
}
ALLOW_TEST_CAPABILITIES = {"filesystem_read_logs"}
ALLOW_SUMMARY = "filesystem_write_summary_v0.1"
ALLOW_CACHE = "filesystem_write_cache_v0.1"
ALLOW_DRIFT_EVIDENCE = "filesystem_write_drift_evidence_v0.1"

EXECUTION_GATE_DECISION_SCHEMA = "execution_gate_decision_v0.1"
POLICY_DENY_ALL = "deny_all_policy_v0.1"
POLICY_ALLOW_TEST_FS_READ_LOGS = "allow_test_filesystem_read_logs_v0.1"
POLICY_ALLOW_SUMMARY_WRITES = "allow_append_only_summaries_v0.1"
POLICY_ALLOW_CACHE_WRITES = "allow_cache_writes_v0.1"
POLICY_ALLOW_DRIFT_EVIDENCE = "allow_drift_evidence_v0.1"


def new_decision_id(source: str = "execution_gate") -> str:
    """Generate a unique decision_id."""
    ts = now_iso().replace(":", "").replace("-", "")
    return f"egdec-{ts}-{source}-{uuid.uuid4().hex[:8]}"


def build_action_request(
    *,
    request_id: str,
    session_id: str,
    node_id: str,
    node_role: str,
    capability: str,
    action: str,
    target: Dict[str, Any],
    parameters: Optional[Dict[str, Any]] = None,
    intent: Optional[str] = None,
    justification: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Construct a well-shaped Action Request object."""
    return {
        "request_id": request_id,
        "session_id": session_id,
        "node_id": node_id,
        "node_role": node_role,
        "capability": capability,
        "action": action,
        "target": target,
        "parameters": parameters or {},
        "intent": intent,
        "justification": justification,
        "timestamp": timestamp or now_iso(),
    }


def _validate_action_request(action_request: Dict[str, Any]) -> None:
    """Basic validation of action request shape and capability."""
    required_keys = [
        "request_id",
        "session_id",
        "node_id",
        "node_role",
        "capability",
        "action",
        "target",
        "timestamp",
    ]
    for key in required_keys:
        if key not in action_request:
            raise ValueError(f"action_request missing required field: {key}")
    capability = action_request.get("capability")
    if capability not in CAPABILITIES:
        raise ValueError(f"Unsupported capability: {capability}")


def _is_allowed_test(action_request: Dict[str, Any]) -> bool:
    """Check if this request meets the scoped test allow criteria (reflection-only)."""
    if not action_request.get("allow_test"):
        return False
    capability = action_request.get("capability")
    if capability not in ALLOW_TEST_CAPABILITIES:
        return False
    target = action_request.get("target") or {}
    path = target.get("path") or ""
    if not isinstance(path, str):
        return False
    if not path.startswith("logs/calyx/"):
        return False
    action = action_request.get("action")
    if action not in ("read_file", "read_logs"):
        return False
    return True


def _is_allowed_summary_write(action_request: Dict[str, Any]) -> bool:
    if not action_request.get("allow_summary"):
        return False
    capability = action_request.get("capability")
    if capability != "filesystem_write":
        return False
    target = action_request.get("target") or {}
    path = target.get("path") or ""
    if not isinstance(path, str):
        return False
    path_norm = str(Path(path).as_posix())
    if not path_norm.startswith("outgoing/CBO/summaries/"):
        return False
    action = action_request.get("action")
    if action not in ("write_file", "append_file"):
        return False
    data_size = (action_request.get("parameters") or {}).get("data_size_bytes")
    return data_size is None or data_size <= 1_000_000  # 1MB safety cap


def _is_allowed_cache_write(action_request: Dict[str, Any]) -> bool:
    if not action_request.get("allow_cache"):
        return False
    capability = action_request.get("capability")
    if capability != "filesystem_write":
        return False
    target = action_request.get("target") or {}
    path = target.get("path") or ""
    if not isinstance(path, str):
        return False
    path_norm = str(Path(path).as_posix())
    if not path_norm.startswith("logs/calyx/cache/"):
        return False
    action = action_request.get("action")
    if action not in ("write_file", "replace_file"):
        return False
    data_size = (action_request.get("parameters") or {}).get("data_size_bytes")
    return data_size is None or data_size <= 1_000_000  # 1MB per file cap


def _is_allowed_drift_evidence(action_request: Dict[str, Any]) -> bool:
    if not action_request.get("allow_drift_evidence"):
        return False
    capability = action_request.get("capability")
    if capability != "filesystem_write":
        return False
    target = action_request.get("target") or {}
    path = target.get("path") or ""
    if not isinstance(path, str):
        return False
    path_norm = str(Path(path).as_posix())
    if not path_norm.startswith("logs/calyx/drift_evidence/"):
        return False
    action = action_request.get("action")
    if action not in ("write_file", "append_file"):
        return False
    data_size = (action_request.get("parameters") or {}).get("data_size_bytes")
    return data_size is None or data_size <= 64_000  # 64KB cap


def _eval_allowance(action_request: Dict[str, Any]) -> (bool, str, list):
    """Evaluate scoped allows; default deny-all."""
    # Read-only logs test
    if _is_allowed_test(action_request):
        return True, POLICY_ALLOW_TEST_FS_READ_LOGS, [
            {
                "scope": "logs/calyx/*",
                "mode": "read_only",
                "policy": POLICY_ALLOW_TEST_FS_READ_LOGS,
                "timebox_hours": action_request.get("timebox_hours"),
            }
        ]
    # Append-only summaries
    if _is_allowed_summary_write(action_request):
        return True, POLICY_ALLOW_SUMMARY_WRITES, [
            {
                "scope": "outgoing/CBO/summaries/*",
                "mode": "append_only",
                "policy": POLICY_ALLOW_SUMMARY_WRITES,
                "timebox_hours": action_request.get("timebox_hours"),
            }
        ]
    # Cache writes (bounded)
    if _is_allowed_cache_write(action_request):
        return True, POLICY_ALLOW_CACHE_WRITES, [
            {
                "scope": "logs/calyx/cache/*",
                "mode": "write_replace_within_cache",
                "policy": POLICY_ALLOW_CACHE_WRITES,
                "timebox_hours": action_request.get("timebox_hours"),
            }
        ]
    # Drift evidence append
    if _is_allowed_drift_evidence(action_request):
        return True, POLICY_ALLOW_DRIFT_EVIDENCE, [
            {
                "scope": "logs/calyx/drift_evidence/*",
                "mode": "append_only",
                "policy": POLICY_ALLOW_DRIFT_EVIDENCE,
                "timebox_hours": action_request.get("timebox_hours"),
            }
        ]
    return False, POLICY_DENY_ALL, []


def evaluate_action_request(action_request: Dict[str, Any]) -> Dict[str, Any]:
    """Return a Gate Decision Object (deny-all in v0.1)."""
    _validate_action_request(action_request)
    registry_metadata = annotate_action_request(action_request)

    allowed, decision_reason, conditions = _eval_allowance(action_request)
    refusal_msg = None if allowed else standard_refusal()

    return {
        "decision_id": new_decision_id(action_request.get("node_id", "unknown")),
        "request": action_request,
        "allowed": allowed,
        "decision_reason": decision_reason,
        "refusal_message": refusal_msg,
        "conditions": conditions,
        "governance_state": dict(DEFAULT_GOVERNANCE_STATE),
        "safety_status": dict(DEFAULT_SAFETY_STATUS),
        "registry_metadata": registry_metadata,
        "timestamp": now_iso(),
        "schema_version": EXECUTION_GATE_DECISION_SCHEMA,
    }


def request_action(action_request: Dict[str, Any]) -> Dict[str, Any]:
    """Validate, log request/decision, and return decision (deny-all)."""
    _validate_action_request(action_request)

    # Log execution_request
    log_telemetry(
        event_type="execution_request",
        subsystem=action_request.get("node_id", "UNKNOWN_NODE"),
        severity="info",
        payload={
            "capability": action_request.get("capability"),
            "action": action_request.get("action"),
            "node_id": action_request.get("node_id"),
            "node_role": action_request.get("node_role"),
            "target": action_request.get("target"),
            "intent": action_request.get("intent"),
            "justification": action_request.get("justification"),
        },
        request_id=action_request.get("request_id"),
        session_id=action_request.get("session_id"),
    )

    decision = evaluate_action_request(action_request)

    # Log execution_decision
    log_telemetry(
        event_type="execution_decision",
        subsystem="EXECUTION_GATE",
        severity="info",
        payload={
            "decision_id": decision["decision_id"],
            "allowed": decision["allowed"],
            "decision_reason": decision["decision_reason"],
            "refusal_message": decision.get("refusal_message"),
            "capability": action_request.get("capability"),
            "node_id": action_request.get("node_id"),
            "registry_metadata": decision.get("registry_metadata"),
        },
        request_id=action_request.get("request_id"),
        session_id=action_request.get("session_id"),
        reflection="Execution Gate v0.1 denies all action requests by policy.",
    )

    return decision


__all__ = [
    "CAPABILITIES",
    "EXECUTION_GATE_DECISION_SCHEMA",
    "POLICY_DENY_ALL",
    "new_decision_id",
    "build_action_request",
    "evaluate_action_request",
    "request_action",
]
