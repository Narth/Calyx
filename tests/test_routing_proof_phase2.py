from __future__ import annotations

import asyncio
from pathlib import Path

from starlette.requests import Request


def test_build_and_validate_routing_proof() -> None:
    from calyx.kernel.routing_proof import build_routing_proof, validate_routing_proof

    proof = build_routing_proof(
        selected_tool_path="STATE_FAST_PATH",
        rejected_alternatives=["LLM_TOOL_ROUTER"],
        source_target_required=["STATE.md"],
        resolved_source_targets=["STATE.md"],
        intent="INTENT_HEARTBEAT",
        entry_point="browser",
        rationale="Heartbeat uses STATE.",
        proof_id="proof-1",
    )
    valid, missing = validate_routing_proof(proof)
    assert valid
    assert missing == []
    assert proof["SELECTED_TOOL_PATH"] == "STATE_FAST_PATH"


def test_source_targets_satisfied_requires_resolution() -> None:
    from calyx.kernel.routing_proof import build_routing_proof, source_targets_satisfied

    proof = build_routing_proof(
        selected_tool_path="LLM_TOOL_ROUTER",
        rejected_alternatives=["DIRECT_UNGROUNDED_REPLY"],
        source_target_required=["repo_search_hits"],
        resolved_source_targets=[],
    )
    assert source_targets_satisfied(proof) is False
    proof["RESOLVED_SOURCE_TARGETS"] = ["repo_search_hits"]
    assert source_targets_satisfied(proof) is True


def test_append_resolved_source_targets_deduplicates() -> None:
    from calyx.kernel.routing_proof import append_resolved_source_targets, build_routing_proof

    proof = build_routing_proof(
        selected_tool_path="LLM_TOOL_ROUTER",
        rejected_alternatives=["DIRECT_UNGROUNDED_REPLY"],
        source_target_required=["repo_search_hits"],
        resolved_source_targets=[],
    )
    proof = append_resolved_source_targets(proof, ["repo_search_hits", "repo_search_hits"])
    assert proof["RESOLVED_SOURCE_TARGETS"] == ["repo_search_hits"]


def test_intent_pipeline_plan_includes_routing_proof(tmp_path: Path) -> None:
    from calyx.cbo.intent_pipeline.plan import build_plan
    from calyx.cbo.intent_pipeline.registry import save_intent_artifact, save_status

    runtime_dir = tmp_path / "runtime"
    intent_id = "intent-phase2-plan"
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
    assert "routing_proof" in plan
    assert plan["routing_proof"]["SELECTED_TOOL_PATH"] == "INTENT_PIPELINE_PLAN_ROUTE"


def test_normalize_routing_proof_uses_intent_artifact_and_compound_targets() -> None:
    from calyx.cbo.intent_pipeline.intake_card import merge_intake_card
    from calyx.cbo.intent_pipeline.routing_proof import normalize_routing_proof

    artifact = merge_intake_card(
        {
            "intent": "Search the Station repo for FAILURE EVENT and tell me which file defines emit.",
            "task_type": "doc_update",
            "evidence_requirements": {"checks": ["repo_search"], "receipt_types": ["doc_changes.jsonl"]},
        }
    )
    proof = normalize_routing_proof(artifact)
    assert proof["SOURCE_TARGET_REQUIRED"][0] == "intent_artifact"
    assert "checks:repo_search" not in proof["SOURCE_TARGET_REQUIRED"]
    assert "receipt_types:doc_changes.jsonl" not in proof["SOURCE_TARGET_REQUIRED"]
    assert any(target.startswith("search_target:") for target in proof["SOURCE_TARGET_REQUIRED"])
    assert any(target.startswith("definition_target:") for target in proof["SOURCE_TARGET_REQUIRED"])


def test_chat_denies_ungrounded_synthesis_when_source_target_unresolved(monkeypatch) -> None:
    import cbo_hub.cbo_core.app as core_app

    receipts: list[dict] = []
    persisted_proofs: list[dict] = []

    async def fake_call_anthropic(prompt: str, max_output_tokens: int = 900):
        return (
            "This is a synthesized answer with no grounded repo target and no supported source citation.",
            {"usage": {}},
        )

    async def fake_call_dev_harness(path: str, payload: dict):
        if path == "/repo/search":
            return {"hits": [], "sha256": "repo-search-sha"}
        if path == "/repo/list":
            return {"entries": [], "sha256": "repo-list-sha"}
        raise AssertionError(path)

    monkeypatch.setattr(core_app, "_call_anthropic", fake_call_anthropic)
    monkeypatch.setattr(core_app, "_call_dev_harness", fake_call_dev_harness)
    monkeypatch.setattr(core_app, "_check_integrity_gate", lambda: None)
    monkeypatch.setattr(core_app, "_check_navigator_pause", lambda: (False, ""))
    monkeypatch.setattr(core_app, "_emit", lambda *args, **kwargs: None)
    monkeypatch.setattr(core_app, "_write_receipt", lambda receipt: receipts.append(receipt))
    monkeypatch.setattr(core_app, "_emit_canonical_hash", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(core_app, "_write_governance_budget", lambda *args, **kwargs: None)
    monkeypatch.setattr(core_app, "_persist_chat_routing_proof", lambda request, proof: persisted_proofs.append(dict(proof)))

    request = Request({"type": "http", "method": "POST", "path": "/chat", "headers": []})
    req = core_app.ChatReq(
        user_text="Search the repo for Calyx receipts and summarize them.",
        session_id="phase2-test",
        mode="dev",
        allow_tools=True,
        model_role="architect",
    )

    response = asyncio.run(core_app.chat(req, request))

    assert "No grounded source target available for synthesis." in response.reply_text
    assert receipts
    assert receipts[-1]["routing_proof"]["SOURCE_TARGET_REQUIRED"] == ["repo_search_hits"]
    assert receipts[-1]["routing_proof"]["RESOLVED_SOURCE_TARGETS"] == []
    assert len(persisted_proofs) >= 2
