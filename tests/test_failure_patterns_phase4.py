from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path

from starlette.requests import Request


def test_attach_failure_pattern_metadata_adds_doc_path() -> None:
    from calyx.kernel.failure_patterns import attach_failure_pattern_metadata

    payload = attach_failure_pattern_metadata(
        {"status": "denied"},
        signals=["critique_checkpoint_missing_or_invalid"],
    )
    assert payload["failure_pattern_ids"] == ["premature_execution"]
    assert payload["failure_patterns_doc"] == "runtime/docs/KNOWN_FAILURE_PATTERNS.md"


def test_attach_failure_pattern_metadata_tags_scope_drift() -> None:
    from calyx.kernel.failure_patterns import attach_failure_pattern_metadata

    payload = attach_failure_pattern_metadata(
        {"status": "pending_clarification"},
        signals=["phase1_intake_card_incomplete"],
    )
    assert "scope_drift" in payload["failure_pattern_ids"]
    assert payload["failure_patterns_doc"] == "runtime/docs/KNOWN_FAILURE_PATTERNS.md"


def test_chat_receipt_tags_hallucinated_context_when_source_target_unresolved(monkeypatch) -> None:
    import cbo_hub.cbo_core.app as core_app

    receipts: list[dict] = []

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
    monkeypatch.setattr(core_app, "_persist_chat_routing_proof", lambda request, proof: None)

    request = Request({"type": "http", "method": "POST", "path": "/chat", "headers": []})
    req = core_app.ChatReq(
        user_text="Search the repo for Calyx receipts and summarize them.",
        session_id="phase4-test",
        mode="dev",
        allow_tools=True,
        model_role="architect",
    )

    asyncio.run(core_app.chat(req, request))

    assert receipts
    assert "hallucinated_context" in receipts[-1]["failure_pattern_ids"]
    assert "tool_misuse" in receipts[-1]["failure_pattern_ids"]


def test_hub_runner_denial_receipt_tags_premature_execution() -> None:
    from calyx.execution.hub_runner import run_work_envelope
    from calyx.kernel.envelope import WorkEnvelope

    repo_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="phase4_runtime_") as tmp:
        runtime_dir = Path(tmp)
        intent_dir = runtime_dir / "cbo" / "intents" / "intent-phase4-deny"
        intent_dir.mkdir(parents=True, exist_ok=True)
        envelope = WorkEnvelope(
            envelope_id="phase4-deny-001",
            intent_id="intent-phase4-deny",
            task_type="repo_readonly_review",
            scope={"paths": ["docs/**"]},
            constraints={},
            ts_utc="2026-03-09T23:00:00Z",
            source="discord",
            requires_human_approval=False,
            approval_token=None,
            risk_tier="low",
        )
        with open(intent_dir / "status.json", "w", encoding="utf-8") as f:
            json.dump({"status": "minted", "work_envelope_hash": envelope.deterministic_hash()}, f)
        prev_runtime = os.environ.get("CALYX_RUNTIME_DIR")
        try:
            os.environ["CALYX_RUNTIME_DIR"] = str(runtime_dir)
            ok, err = run_work_envelope(envelope, repo_root=repo_root)
        finally:
            if prev_runtime is not None:
                os.environ["CALYX_RUNTIME_DIR"] = prev_runtime
            else:
                os.environ.pop("CALYX_RUNTIME_DIR", None)

        assert ok is False
        assert err == "critique_checkpoint_missing_or_invalid"
        receipt_path = sorted((runtime_dir / "receipts").glob("hub_runner__*.jsonl"))[-1]
        receipt_lines = receipt_path.read_text(encoding="utf-8").strip().splitlines()
        receipt = json.loads(receipt_lines[-1])
        assert "premature_execution" in receipt["failure_pattern_ids"]
