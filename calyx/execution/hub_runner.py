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
from calyx.kernel.envelope import WorkEnvelope
from calyx.kernel.integrity_gate import spine_operation_lease
from calyx.kernel.paths import resolve_repo_root, resolve_runtime_dir, resolve_receipts_dir, resolve_manifests_dir
from calyx.kernel.receipts import append_receipt_line

from .task_handlers import HANDLERS


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
            append_receipt_line(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "phase": "execution",
                    "status": "denied",
                    "receipt_type": "hub_runner",
                    "envelope_id": env.envelope_id,
                    "reason": "integrity_or_lease_failed",
                },
                prefix="hub_runner",
                repo_root=root,
            )
            return False, "integrity_or_lease_failed"

        contract_path_val = contract_path or (root / "CALYX_CONTRACT.yaml")
        contract, contract_sha = load_contract(contract_path_val)
        if isinstance(envelope, dict):
            envelope = WorkEnvelope.from_dict(envelope)
        mint_ok, mint_reason = _verify_cbo_mint(envelope, runtime_dir)
        if not mint_ok:
            append_receipt_line(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "phase": "execution",
                    "status": "denied",
                    "receipt_type": "hub_runner",
                    "envelope_id": envelope.envelope_id,
                    "reason": mint_reason,
                },
                prefix="hub_runner",
                repo_root=root,
            )
            return False, mint_reason
        allowed, reason = validate_work_envelope(envelope, contract, contract_sha)
        if not allowed:
            append_receipt_line(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "phase": "execution",
                    "status": "denied",
                    "receipt_type": "hub_runner",
                    "envelope_id": envelope.envelope_id,
                    "reason": reason,
                },
                prefix="hub_runner",
                repo_root=root,
            )
            return False, reason
        handler = HANDLERS.get(envelope.task_type)
        if not handler:
            append_receipt_line(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "phase": "execution",
                    "status": "denied",
                    "receipt_type": "hub_runner",
                    "envelope_id": envelope.envelope_id,
                    "reason": f"no_handler:{envelope.task_type}",
                },
                prefix="hub_runner",
                repo_root=root,
            )
            return False, f"no handler for task_type {envelope.task_type}"
        try:
            success, result, receipts = handler(
                envelope.to_canonical_dict(),
                contract,
                root,
            )
        except Exception as e:
            append_receipt_line(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "phase": "execution",
                    "status": "failed",
                    "receipt_type": "hub_runner",
                    "envelope_id": envelope.envelope_id,
                    "error": str(e),
                },
                prefix="hub_runner",
                repo_root=root,
            )
            return False, str(e)
        run_id = f"{envelope.task_type}_{envelope.envelope_id[:8]}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        append_receipt_line(
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
            prefix="hub_runner",
            repo_root=root,
        )
        manifests_dir = resolve_manifests_dir(root)
        manifests_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifests_dir / f"{run_id}_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(
                {"run_id": run_id, "envelope_id": envelope.envelope_id, "artifacts": receipts, "result": result},
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
