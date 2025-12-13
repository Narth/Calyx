"""Node Output Schema v1.0 helper utilities for Station Calyx.

Append-only helpers to construct and write node_output_v1.0 records and
optionally emit linked CTL telemetry entries. No scheduling or autonomous
execution is introduced; callers must invoke explicitly.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from tools.calyx_telemetry_logger import (
    BASE_LOG_DIR,
    DEFAULT_GOVERNANCE_STATE,
    log_telemetry,
    new_request_id,
    new_session_id,
    now_iso,
)

NODE_OUTPUT_SCHEMA_VERSION = "node_output_v1.0"
NODE_OUTPUT_PATH = BASE_LOG_DIR / "node_outputs.jsonl"
DEFAULT_NODE_GOVERNANCE = {
    "governance_state": dict(DEFAULT_GOVERNANCE_STATE),
    "allowed_capabilities": ["read_files", "summarize", "reflect"],
    "denied_capabilities": [
        "execute_code",
        "modify_files",
        "schedule_tasks",
    ],
}
DEFAULT_NODE_SAFETY = {
    "rule_violations": [],
    "blocked_intents": [],
    "risk_assessment": "low",
    "notes": "Within reflection-only boundaries; no execution attempted.",
}


def new_node_output_id(node_id: str) -> str:
    """Generate a node_output_id using timestamp and short UUID."""
    ts = now_iso().replace(":", "").replace("-", "")
    return f"nodeout-{ts}-{node_id}-{uuid.uuid4().hex[:8]}"


def append_node_output(record: Dict[str, Any]) -> None:
    """Append a node_output_v1.0 record to logs/calyx/node_outputs.jsonl."""
    target = Path(NODE_OUTPUT_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False)
        handle.write("\n")


def build_node_output(
    *,
    node_id: str,
    node_role: str,
    request_context: Dict[str, Any],
    task: Dict[str, Any],
    outputs: Dict[str, Any],
    governance: Optional[Dict[str, Any]] = None,
    safety: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    artifacts: Optional[Dict[str, Any]] = None,
    introspection: Optional[Dict[str, Any]] = None,
    node_output_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Construct a node_output_v1.0 record with required fields."""
    record = {
        "node_output_id": node_output_id or new_node_output_id(node_id),
        "node_id": node_id,
        "node_role": node_role,
        "timestamp": timestamp or now_iso(),
        "request_context": request_context,
        "task": task,
        "outputs": outputs,
        "governance": governance
        or {
            "governance_state": dict(DEFAULT_GOVERNANCE_STATE),
            "allowed_capabilities": list(DEFAULT_NODE_GOVERNANCE["allowed_capabilities"]),
            "denied_capabilities": list(DEFAULT_NODE_GOVERNANCE["denied_capabilities"]),
        },
        "safety": safety
        or {
            "rule_violations": list(DEFAULT_NODE_SAFETY["rule_violations"]),
            "blocked_intents": list(DEFAULT_NODE_SAFETY["blocked_intents"]),
            "risk_assessment": DEFAULT_NODE_SAFETY["risk_assessment"],
            "notes": DEFAULT_NODE_SAFETY["notes"],
        },
        "schema_version": NODE_OUTPUT_SCHEMA_VERSION,
    }
    if metrics is not None:
        record["metrics"] = metrics
    if artifacts is not None:
        record["artifacts"] = artifacts
    if introspection is not None:
        record["introspection"] = introspection
    return record


def emit_node_output_with_telemetry(
    *,
    node_id: str,
    node_role: str,
    request_context: Dict[str, Any],
    task: Dict[str, Any],
    outputs: Dict[str, Any],
    governance: Optional[Dict[str, Any]] = None,
    safety: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    artifacts: Optional[Dict[str, Any]] = None,
    introspection: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create node output record, append to node_outputs.jsonl, and emit CTL link."""
    record = build_node_output(
        node_id=node_id,
        node_role=node_role,
        request_context=request_context,
        task=task,
        outputs=outputs,
        governance=governance,
        safety=safety,
        metrics=metrics,
        artifacts=artifacts,
        introspection=introspection,
    )
    append_node_output(record)

    log_telemetry(
        event_type="node_output",
        subsystem=node_id,
        severity="info",
        payload={
            "node_output_id": record["node_output_id"],
            "node_id": node_id,
            "node_role": node_role,
            "task_id": task.get("task_id"),
        },
        request_id=request_id,
        session_id=session_id,
    )
    return record


__all__ = [
    "NODE_OUTPUT_SCHEMA_VERSION",
    "NODE_OUTPUT_PATH",
    "new_node_output_id",
    "new_request_id",
    "new_session_id",
    "build_node_output",
    "append_node_output",
    "emit_node_output_with_telemetry",
]
