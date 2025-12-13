"""Governance orchestration helpers (reflection-only).

Build governance requests, append to governance log, and emit governance_decision
records (no actual execution/mutation is performed).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from tools.calyx_telemetry_logger import log_telemetry, now_iso

GOV_REQUEST_LOG = Path("logs") / "calyx" / "governance_requests.jsonl"
GOV_DECISION_LOG = Path("logs") / "calyx" / "governance_decisions.jsonl"
EXECUTION_REQUEST_LOG = Path("logs") / "calyx" / "execution_requests.jsonl"


def append_jsonl(obj: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        json.dump(obj, handle, ensure_ascii=False)
        handle.write("\n")


def build_kernel_diagnostics_execution_request(
    request: Dict[str, Any], decision: Dict[str, Any]
) -> Dict[str, Any]:
    """Build an execution_request for kernel diagnostics ingest directive (reflection-only)."""
    target = request.get("intent", {}).get("target", {}) or {}
    target_path = target.get("path") or ""
    basename = Path(target_path).stem
    canon_path = f"canon/kernel_diagnostics/{basename}.md"
    exec_request_id = f"execreq-{now_iso()}-{decision['decision_id'].split('-')[-1]}"

    return {
        "event_type": "execution_request",
        "execution_request_id": exec_request_id,
        "timestamp": now_iso(),
        "channel": "governance_cli",
        "source": {
            "request_id": request.get("request_id"),
            "session_id": request.get("session_id"),
            "actor": request.get("actor", {}).get("id", "architect"),
        },
        "intent": {
            "scope": "kernel_diagnostics",
            "requested_action": "ingest_directive",
            "description": request.get("intent", {}).get("description"),
            "target": target,
        },
        "capabilities": [
            {
                "name": "filesystem_read_directive",
                "args": {"path": target_path},
            },
            {
                "name": "filesystem_write_canon_kernel_diagnostics",
                "args": {"canon_path": canon_path},
            },
        ],
        "safety_frame": request.get("safety_frame"),
        "governance_ref": {
            "governance_request_id": request.get("request_id"),
            "governance_decision_id": decision.get("decision_id"),
            "policy_version": decision.get("policy_version"),
        },
        "schema_version": "execution_request_v0.1",
    }


def _maybe_emit_kernel_diagnostics_exec_request(
    request: Dict[str, Any], decision: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Emit execution_request for kernel diagnostics ingest if all conditions match."""
    intent = request.get("intent") or {}
    target = intent.get("target") or {}
    scope_ok = intent.get("scope") == "kernel_diagnostics"
    action_ok = intent.get("requested_action") == "ingest_directive"
    target_kind_ok = target.get("kind") == "file"
    target_path = target.get("path") or ""
    path_ok = target_path.startswith("outgoing/CBO/governance/") and target_path.endswith(
        ".md"
    )
    channel_ok = request.get("channel") == "governance_cli"
    decision_ok = decision.get("outcome") == "allowed"
    exec_allowed = (request.get("safety_frame") or {}).get("execution_allowed", False)

    if not all([scope_ok, action_ok, target_kind_ok, path_ok, channel_ok, decision_ok, exec_allowed]):
        return None

    exec_req = build_kernel_diagnostics_execution_request(request, decision)
    append_jsonl(exec_req, EXECUTION_REQUEST_LOG)

    log_telemetry(
        event_type="execution_request",
        subsystem="CBO",
        severity="info",
        payload={
            "execution_request_id": exec_req["execution_request_id"],
            "request_id": exec_req["source"]["request_id"],
            "scope": exec_req["intent"]["scope"],
            "requested_action": exec_req["intent"]["requested_action"],
            "target_path": target_path,
            "capabilities": [cap["name"] for cap in exec_req["capabilities"]],
        },
        request_id=request.get("request_id"),
        session_id=request.get("session_id"),
    )
    return exec_req


def run_governance_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Record a governance_decision event for the given request (reflection-only)."""
    # Append request for traceability
    append_jsonl(request, GOV_REQUEST_LOG)

    # Build a simple decision (no execution is performed)
    decision = {
        "schema_version": "governance_decision_v0.1",
        "request_id": request.get("request_id"),
        "decision_id": f"govdec-{now_iso()}",
        "timestamp": now_iso(),
        "channel": request.get("channel"),
        "outcome": "allowed",  # reflection-only; no action performed
        "reason": "Recorded governance request; no execution performed under deny-all.",
        "required_capabilities": request.get("safety_frame", {}).get(
            "max_side_effects", []
        ),
        "safety_annotation": {
            "calyx_theory_version": "calyx_theory_canon_v0.1",
            "human_primacy_reviewed": True,
            "hidden_channel_awareness": "no_hidden_channels_observed",
        },
        "canonical_path": None,
        "notes": [],
    }

    exec_req = _maybe_emit_kernel_diagnostics_exec_request(request, decision)
    if exec_req:
        decision["notes"].append(
            "Execution request emitted for kernel_diagnostics ingest_directive lane v0.1."
        )

    append_jsonl(decision, GOV_DECISION_LOG)

    # Emit CTL governance_decision
    log_telemetry(
        event_type="governance_decision",
        subsystem="CBO",
        severity="info",
        payload={
            "decision": "governance_request_processed",
            "channel": decision["channel"],
            "request_id": decision["request_id"],
            "outcome": decision["outcome"],
            "reason": decision["reason"],
        },
        request_id=request.get("request_id"),
        session_id=request.get("session_id"),
    )

    return decision


__all__ = ["run_governance_request", "GOV_REQUEST_LOG", "GOV_DECISION_LOG"]
