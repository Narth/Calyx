from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def _setup_cbo_core(monkeypatch, tmp_path: Path):
    import cbo_hub.cbo_core.app as core_app

    monkeypatch.setenv("CALYX_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setattr(core_app, "_run_sunrise_preflight", lambda: None)
    monkeypatch.setattr(core_app, "_emit", lambda *args, **kwargs: None)
    monkeypatch.setattr(core_app, "_persist_chat_routing_proof", lambda *args, **kwargs: None)
    monkeypatch.setattr(core_app, "_check_integrity_gate", lambda: None)
    monkeypatch.setattr(core_app, "_check_governance_auth", lambda request, req: (True, "ungoverned", False))
    monkeypatch.setattr(core_app, "_check_navigator_pause", lambda: (False, None))
    monkeypatch.setattr(core_app, "_emit_canonical_hash", lambda *args, **kwargs: {"claim_attempted": 0, "claim_verified": 0, "claim_failed": 0, "canonical_receipt_written": False, "equivalence_hash_emitted": False, "response_sha256": "", "equivalence_hash_sha256": "", "canonical_receipt_path": ""})
    monkeypatch.setattr(core_app, "_write_governance_budget", lambda *args, **kwargs: True)
    receipts: list[dict] = []
    monkeypatch.setattr(core_app, "_write_receipt", lambda payload: receipts.append(payload))
    return core_app, receipts, TestClient(core_app.app)


def _proposal_payload() -> dict:
    return {
        "session_id": "workspace-v0",
        "model_role": "local",
        "board_state": {"elements": [{"id": "shape_1", "type": "shape", "shape_kind": "rect", "x": 100, "y": 100, "width": 240, "height": 120, "text": "Cluster"}]},
        "board_state_hash": "hash123",
        "board_snapshot_ref": "runtime/workspace_v0/snapshots/test.png",
        "board_snapshot_sha256": "snap123",
        "discussion_context": [{"role": "user", "text": "Please refine the plan."}],
        "operator_note": "Refine the board.",
    }


def test_workspace_proposal_endpoint_returns_tier_2_safe_refinement(monkeypatch, tmp_path: Path) -> None:
    core_app, receipts, client = _setup_cbo_core(monkeypatch, tmp_path)

    async def _fake_run_model_role(**kwargs):
        return {
            "model_role": "local",
            "model_text": '{"discussion_response":"Add a clearer heading.","operations":[{"type":"add","summary":"Add a heading.","element":{"id":"title_1","type":"text","x":120,"y":70,"width":260,"height":84,"text":"North Star"}}]}',
            "kimi_receipt": None,
            "local_receipt": {"provider": "local", "called": True, "usage": {"input_tokens": 10, "output_tokens": 20}},
            "architect_info": None,
            "openai_info": None,
        }

    monkeypatch.setattr(core_app, "_run_model_role", _fake_run_model_role)

    response = client.post("/workspace/proposal", json=_proposal_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["discussion_response"] == "Add a clearer heading."
    assert payload["operations"][0]["type"] == "add"
    assert payload["intent_schema"]["task_type"] == "layout_reorganize"
    assert payload["proposal_tier"] == 2
    assert payload["tier_label"] == "Safe Refinement"
    assert payload["proposal_kind"] == "mutation_bearing"
    assert payload["provider_used"] == "local"
    assert receipts[-1]["endpoint"] == "/workspace/proposal"
    assert receipts[-1]["structured_valid"] is True
    assert receipts[-1]["proposal_tier"] == 2


def test_workspace_proposal_endpoint_returns_tier_0_observation(monkeypatch, tmp_path: Path) -> None:
    core_app, _, client = _setup_cbo_core(monkeypatch, tmp_path)

    async def _fake_run_model_role(**kwargs):
        return {
            "model_role": "architect",
            "model_text": '{"discussion_response":"Board contains dense freehand strokes with insufficient structure for safe edits.","operations":[]}',
            "kimi_receipt": None,
            "local_receipt": None,
            "architect_info": {"usage": {"input_tokens": 12, "output_tokens": 8}},
            "openai_info": None,
        }

    monkeypatch.setattr(core_app, "_run_model_role", _fake_run_model_role)

    response = client.post("/workspace/proposal", json=_proposal_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["proposal_tier"] == 0
    assert payload["intent_schema"]["task_type"] == "observe"
    assert payload["tier_label"] == "Observation"
    assert payload["proposal_kind"] == "no_op"
    assert payload["quality_signal"] == "insufficient_structure"


def test_workspace_proposal_endpoint_returns_tier_4_creative_reinterpretation(monkeypatch, tmp_path: Path) -> None:
    core_app, _, client = _setup_cbo_core(monkeypatch, tmp_path)

    async def _fake_run_model_role(**kwargs):
        return {
            "model_role": "second_opinion",
            "model_text": '{"discussion_response":"Arrange the shapes into a smiling robot with a nearby CBO badge.","operations":[{"type":"update","summary":"Move the top rectangle into the robot head position.","element_id":"shape_1","patch":{"x":240,"y":120,"width":260,"height":180}}]}',
            "kimi_receipt": {"provider": "kimi", "called": True, "usage": {"input_tokens": 10, "output_tokens": 12}},
            "local_receipt": None,
            "architect_info": None,
            "openai_info": None,
        }

    monkeypatch.setattr(core_app, "_run_model_role", _fake_run_model_role)
    payload = _proposal_payload()
    payload["model_role"] = "second_opinion"
    payload["operator_note"] = "Please propose a smiling robot with CBO beside it."

    response = client.post("/workspace/proposal", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["proposal_tier"] == 4
    assert body["tier_label"] == "Creative Reinterpretation"
    assert body["intent_schema"]["task_type"] == "creative_layout"
    assert body["selected_route"] == "second_opinion"
    assert body["actual_route"] == "second_opinion"
    assert body["provider_used"] == "kimi"


def test_workspace_proposal_endpoint_rejects_wrapped_response(monkeypatch, tmp_path: Path) -> None:
    core_app, receipts, client = _setup_cbo_core(monkeypatch, tmp_path)

    async def _fake_run_model_role(**kwargs):
        return {
            "model_role": "workhorse",
            "model_text": "[CBO online] session=workspace-v0\nYou said: hello\nMessage received.",
            "kimi_receipt": None,
            "local_receipt": None,
            "architect_info": None,
            "openai_info": {"usage": {"total_tokens": 100}},
        }

    monkeypatch.setattr(core_app, "_run_model_role", _fake_run_model_role)

    response = client.post("/workspace/proposal", json=_proposal_payload())

    assert response.status_code == 422
    assert response.json()["detail"]["reason"] == "malformed_model_output"
    assert receipts[-1]["structured_valid"] is False


def test_workspace_proposal_endpoint_surfaces_provider_overload(monkeypatch, tmp_path: Path) -> None:
    core_app, receipts, client = _setup_cbo_core(monkeypatch, tmp_path)

    async def _fake_run_model_role(**kwargs):
        return {
            "model_role": "architect",
            "model_text": '[anthropic] error 529: {"type":"error","error":{"type":"overloaded_error","message":"Overloaded"}}',
            "kimi_receipt": None,
            "local_receipt": None,
            "architect_info": {"usage": {"input_tokens": 12, "output_tokens": 1}},
            "openai_info": None,
        }

    monkeypatch.setattr(core_app, "_run_model_role", _fake_run_model_role)

    response = client.post("/workspace/proposal", json=_proposal_payload() | {"model_role": "architect"})

    assert response.status_code == 503
    assert response.json()["detail"]["reason"] == "provider_overload"
    assert receipts[-1]["structured_valid"] is False
    assert receipts[-1]["failure_reason"] == "provider_overload"


def test_workspace_proposal_endpoint_bypasses_confirmation_fast_path(monkeypatch, tmp_path: Path) -> None:
    core_app, receipts, client = _setup_cbo_core(monkeypatch, tmp_path)
    captured_prompts: list[str] = []

    async def _fake_run_model_role(**kwargs):
        captured_prompts.append(kwargs["prompt"])
        return {
            "model_role": "architect",
            "model_text": '{"discussion_response":"Refined without confirmation fast path.","operations":[]}',
            "kimi_receipt": None,
            "local_receipt": None,
            "architect_info": {"usage": {"input_tokens": 12, "output_tokens": 8}},
            "openai_info": None,
        }

    monkeypatch.setattr(core_app, "_run_model_role", _fake_run_model_role)
    payload = _proposal_payload()
    payload["operator_note"] = "Please confirm receipt before anything else."

    response = client.post("/workspace/proposal", json=payload)

    assert response.status_code == 200
    assert response.json()["discussion_response"] == "Refined without confirmation fast path."
    assert "Do not acknowledge receipt." in captured_prompts[-1]
    assert "Message received." not in response.text


def test_workspace_proposal_prompt_filters_context_and_includes_element_index(monkeypatch, tmp_path: Path) -> None:
    core_app, _, client = _setup_cbo_core(monkeypatch, tmp_path)
    captured_prompts: list[str] = []
    captured_output_tokens: list[int] = []

    async def _fake_run_model_role(**kwargs):
        captured_prompts.append(kwargs["prompt"])
        captured_output_tokens.append(kwargs["max_output_tokens"])
        return {
            "model_role": "local",
            "model_text": '{"discussion_response":"Keep changes grounded in the live ids.","operations":[]}',
            "kimi_receipt": None,
            "local_receipt": {"provider": "local", "called": True},
            "architect_info": None,
            "openai_info": None,
        }

    monkeypatch.setattr(core_app, "_run_model_role", _fake_run_model_role)
    payload = _proposal_payload()
    payload["discussion_context"] = [
        {"role": "user", "message_type": "discussion", "text": "Operator intent: refine the labeled cluster."},
        {"role": "assistant", "message_type": "failure", "text": "Workspace submission did not complete cleanly."},
        {"role": "assistant", "message_type": "proposal", "text": "Previous proposal moved the title card."},
        {"role": "user", "message_type": "submission", "text": "Hybrid board submission sent."},
    ]

    response = client.post("/workspace/proposal", json=payload)

    assert response.status_code == 200
    prompt = captured_prompts[-1]
    assert '"element_index"' in prompt
    assert '"intent_schema"' in prompt
    assert '"id": "shape_1"' in prompt
    assert "Workspace submission did not complete cleanly." not in prompt
    assert "Hybrid board submission sent." not in prompt
    assert "Previous proposal moved the title card." not in prompt
    assert "Local route discipline" in prompt
    assert captured_output_tokens[-1] == 500


def test_workspace_discussion_endpoint_is_board_aware_without_runtime_state(monkeypatch, tmp_path: Path) -> None:
    core_app, receipts, client = _setup_cbo_core(monkeypatch, tmp_path)
    captured_prompts: list[str] = []
    monkeypatch.setattr(core_app, "_load_state_md", lambda: "RUNTIME_STATE_MARKER")

    async def _fake_run_model_role(**kwargs):
        captured_prompts.append(kwargs["prompt"])
        return {
            "model_role": "local",
            "model_text": "The Planning Surface shows one labeled cluster on the canvas.",
            "kimi_receipt": None,
            "local_receipt": {"provider": "local", "called": True},
            "architect_info": None,
            "openai_info": None,
        }

    monkeypatch.setattr(core_app, "_run_model_role", _fake_run_model_role)

    response = client.post(
        "/workspace/discussion",
        json={
            "session_id": "workspace-v0",
            "model_role": "local",
            "user_text": "Assess the current Planning Surface state.",
            "board_state": {"elements": [{"id": "shape_1", "type": "shape", "shape_kind": "rect", "x": 100, "y": 100, "width": 240, "height": 120, "text": "Cluster"}]},
            "board_state_hash": "hash123",
            "discussion_context": [],
            "board_snapshot_ref": "runtime/workspace_v0/snapshots/test.png",
            "active_proposal_summary": {"proposal_id": "proposal_abc123", "tier_label": "Observation"},
        },
    )

    assert response.status_code == 200
    assert response.json()["discussion_response"].startswith("The Planning Surface")
    assert "Workspace context" in captured_prompts[-1]
    assert "RUNTIME_STATE_MARKER" not in captured_prompts[-1]
    assert receipts[-1]["endpoint"] == "/workspace/discussion"
    assert receipts[-1]["runtime_context_injected"] is False


def test_workspace_discussion_endpoint_injects_runtime_state_only_when_requested(monkeypatch, tmp_path: Path) -> None:
    core_app, receipts, client = _setup_cbo_core(monkeypatch, tmp_path)
    captured_prompts: list[str] = []
    monkeypatch.setattr(core_app, "_load_state_md", lambda: "RUNTIME_STATE_MARKER")

    async def _fake_run_model_role(**kwargs):
        captured_prompts.append(kwargs["prompt"])
        return {
            "model_role": "workhorse",
            "model_text": "Workspace board looks stable; Station heartbeat also reports healthy status.",
            "kimi_receipt": None,
            "local_receipt": None,
            "architect_info": None,
            "openai_info": {"usage": {"total_tokens": 100}},
        }

    monkeypatch.setattr(core_app, "_run_model_role", _fake_run_model_role)

    response = client.post(
        "/workspace/discussion",
        json={
            "session_id": "workspace-v0",
            "model_role": "workhorse",
            "user_text": "Please assess the Planning Surface and include current bridge pulse status.",
            "board_state": {"elements": []},
            "board_state_hash": "hash123",
            "discussion_context": [],
        },
    )

    assert response.status_code == 200
    assert "RUNTIME_STATE_MARKER" in captured_prompts[-1]
    assert receipts[-1]["runtime_context_injected"] is True
