"""Plan: build plan from artifact; mint Work Envelope (CBO only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from calyx.kernel.envelope import WorkEnvelope
from calyx.kernel.paths import resolve_repo_root, resolve_runtime_dir

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
    scored = score_intent(artifact)
    plan = {
        "intent_id": intent_id,
        "task_type": artifact.get("task_type", "doc_update"),
        "scope": artifact.get("scope") or {"paths": ["**"]},
        "constraints": artifact.get("constraints") or {"timeout_seconds": 300},
        "risk_tier": scored.get("risk_tier", "low"),
        "source": artifact.get("source", "discord"),
        "requires_human_approval": artifact.get("requires_human_approval", False),
        "approval_token": artifact.get("approval_token"),
    }
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
    root = repo_root or resolve_repo_root()
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
    )
    det_hash = we.deterministic_hash()
    save_status(intent_id, runtime_dir, {"status": "minted", "work_envelope_hash": det_hash})
    work_outbox = runtime_dir / "cbo" / "work_outbox"
    work_outbox.mkdir(parents=True, exist_ok=True)
    out_dict = we.to_canonical_dict()
    out_dict["minted_by"] = "cbo"
    out_dict["minted_hash"] = det_hash
    out_path = work_outbox / f"{we.envelope_id}.json"
    import json
    import os
    import tempfile
    content = json.dumps(out_dict, indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=work_outbox, prefix=".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, out_path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return we
