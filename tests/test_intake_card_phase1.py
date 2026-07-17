from __future__ import annotations

from pathlib import Path


def test_normalize_intake_card_marks_compound_query_boundaries() -> None:
    from calyx.cbo.intent_pipeline.intake_card import normalize_intake_card

    artifact = {
        "intent": "Search the Station repo for FAILURE EVENT and tell me which file defines the emit function.",
        "task_type": "doc_update",
        "evidence_requirements": {"checks": ["repo_search"]},
    }
    card = normalize_intake_card(artifact)
    assert card["USE_CASE"]
    assert "search_target:FAILURE EVENT" in card["TRIGGERS"]
    assert "definition_target:the emit function" in card["TRIGGERS"]
    assert "do_not_collapse_search_target_into_definition_target" in card["ANTI_TRIGGERS"]
    assert any("FAILURE EVENT" in step for step in card["ORDERED_STEPS"])


def test_mark_ready_persists_complete_intake_card(tmp_path: Path) -> None:
    from calyx.cbo.intent_pipeline.clarify import mark_ready
    from calyx.cbo.intent_pipeline.registry import load_intent_artifact, load_status, save_intent_artifact

    runtime_dir = tmp_path / "runtime"
    intent_id = "intent-phase1-ready"
    save_intent_artifact(
        intent_id,
        runtime_dir,
        {
            "intent": "Review docs in scope.",
            "task_type": "doc_update",
            "scope": {"paths": ["docs/**"]},
            "constraints": {"timeout_seconds": 30},
        },
    )

    mark_ready(intent_id, runtime_dir)
    status = load_status(intent_id, runtime_dir)
    artifact = load_intent_artifact(intent_id, runtime_dir)

    assert status is not None
    assert status["status"] == "ready"
    assert status["intake_card_status"] == "complete"
    assert artifact is not None
    assert "intake_card" in artifact
    assert artifact["intake_card"]["EXPECTED_RESULT"]


def test_build_plan_includes_intake_card(tmp_path: Path) -> None:
    from calyx.cbo.intent_pipeline.plan import build_plan
    from calyx.cbo.intent_pipeline.registry import save_intent_artifact, save_status

    runtime_dir = tmp_path / "runtime"
    intent_id = "intent-phase1-plan"
    save_intent_artifact(
        intent_id,
        runtime_dir,
        {
            "intent": "Search the repo for failure event format.",
            "task_type": "doc_update",
            "scope": {"paths": ["docs/**"]},
            "constraints": {"timeout_seconds": 60},
            "source": "discord",
            "requires_human_approval": False,
            "approval_token": None,
            "evidence_requirements": {"checks": ["repo_search"], "receipt_types": ["doc_changes.jsonl"]},
        },
    )
    save_status(intent_id, runtime_dir, {"status": "ready"})

    plan = build_plan(intent_id, runtime_dir)
    assert plan is not None
    assert "intake_card" in plan
    assert plan["intake_card"]["USE_CASE"]
    assert plan["intake_card"]["REQUIRED_EVIDENCE"]
