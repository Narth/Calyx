"""Plan: build plan from artifact; mint Work Envelope (CBO only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from calyx.kernel.critique_checkpoint import build_critique_checkpoint
from calyx.kernel.envelope import WorkEnvelope
from calyx.kernel.failure_patterns import attach_failure_pattern_metadata
from calyx.kernel.routing_proof import validate_routing_proof
from calyx.kernel.swarm_lease import issue_static_worker_leases
from calyx.kernel.swarm_sandbox import prepare_read_only_probe_sandboxes
from calyx.kernel.swarm_trace import (
    append_sandbox_preparation_to_trace_graph,
    refresh_swarm_receipt_bundle,
)
from calyx.kernel.swarm_work_envelope import validate_swarm_extensions

from .intake_card import intake_card_clarification_message, merge_intake_card, validate_intake_card
from .routing_proof import normalize_routing_proof
from .registry import load_intent_artifact, load_status, save_plan, save_status
from .score import score_intent


def build_plan(intent_id: str, runtime_dir: Path) -> dict[str, Any] | None:
    """
    Build plan from Intent Artifact. Persist plan.json. No Work Envelope yet.
    """
    artifact = load_intent_artifact(intent_id, runtime_dir)
    if not artifact:
        return None
    status = load_status(intent_id, runtime_dir)
    if status and status.get("status") != "ready":
        return None
    artifact = merge_intake_card(artifact)
    valid, missing = validate_intake_card(artifact.get("intake_card") or {})
    if not valid:
        from .registry import append_clarification, save_intent_artifact

        save_intent_artifact(intent_id, runtime_dir, artifact)
        append_clarification(
            intent_id,
            runtime_dir,
            {"request": intake_card_clarification_message(missing), "source": "phase1_intake_card"},
        )
        save_status(
            intent_id,
            runtime_dir,
            attach_failure_pattern_metadata(
                {
                "status": "pending_clarification",
                "intake_card_status": "needs_clarification",
                "missing_intake_fields": missing,
                "reason": "phase1_intake_card_incomplete",
                },
                pattern_ids=["scope_drift"],
            ),
        )
        return None
    artifact["routing_proof"] = normalize_routing_proof(artifact)
    routing_valid, routing_missing = validate_routing_proof(artifact.get("routing_proof") or {})
    if not routing_valid:
        from .registry import append_clarification, save_intent_artifact

        save_intent_artifact(intent_id, runtime_dir, artifact)
        append_clarification(
            intent_id,
            runtime_dir,
            {
                "request": f"Phase II routing proof incomplete. Missing fields: {', '.join(routing_missing)}.",
                "source": "phase2_routing_proof",
            },
        )
        save_status(
            intent_id,
            runtime_dir,
            attach_failure_pattern_metadata(
                {
                "status": "pending_clarification",
                "intake_card_status": "complete",
                "missing_intake_fields": [],
                "routing_proof_status": "needs_clarification",
                "missing_routing_fields": routing_missing,
                "reason": "phase2_routing_proof_incomplete",
                },
                pattern_ids=["tool_misuse", "hallucinated_context"],
            ),
        )
        return None
    scored = score_intent(artifact)
    critique_checkpoint = build_critique_checkpoint(
        task_type=artifact.get("task_type", "doc_update"),
        risk_tier=scored.get("risk_tier", "low"),
    )
    plan = {
        "intent_id": intent_id,
        "task_type": artifact.get("task_type", "doc_update"),
        "scope": artifact.get("scope") or {"paths": ["**"]},
        "constraints": artifact.get("constraints") or {"timeout_seconds": 300},
        "risk_tier": scored.get("risk_tier", "low"),
        "source": artifact.get("source", "discord"),
        "requires_human_approval": artifact.get("requires_human_approval", False),
        "approval_token": artifact.get("approval_token"),
        "intake_card": artifact.get("intake_card") or {},
        "routing_proof": artifact.get("routing_proof") or {},
        "critique_checkpoint": critique_checkpoint,
    }
    swarm_valid, swarm_errors = validate_swarm_extensions(plan["scope"], plan["constraints"])
    if not swarm_valid:
        from .registry import append_clarification

        append_clarification(
            intent_id,
            runtime_dir,
            {
                "request": "Phase 0 swarm schema invalid. Errors: " + "; ".join(swarm_errors),
                "source": "phase0_swarm_schema_validation",
            },
        )
        save_status(
            intent_id,
            runtime_dir,
            attach_failure_pattern_metadata(
                {
                    "status": "pending_clarification",
                    "intake_card_status": "complete",
                    "routing_proof_status": "complete",
                    "swarm_schema_status": "needs_clarification",
                    "swarm_validation_errors": swarm_errors,
                    "reason": "phase0_swarm_schema_invalid",
                },
                pattern_ids=["scope_drift"],
            ),
        )
        return None
    save_plan(intent_id, runtime_dir, plan)
    return plan


def mint_work_envelope(intent_id: str, runtime_dir: Path, repo_root: Path | None = None) -> WorkEnvelope | None:
    """
    CBO-only: mint Work Envelope from clarified Intent Artifact. Persist deterministic hash.
    No direct Mail -> Work without Intent Artifact persistence.
    """
    plan = build_plan(intent_id, runtime_dir)
    if not plan:
        return None
    artifact = load_intent_artifact(intent_id, runtime_dir)
    if not artifact:
        return None
    from datetime import datetime, timezone
    we = WorkEnvelope(
        envelope_id=artifact.get("envelope_id", intent_id),
        intent_id=intent_id,
        task_type=plan["task_type"],
        scope=plan["scope"],
        constraints=plan["constraints"],
        ts_utc=artifact.get("ts_utc", datetime.now(timezone.utc).isoformat()),
        source=plan["source"],
        requires_human_approval=plan.get("requires_human_approval", False),
        approval_token=plan.get("approval_token"),
        risk_tier=plan.get("risk_tier", "low"),
        critique_checkpoint=plan.get("critique_checkpoint") or {},
    )
    det_hash = we.deterministic_hash()
    status_payload: dict[str, Any] = {"status": "minted", "work_envelope_hash": det_hash}
    work_outbox = runtime_dir / "cbo" / "work_outbox"
    out_path = work_outbox / f"{we.envelope_id}.json"
    if we.has_swarm_extensions():
        try:
            (
                lease_artifact,
                ownership_map,
                lifecycle,
                trace_graph,
                receipt_bundle,
                lease_artifact_path,
                ownership_map_path,
                lifecycle_path,
                trace_graph_path,
                receipt_bundle_path,
                lease_receipt_path,
                transition_receipt_paths,
            ) = issue_static_worker_leases(
                we,
                runtime_dir,
                work_envelope_ref=str(out_path),
            )
            sandbox_manifests, sandbox_manifest_paths, snapshot_records, snapshot_paths = (
                prepare_read_only_probe_sandboxes(
                    lease_artifact,
                    runtime_dir=runtime_dir,
                    repo_root=repo_root or Path.cwd(),
                )
            )
            trace_graph, receipt_bundle = append_sandbox_preparation_to_trace_graph(
                runtime_dir,
                swarm_run_id=lease_artifact["swarm_run_id"],
                sandbox_manifests=sandbox_manifests,
                sandbox_manifest_paths=sandbox_manifest_paths,
                snapshot_records=snapshot_records,
                snapshot_paths=snapshot_paths,
            )
        except ValueError as exc:
            from .registry import append_clarification

            reason = str(exc)
            append_clarification(
                intent_id,
                runtime_dir,
                {
                    "request": "Phase 2 swarm ownership validation failed. Errors: " + reason,
                    "source": "phase2_swarm_ownership_validation",
                },
            )
            save_status(
                intent_id,
                runtime_dir,
                attach_failure_pattern_metadata(
                    {
                        "status": "pending_clarification",
                        "swarm_schema_status": "complete",
                        "swarm_lease_status": "needs_clarification",
                        "swarm_ownership_status": "needs_clarification",
                        "swarm_validation_errors": [reason],
                        "reason": "phase2_swarm_ownership_conflict",
                    },
                    pattern_ids=["scope_drift"],
                ),
            )
            return None
        status_payload.update(
            {
                "swarm_lease_status": "static_issued",
                "swarm_ownership_status": "validated",
                "worker_lease_state": lease_artifact.get("lease_state"),
                "worker_lease_count": lease_artifact.get("worker_count"),
                "worker_leases_path": str(lease_artifact_path),
                "ownership_map_path": str(ownership_map_path),
                "lease_lifecycle_path": str(lifecycle_path),
                "trace_graph_path": str(trace_graph_path),
                "receipt_bundle_path": str(receipt_bundle_path),
                "worker_lease_receipt_path": str(lease_receipt_path),
                "ownership_conflict_count": len(ownership_map.get("conflicts", [])),
                "worker_lease_transition_receipt_count": len(transition_receipt_paths),
                "worker_lease_terminal_count": sum(
                    1 for row in lifecycle.get("leases", []) if row.get("terminal_state")
                ),
                "sandbox_manifest_count": len(sandbox_manifest_paths),
                "snapshot_count": len(snapshot_paths),
                "trace_node_count": len(trace_graph.get("nodes", [])),
                "receipt_bundle_status": receipt_bundle.get("bundle_status"),
            }
        )
    out_dict = we.to_canonical_dict()
    out_dict["minted_by"] = "cbo"
    out_dict["minted_hash"] = det_hash
    import json
    import os
    import tempfile
    content = json.dumps(out_dict, indent=2, ensure_ascii=False)
    work_outbox.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=work_outbox, prefix=".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, out_path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    if we.has_swarm_extensions():
        refreshed_bundle = refresh_swarm_receipt_bundle(
            runtime_dir,
            plan["scope"]["swarm"]["swarm_run_id"],
        )
        status_payload["receipt_bundle_status"] = refreshed_bundle.get("bundle_status")
    save_status(intent_id, runtime_dir, status_payload)
    return we
