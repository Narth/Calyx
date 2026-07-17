from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def test_build_critique_checkpoint_requires_phase_graph_for_cross_tool() -> None:
    from calyx.kernel.critique_checkpoint import CRITIQUE_PHASE_GRAPH, build_critique_checkpoint

    checkpoint = build_critique_checkpoint(task_type="repo_readonly_review", risk_tier="low")
    assert checkpoint["required"] is True
    assert checkpoint["phase_graph"] == CRITIQUE_PHASE_GRAPH
    assert "cross_tool_execution" in checkpoint["triggers"]


def test_plan_includes_critique_checkpoint_for_cross_tool_task(tmp_path: Path) -> None:
    from calyx.cbo.intent_pipeline.plan import build_plan
    from calyx.cbo.intent_pipeline.registry import save_intent_artifact, save_status

    runtime_dir = tmp_path / "runtime"
    intent_id = "intent-phase3-plan"
    save_intent_artifact(
        intent_id,
        runtime_dir,
        {
            "intent": "Review the repository in scope.",
            "task_type": "repo_readonly_review",
            "scope": {"paths": ["docs/**"]},
            "constraints": {"timeout_seconds": 60},
            "source": "discord",
            "requires_human_approval": False,
            "approval_token": None,
        },
    )
    save_status(intent_id, runtime_dir, {"status": "ready"})

    plan = build_plan(intent_id, runtime_dir)

    assert plan is not None
    assert plan["critique_checkpoint"]["required"] is True
    assert "validate" in plan["critique_checkpoint"]["phase_graph"]


def test_run_work_envelope_denies_missing_required_critique_checkpoint() -> None:
    from calyx.execution.hub_runner import run_work_envelope
    from calyx.kernel.envelope import WorkEnvelope

    repo_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="phase3_runtime_") as tmp:
        runtime_dir = Path(tmp)
        intent_dir = runtime_dir / "cbo" / "intents" / "intent-phase3-deny"
        intent_dir.mkdir(parents=True, exist_ok=True)
        envelope = WorkEnvelope(
            envelope_id="phase3-deny-001",
            intent_id="intent-phase3-deny",
            task_type="repo_readonly_review",
            scope={"paths": ["docs/**"]},
            constraints={},
            ts_utc="2026-03-09T22:00:00Z",
            source="discord",
            requires_human_approval=False,
            approval_token=None,
            risk_tier="low",
        )
        with open(intent_dir / "status.json", "w", encoding="utf-8") as f:
            json.dump({"status": "minted", "work_envelope_hash": envelope.deterministic_hash()}, f)
        prev = os.environ.get("CALYX_RUNTIME_DIR")
        try:
            os.environ["CALYX_RUNTIME_DIR"] = str(runtime_dir)
            ok, err = run_work_envelope(envelope, repo_root=repo_root)
        finally:
            if prev is not None:
                os.environ["CALYX_RUNTIME_DIR"] = prev
            else:
                os.environ.pop("CALYX_RUNTIME_DIR", None)

        assert ok is False
        assert err == "critique_checkpoint_missing_or_invalid"
        critique_path = intent_dir / "critique_checkpoint.json"
        assert critique_path.exists()


def test_run_work_envelope_persists_critique_checkpoint_artifact() -> None:
    from calyx.execution.hub_runner import run_work_envelope
    from calyx.kernel.critique_checkpoint import build_critique_checkpoint
    from calyx.kernel.envelope import WorkEnvelope

    repo_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="phase3_runtime_") as tmp:
        runtime_dir = Path(tmp)
        intent_id = "intent-phase3-pass"
        intent_dir = runtime_dir / "cbo" / "intents" / intent_id
        intent_dir.mkdir(parents=True, exist_ok=True)
        checkpoint = build_critique_checkpoint(task_type="repo_readonly_review", risk_tier="low")
        envelope = WorkEnvelope(
            envelope_id="phase3-pass-001",
            intent_id=intent_id,
            task_type="repo_readonly_review",
            scope={"paths": ["docs/**"]},
            constraints={},
            ts_utc="2026-03-09T22:00:00Z",
            source="discord",
            requires_human_approval=False,
            approval_token=None,
            risk_tier="low",
            critique_checkpoint=checkpoint,
        )
        with open(intent_dir / "status.json", "w", encoding="utf-8") as f:
            json.dump({"status": "minted", "work_envelope_hash": envelope.deterministic_hash()}, f)
        prev = os.environ.get("CALYX_RUNTIME_DIR")
        try:
            os.environ["CALYX_RUNTIME_DIR"] = str(runtime_dir)
            ok, err = run_work_envelope(envelope, repo_root=repo_root)
        finally:
            if prev is not None:
                os.environ["CALYX_RUNTIME_DIR"] = prev
            else:
                os.environ.pop("CALYX_RUNTIME_DIR", None)

        assert ok is True
        assert err is None
        critique_path = intent_dir / "critique_checkpoint.json"
        assert critique_path.exists()
        report = json.loads(critique_path.read_text(encoding="utf-8"))
        assert report["critique_status"] == "passed"
        assert report["validation_status"] == "passed"
        assert report["finalization_allowed"] is True
