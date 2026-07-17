"""
Hub Runner: validate Work Envelope via contract, execute via task handlers, emit receipt and manifest.
Work Envelope only; no raw payloads.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from calyx.kernel.contract import load_contract, validate_work_envelope, get_tool_allowlist
from calyx.kernel.critique_checkpoint import evaluate_critique_checkpoint, validate_critique_checkpoint
from calyx.kernel.envelope import WorkEnvelope
from calyx.kernel.failure_patterns import attach_failure_pattern_metadata
from calyx.kernel.integrity_gate import spine_operation_lease
from calyx.kernel.paths import resolve_repo_root, resolve_runtime_dir, resolve_receipts_dir, resolve_manifests_dir
from calyx.kernel.receipts import append_receipt_line
from calyx.kernel.swarm_lease import validate_static_worker_lease_set

from .task_handlers import HANDLERS


def _write_intent_checkpoint_artifact(runtime_dir: Path, intent_id: str, report: dict[str, Any]) -> Path:
    """Persist critique checkpoint artifact beside the intent."""
    from calyx.cbo.intent_pipeline.registry import save_critique_checkpoint

    return save_critique_checkpoint(intent_id, runtime_dir, report)


def _update_intent_status(runtime_dir: Path, intent_id: str, **updates: Any) -> None:
    """Merge execution status into runtime/cbo/intents/<intent_id>/status.json."""
    status_path = runtime_dir / "cbo" / "intents" / intent_id / "status.json"
    if not status_path.exists():
        return
    try:
        with open(status_path, "r", encoding="utf-8") as f:
            status = json.load(f)
    except Exception:
        status = {}
    status.update(updates)
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)


def _append_hub_receipt(repo_root: Path, payload: dict[str, Any]) -> None:
    """Append a hub-runner receipt line with failure-pattern metadata when applicable."""
    append_receipt_line(
        attach_failure_pattern_metadata(
            payload,
            signals=[
                payload.get("reason"),
                payload.get("error"),
                payload.get("phase"),
                payload.get("status"),
                payload.get("task_type"),
                payload.get("critique_status"),
                payload.get("validation_status"),
            ],
        ),
        prefix="hub_runner",
        repo_root=repo_root,
    )


def _verify_cbo_mint(envelope: WorkEnvelope, runtime_dir: Path) -> tuple[bool, str | None]:
    """Only CBO-minted envelopes may execute. Returns (valid, denial_reason)."""
    status_path = runtime_dir / "cbo" / "intents" / envelope.intent_id / "status.json"
    if not status_path.exists():
        return False, "intent_artifact_missing"
    try:
        with open(status_path, "r", encoding="utf-8") as f:
            status = json.load(f)
    except Exception:
        return False, "intent_status_unreadable"
    if status.get("status") != "minted":
        return False, "work_envelope_not_minted"
    expected_hash = status.get("work_envelope_hash")
    actual_hash = envelope.deterministic_hash()
    if expected_hash != actual_hash:
        return False, "work_envelope_hash_mismatch"
    return True, None


def get_work_outbox(runtime_dir: Path) -> Path:
    """Where CBO writes minted Work Envelopes for execution."""
    path = runtime_dir / "cbo" / "work_outbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_work_envelope(
    envelope: WorkEnvelope | dict[str, Any],
    repo_root: Path | None = None,
    contract_path: Path | str | None = None,
) -> tuple[bool, str | None]:
    """
    Validate Work Envelope, run handler, write receipt and manifest.
    Returns (success, error_message).
    """
    root = repo_root or resolve_repo_root()
    runtime_dir = resolve_runtime_dir(root)
    env = envelope if isinstance(envelope, WorkEnvelope) else WorkEnvelope.from_dict(envelope)
    with spine_operation_lease(runtime_dir, root, include_execution_path=True, skip_if_env=True) as ok:
        if not ok:
            _append_hub_receipt(
                root,
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "phase": "execution",
                    "status": "denied",
                    "receipt_type": "hub_runner",
                    "envelope_id": env.envelope_id,
                    "reason": "integrity_or_lease_failed",
                },
            )
            return False, "integrity_or_lease_failed"

        contract_path_val = contract_path or (root / "CALYX_CONTRACT.yaml")
        contract, contract_sha = load_contract(contract_path_val)
        if isinstance(envelope, dict):
            envelope = WorkEnvelope.from_dict(envelope)
        mint_ok, mint_reason = _verify_cbo_mint(envelope, runtime_dir)
        if not mint_ok:
            _append_hub_receipt(
                root,
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "phase": "execution",
                    "status": "denied",
                    "receipt_type": "hub_runner",
                    "envelope_id": envelope.envelope_id,
                    "reason": mint_reason,
                },
            )
            return False, mint_reason
        allowed, reason = validate_work_envelope(envelope, contract, contract_sha)
        if not allowed:
            _append_hub_receipt(
                root,
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "phase": "execution",
                    "status": "denied",
                    "receipt_type": "hub_runner",
                    "envelope_id": envelope.envelope_id,
                    "reason": reason,
                },
            )
            return False, reason
        if envelope.has_swarm_extensions():
            swarm_valid, swarm_errors, lease_artifact, ownership_map = validate_static_worker_lease_set(envelope)
            if not swarm_valid:
                _append_hub_receipt(
                    root,
                    {
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "phase": "validate",
                        "status": "denied",
                        "receipt_type": "hub_runner",
                        "envelope_id": envelope.envelope_id,
                        "reason": "invalid_swarm_lease_set",
                        "errors": swarm_errors,
                    },
                )
                return False, "invalid_swarm_lease_set"
            _append_hub_receipt(
                root,
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "phase": "validate",
                    "status": "allowed",
                    "receipt_type": "hub_runner",
                    "envelope_id": envelope.envelope_id,
                    "reason": "swarm_validate_only_phase2",
                    "worker_ids": [lease.get("worker_id") for lease in lease_artifact.get("leases", [])],
                    "ownership_conflict_count": len(ownership_map.get("conflicts", [])),
                },
            )
            return False, "swarm_execution_not_enabled_phase2"
        tool_allowlist = get_tool_allowlist(contract, envelope.task_type)
        checkpoint = envelope.critique_checkpoint or {}
        checkpoint_valid, checkpoint_errors, expected_checkpoint = validate_critique_checkpoint(
            checkpoint,
            task_type=envelope.task_type,
            risk_tier=envelope.risk_tier,
            tool_allowlist=tool_allowlist,
        )
        if expected_checkpoint.get("required") and not checkpoint_valid:
            report = {
                "required": True,
                "task_type": envelope.task_type,
                "risk_tier": envelope.risk_tier,
                "triggers": expected_checkpoint.get("triggers", []),
                "phase_graph": checkpoint.get("phase_graph") or [],
                "tool_allowlist": tool_allowlist,
                "critique_status": "failed",
                "validation_status": "failed",
                "finalization_allowed": False,
                "errors": checkpoint_errors,
            }
            artifact_path = _write_intent_checkpoint_artifact(runtime_dir, envelope.intent_id, report)
            _update_intent_status(
                runtime_dir,
                envelope.intent_id,
                critique_checkpoint_status="failed",
                critique_checkpoint_errors=checkpoint_errors,
                critique_checkpoint_path=str(artifact_path),
            )
            _append_hub_receipt(
                root,
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "phase": "critique",
                    "status": "denied",
                    "receipt_type": "hub_runner",
                    "envelope_id": envelope.envelope_id,
                    "reason": "critique_checkpoint_missing_or_invalid",
                    "errors": checkpoint_errors,
                },
            )
            return False, "critique_checkpoint_missing_or_invalid"
        handler = HANDLERS.get(envelope.task_type)
        if not handler:
            _append_hub_receipt(
                root,
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "phase": "execution",
                    "status": "denied",
                    "receipt_type": "hub_runner",
                    "envelope_id": envelope.envelope_id,
                    "reason": f"no_handler:{envelope.task_type}",
                },
            )
            return False, f"no handler for task_type {envelope.task_type}"
        try:
            success, result, receipts = handler(
                envelope.to_canonical_dict(),
                contract,
                root,
            )
        except Exception as e:
            _append_hub_receipt(
                root,
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "phase": "execution",
                    "status": "failed",
                    "receipt_type": "hub_runner",
                    "envelope_id": envelope.envelope_id,
                    "error": str(e),
                },
            )
            return False, str(e)
        critique_report = evaluate_critique_checkpoint(
            checkpoint=checkpoint or expected_checkpoint,
            expected=expected_checkpoint,
            execution_success=success,
            result=result,
            receipts=receipts,
            requires_human_approval=envelope.requires_human_approval,
            approval_token=envelope.approval_token,
        )
        artifact_path = _write_intent_checkpoint_artifact(runtime_dir, envelope.intent_id, critique_report)
        if critique_report.get("required"):
            _append_hub_receipt(
                root,
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "phase": "critique",
                    "status": "allowed" if critique_report.get("critique_status") == "passed" else "failed",
                    "receipt_type": "hub_runner",
                    "envelope_id": envelope.envelope_id,
                    "task_type": envelope.task_type,
                    "critique_status": critique_report.get("critique_status"),
                    "artifact_path": str(artifact_path),
                },
            )
            _append_hub_receipt(
                root,
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "phase": "validate",
                    "status": "allowed" if critique_report.get("validation_status") == "passed" else "failed",
                    "receipt_type": "hub_runner",
                    "envelope_id": envelope.envelope_id,
                    "task_type": envelope.task_type,
                    "validation_status": critique_report.get("validation_status"),
                    "artifact_path": str(artifact_path),
                },
            )
            if not critique_report.get("finalization_allowed"):
                _update_intent_status(
                    runtime_dir,
                    envelope.intent_id,
                    critique_checkpoint_status="failed",
                    critique_checkpoint_errors=["critique_checkpoint_failed"],
                    critique_checkpoint_path=str(artifact_path),
                )
                return False, "critique_checkpoint_failed"
        run_id = f"{envelope.task_type}_{envelope.envelope_id[:8]}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        _update_intent_status(
            runtime_dir,
            envelope.intent_id,
            status="executed",
            critique_checkpoint_status=critique_report.get("validation_status", "not_required"),
            critique_checkpoint_path=str(artifact_path),
        )
        _append_hub_receipt(
            root,
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "phase": "execution",
                "status": "allowed" if success else "failed",
                "receipt_type": "hub_runner",
                "envelope_id": envelope.envelope_id,
                "run_id": run_id,
                "task_type": envelope.task_type,
                "result": result,
            },
        )
        manifests_dir = resolve_manifests_dir(root)
        manifests_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifests_dir / f"{run_id}_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "run_id": run_id,
                    "envelope_id": envelope.envelope_id,
                    "artifacts": receipts,
                    "result": result,
                    "critique_checkpoint": critique_report,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        return success, None


def process_work_outbox(repo_root: Path | None = None) -> dict[str, int]:
    """Process all Work Envelopes in work_outbox. Returns counts. Lease acquired per envelope in run_work_envelope."""
    root = repo_root or resolve_repo_root()
    runtime_dir = resolve_runtime_dir(root)
    outbox = get_work_outbox(runtime_dir)
    processed = denied = 0
    for path in sorted(outbox.glob("*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                envelope = json.load(f)
        except Exception:
            denied += 1
            continue
        ok, _ = run_work_envelope(envelope, repo_root=root)
        if ok:
            processed += 1
            path.unlink()
        else:
            denied += 1
    return {"processed": processed, "denied": denied}
