from __future__ import annotations

import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

_PNG_DATA_URL = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jXioAAAAASUVORK5CYII="


def _setup_workspace(monkeypatch, tmp_path: Path):
    import cbo_hub.avatar_web.app as avatar_app

    monkeypatch.setenv("CALYX_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setattr(avatar_app, "_emit", lambda *args, **kwargs: None)
    avatar_app._TASKS = []
    avatar_app._DATA_DIR = tmp_path / "data"
    avatar_app._TASKS_FILE = avatar_app._DATA_DIR / "whiteboard_tasks.json"
    avatar_app._WORKSPACE_BOARD_FILE = avatar_app._DATA_DIR / "workspace_live_board.json"
    avatar_app._WORKSPACE_PROPOSAL_FILE = avatar_app._DATA_DIR / "workspace_proposal_state.json"
    avatar_app._WORKSPACE_DISCUSSION_FILE = avatar_app._DATA_DIR / "workspace_discussion.json"
    avatar_app._WORKSPACE_META_FILE = avatar_app._DATA_DIR / "workspace_meta.json"
    avatar_app._WORKSPACE_UNDO_FILE = avatar_app._DATA_DIR / "workspace_undo_state.json"
    avatar_app._CBO_CORE_RECEIPTS_FILE = tmp_path / "receipts" / "cbo_core.jsonl"
    return avatar_app, TestClient(avatar_app.app)


def _workspace_receipts(tmp_path: Path) -> list[dict]:
    receipts_dir = tmp_path / "runtime" / "receipts"
    payloads: list[dict] = []
    for path in sorted(receipts_dir.glob("avatar_workspace__*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                payloads.append(json.loads(line))
    return payloads


def _governance_receipts(tmp_path: Path) -> list[dict]:
    receipts_dir = tmp_path / "runtime" / "receipts"
    payloads: list[dict] = []
    for path in sorted(receipts_dir.glob("governance__*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                payloads.append(json.loads(line))
    return payloads


def _proposal_reply(
    *,
    discussion_response: str,
    operations: list[dict],
    proposal_tier: int,
    tier_label: str,
    proposal_kind: str = "mutation_bearing",
    quality_signal: str = "grounded",
    selected_route: str = "local",
    actual_route: str | None = None,
    provider_used: str = "local",
) -> dict:
    return {
        "discussion_response": discussion_response,
        "operations": operations,
        "intent_schema": {
            "task_type": "observe" if not operations else "layout_reorganize",
            "preserve_order": True,
            "minimum_gap": 1,
            "preferred_strategy": "direct" if not operations else "greedy",
            "allow_resize": False,
            "target_element_ids": [],
            "axis": "horizontal",
        },
        "proposal_tier": proposal_tier,
        "tier_label": tier_label,
        "tier_rationale": f"{tier_label} rationale.",
        "confidence_summary": f"{tier_label} confidence summary.",
        "proposal_kind": proposal_kind,
        "quality_signal": quality_signal,
        "selected_route": selected_route,
        "actual_route": actual_route or selected_route,
        "receipt_sha256": f"receipt-{tier_label.lower().replace(' ', '-')}",
        "provider_used": provider_used,
    }


def _write_cbo_core_receipt(tmp_path: Path, payload: dict) -> None:
    receipts_file = tmp_path / "receipts" / "cbo_core.jsonl"
    receipts_file.parent.mkdir(parents=True, exist_ok=True)
    receipts_file.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_station_runtime(tmp_path: Path, *, events: list[dict], health: dict | None = None, navigator: dict | None = None, triage: dict | None = None) -> None:
    runtime_dir = tmp_path / "runtime"
    ledger_dir = runtime_dir / "ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    (ledger_dir / "station_events__20260414.jsonl").write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
    (runtime_dir / "station_health.json").write_text(json.dumps(health or {"health": "pass", "entropy": {"tier": "pass"}, "truth_state": "fresh", "health_ts": "2026-04-14T23:11:55Z"}), encoding="utf-8")
    outgoing = tmp_path / "outgoing"
    outgoing.mkdir(parents=True, exist_ok=True)
    (outgoing / "navigator.lock").write_text(json.dumps(navigator or {"interval_status": "hot"}), encoding="utf-8")
    (outgoing / "triage.lock").write_text(json.dumps(triage or {"status": "pass"}), encoding="utf-8")


def _fake_async_client(monkeypatch, avatar_app, reply_factory):
    class _FakeResponse:
        def __init__(self, payload: dict) -> None:
            self._payload = payload
            self.status_code = 200
            self.text = json.dumps(payload)

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict):
            return _FakeResponse(reply_factory(url, json))

    monkeypatch.setattr(avatar_app.httpx, "AsyncClient", _FakeAsyncClient)


def test_workspace_submit_creates_proposal_and_artifacts(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_workspace(monkeypatch, tmp_path)

    def _reply_factory(url: str, payload: dict) -> dict:
        return _proposal_reply(
            discussion_response="Add a title card and keep the live board unchanged until review.",
            proposal_tier=2,
            tier_label="Safe Refinement",
            operations=[
                {
                    "type": "add",
                    "summary": "Introduce a heading for the sketch.",
                    "element": {
                        "id": "title_1",
                        "type": "text",
                        "x": 120,
                        "y": 90,
                        "width": 260,
                        "height": 80,
                        "text": "North Star",
                    },
                }
            ],
        )

    _fake_async_client(monkeypatch, avatar_app, _reply_factory)

    response = client.post(
        "/api/workspace/submit",
        json={
            "board_state": {
                "elements": [
                    {"id": "shape_1", "type": "shape", "shape_kind": "rect", "x": 220, "y": 210, "width": 260, "height": 160, "text": "Current cluster"}
                ]
            },
            "board_snapshot_data_url": _PNG_DATA_URL,
            "operator_note": "Suggest a clearer heading.",
            "model_role": "local",
        },
    )

    assert response.status_code == 200
    proposal = response.json()["proposal_state"]
    assert proposal["proposal_id"].startswith("proposal_")
    assert proposal["validation_result"]["operation_count"] == 1
    assert proposal["proposal_tier"] == 2
    assert proposal["governance_timing"]["proposal_created_at"] == proposal["created_at"]
    assert proposal["governance_timing"]["proposal_displayed_at"] is None
    assert proposal["governance_timing"]["queue_depth_observed"] == 1
    assert Path(proposal["proposal_artifact_path"]).exists()
    assert Path(proposal["board_snapshot_ref"]).exists()
    messages = response.json()["discussion_state"]["messages"]
    assert messages[-2]["message_type"] == "submission"
    assert "Hybrid board submission sent." in messages[-2]["text"]
    assert "Submission: sub_" in messages[-2]["text"]
    assert messages[-1]["message_type"] == "proposal"
    assert "Tier: Safe Refinement" in messages[-1]["text"]
    receipts = _workspace_receipts(tmp_path)
    assert any(receipt["receipt_type"] == "avatar.workspace.proposal.created" for receipt in receipts)


def test_workspace_submit_attaches_route_usage_telemetry_from_cbo_receipt(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_workspace(monkeypatch, tmp_path)
    _write_cbo_core_receipt(
        tmp_path,
        {
            "endpoint": "/workspace/proposal",
            "receipt_sha256": "receipt-safe-refinement",
            "providers_called": ["openai"],
            "usage": {"openai": {"input_tokens": 1200, "output_tokens": 180, "total_tokens": 1380}},
            "cost_estimate_usd": 0.0184,
            "request_latency_ms": 4321,
        },
    )

    def _reply_factory(url: str, payload: dict) -> dict:
        return _proposal_reply(
            discussion_response="Refine the label card.",
            proposal_tier=2,
            tier_label="Safe Refinement",
            operations=[
                {
                    "type": "add",
                    "summary": "Add a cleaner label card.",
                    "element": {"id": "label_1", "type": "text", "x": 90, "y": 120, "width": 220, "height": 72, "text": "CBO"},
                }
            ],
            selected_route="workhorse",
            provider_used="openai",
        )

    _fake_async_client(monkeypatch, avatar_app, _reply_factory)

    response = client.post(
        "/api/workspace/submit",
        json={
            "board_state": {"elements": []},
            "board_snapshot_data_url": _PNG_DATA_URL,
            "operator_note": "Refine the label.",
            "model_role": "workhorse",
        },
    )

    assert response.status_code == 200
    proposal = response.json()["proposal_state"]
    telemetry = proposal["usage_telemetry"]
    assert telemetry["provider"] == "openai"
    assert telemetry["total_tokens"] == 1380
    assert telemetry["cost_estimate_usd"] == 0.0184
    assert telemetry["request_latency_ms"] == 4321
    assert response.json()["meta"]["last_proposal"]["usage_telemetry"]["provider"] == "openai"


def test_workspace_approve_selected_only_applies_chosen_ops_and_supports_undo(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_workspace(monkeypatch, tmp_path)

    def _reply_factory(url: str, payload: dict) -> dict:
        return _proposal_reply(
            discussion_response="One title and one regrouping box are suggested.",
            proposal_tier=3,
            tier_label="Structural Reorganization",
            operations=[
                {
                    "type": "add",
                    "summary": "Add a title card.",
                    "element": {"id": "title_1", "type": "text", "x": 110, "y": 80, "width": 280, "height": 84, "text": "Roadmap"},
                },
                {
                    "type": "add",
                    "summary": "Add a framing box.",
                    "element": {"id": "frame_1", "type": "shape", "shape_kind": "rect", "x": 420, "y": 180, "width": 300, "height": 200, "text": "Frame"},
                },
            ],
        )

    _fake_async_client(monkeypatch, avatar_app, _reply_factory)

    submit = client.post(
        "/api/workspace/submit",
        json={
            "board_state": {"elements": []},
            "board_snapshot_data_url": _PNG_DATA_URL,
            "operator_note": "Propose structure.",
            "model_role": "local",
        },
    )
    proposal = submit.json()["proposal_state"]
    op_ids = [operation["operation_id"] for operation in proposal["operations"]]

    display = client.post("/api/workspace/proposal/displayed", json={"proposal_id": proposal["proposal_id"]})
    assert display.status_code == 200
    displayed_proposal = display.json()["proposal_state"]
    assert displayed_proposal["governance_timing"]["proposal_displayed_at"] == displayed_proposal["displayed_at"]
    assert displayed_proposal["governance_timing"]["time_to_display_seconds"] is not None

    decision = client.post(
        "/api/workspace/proposal/decision",
        json={
            "proposal_id": proposal["proposal_id"],
            "action": "approve_selected",
            "selected_operation_ids": [op_ids[0]],
        },
    )

    assert decision.status_code == 200
    board = decision.json()["board_state"]
    assert [element["id"] for element in board["elements"]] == ["title_1"]
    assert decision.json()["undo_state"]["proposal_id"] == proposal["proposal_id"]
    assert decision.json()["discussion_state"]["messages"][-1]["message_type"] == "decision"
    approval_artifact = json.loads(Path(decision.json()["meta"]["last_decision"]["artifact_path"]).read_text(encoding="utf-8"))
    timing = approval_artifact["governance_timing"]
    assert timing["proposal_created_at"] == proposal["created_at"]
    assert timing["proposal_displayed_at"] == displayed_proposal["displayed_at"]
    assert timing["approval_decision_at"] is not None
    assert timing["execution_started_at"] is not None
    assert timing["execution_completed_at"] is not None
    assert timing["proposal_dwell_seconds"] is not None
    assert timing["display_dwell_seconds"] is not None
    assert timing["execution_duration_ms"] is not None
    assert timing["queue_depth_observed"] == 1
    assert timing["queue_depth_after_decision"] == 0
    gov_receipts = _governance_receipts(tmp_path)
    receipt_types = [item["receipt_type"] for item in gov_receipts]
    assert "proposal_created" in receipt_types
    assert "proposal_displayed" in receipt_types
    assert "execution_attempted" in receipt_types
    assert "approval_granted" in receipt_types
    assert "execution_succeeded" in receipt_types

    undo = client.post("/api/workspace/undo")
    assert undo.status_code == 200
    assert undo.json()["board_state"]["elements"] == []
    assert undo.json()["discussion_state"]["messages"][-1]["text"].startswith("Undo applied.")


def test_workspace_submit_malformed_model_output_writes_failure_and_discussion_survives(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_workspace(monkeypatch, tmp_path)

    def _reply_factory(url: str, payload: dict) -> dict:
        if url.endswith("/workspace/proposal"):
            return {"discussion_response": "broken", "receipt_sha256": "receipt-bad"}
        return {"discussion_response": "Discussion still works after a proposal failure.", "receipt_sha256": "receipt-chat", "provider_used": "local"}

    _fake_async_client(monkeypatch, avatar_app, _reply_factory)

    submit = client.post(
        "/api/workspace/submit",
        json={
            "board_state": {"elements": []},
            "board_snapshot_data_url": _PNG_DATA_URL,
            "operator_note": "Break parsing on purpose.",
            "model_role": "local",
        },
    )

    assert submit.status_code == 422
    artifact_path = Path(submit.json()["detail"]["artifact_path"])
    assert artifact_path.exists()
    discussion_state = client.get("/api/workspace/state").json()["discussion_state"]
    assert discussion_state["messages"][-1]["message_type"] == "failure"
    assert "structured validation failure" in discussion_state["messages"][-1]["text"].lower()

    discussion = client.post("/api/workspace/discussion", json={"user_text": "Can you still answer?", "model_role": "local"})
    assert discussion.status_code == 200
    assert "Discussion still works" in discussion.json()["assistant_message"]["text"]


def test_workspace_submit_surfaces_structured_lane_422_as_malformed(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_workspace(monkeypatch, tmp_path)

    class _FailResponse:
        status_code = 422
        text = '{"detail":{"reason":"malformed_model_output","receipt_sha256":"lane-receipt","raw_model_text_excerpt":"[CBO online]"}}'

        def raise_for_status(self) -> None:
            request = httpx.Request("POST", "http://127.0.0.1:7778/workspace/proposal")
            response = httpx.Response(status_code=422, request=request, text=self.text)
            raise httpx.HTTPStatusError("malformed", request=request, response=response)

        def json(self) -> dict:
            return json.loads(self.text)

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict):
            return _FailResponse()

    monkeypatch.setattr(avatar_app.httpx, "AsyncClient", _FakeAsyncClient)

    submit = client.post(
        "/api/workspace/submit",
        json={
            "board_state": {"elements": []},
            "board_snapshot_data_url": _PNG_DATA_URL,
            "operator_note": "Trigger malformed lane response.",
            "model_role": "local",
        },
    )

    assert submit.status_code == 422
    assert submit.json()["detail"]["reason"] == "malformed_model_output"


def test_workspace_submit_surfaces_provider_overload_distinctly(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_workspace(monkeypatch, tmp_path)

    class _FailResponse:
        status_code = 503
        text = '{"detail":{"reason":"provider_overload","receipt_sha256":"lane-receipt","raw_model_text_excerpt":"[anthropic] error 529: overloaded"}}'

        def raise_for_status(self) -> None:
            request = httpx.Request("POST", "http://127.0.0.1:7778/workspace/proposal")
            response = httpx.Response(status_code=503, request=request, text=self.text)
            raise httpx.HTTPStatusError("overloaded", request=request, response=response)

        def json(self) -> dict:
            return json.loads(self.text)

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict):
            return _FailResponse()

    monkeypatch.setattr(avatar_app.httpx, "AsyncClient", _FakeAsyncClient)

    submit = client.post(
        "/api/workspace/submit",
        json={
            "board_state": {"elements": []},
            "board_snapshot_data_url": _PNG_DATA_URL,
            "operator_note": "Trigger provider overload handling.",
            "model_role": "architect",
        },
    )

    assert submit.status_code == 503
    assert submit.json()["detail"]["reason"] == "provider_overload"
    discussion_state = client.get("/api/workspace/state").json()["discussion_state"]
    assert discussion_state["messages"][-1]["message_type"] == "failure"
    assert "provider overload" in discussion_state["messages"][-1]["text"].lower()


def test_workspace_page_includes_theme_toggle_persistence_hook(monkeypatch, tmp_path: Path) -> None:
    _, client = _setup_workspace(monkeypatch, tmp_path)

    response = client.get("/whiteboard")

    assert response.status_code == 200
    assert 'id="themeSelect"' in response.text
    assert 'calyx.workspace.theme' in response.text
    assert "localStorage.setItem(THEME_KEY" in response.text
    assert '<option value="second_opinion">second opinion</option>' in response.text
    assert 'id="assessBoardBtn"' in response.text
    assert "Route usage:" in response.text
    assert "Geometry:" in response.text
    assert "/api/station/activity" in response.text
    assert 'id="stationAvatar"' in response.text


def test_workspace_discussion_uses_workspace_specific_endpoint(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_workspace(monkeypatch, tmp_path)
    captured_calls: list[tuple[str, dict]] = []

    def _reply_factory(url: str, payload: dict) -> dict:
        captured_calls.append((url, payload))
        if url.endswith("/workspace/discussion"):
            return {"discussion_response": "The Planning Surface shows a single cluster.", "receipt_sha256": "receipt-discussion", "provider_used": "local"}
        raise AssertionError(f"Unexpected URL {url}")

    _fake_async_client(monkeypatch, avatar_app, _reply_factory)

    client.put("/api/workspace/board", json={"board_state": {"elements": [{"id": "shape_1", "type": "shape", "shape_kind": "rect", "x": 100, "y": 100, "width": 120, "height": 80, "text": "Cluster"}]}})
    response = client.post("/api/workspace/discussion", json={"user_text": "Assess the Planning Surface.", "model_role": "local"})

    assert response.status_code == 200
    assert captured_calls[0][0].endswith("/workspace/discussion")
    assert captured_calls[0][1]["board_state"]["elements"][0]["text"] == "Cluster"
    assert "Planning Surface" in response.json()["assistant_message"]["text"]


def test_workspace_submit_filters_proposal_context_before_calling_structured_lane(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_workspace(monkeypatch, tmp_path)
    captured_calls: list[tuple[str, dict]] = []

    avatar_app._workspace_append_discussion_message("user", "Operator discussion one.", source="operator", message_type="discussion")
    avatar_app._workspace_append_discussion_message("assistant", "Previous proposal summary.", source="workspace.submit", message_type="proposal")
    avatar_app._workspace_append_discussion_message("assistant", "Workspace submission did not complete cleanly.", source="workspace.submit", message_type="failure")
    avatar_app._workspace_append_discussion_message("user", "Approve the shape layout after review.", source="operator", message_type="discussion")
    avatar_app._workspace_append_discussion_message("user", "Hybrid board submission sent.", source="workspace.submit", message_type="submission")

    def _reply_factory(url: str, payload: dict) -> dict:
        captured_calls.append((url, payload))
        return _proposal_reply(
            discussion_response="Use the current discussion only.",
            proposal_tier=1,
            tier_label="Advisory Suggestion",
            proposal_kind="advisory_only",
            quality_signal="advisory_only",
            operations=[],
        )

    _fake_async_client(monkeypatch, avatar_app, _reply_factory)

    response = client.post(
        "/api/workspace/submit",
        json={
            "board_state": {"elements": [{"id": "shape_1", "type": "shape", "shape_kind": "rect", "x": 100, "y": 100, "width": 120, "height": 80, "text": "Cluster"}]},
            "board_snapshot_data_url": _PNG_DATA_URL,
            "operator_note": "Refine using only relevant context.",
            "model_role": "local",
        },
    )

    assert response.status_code == 200
    proposal_payload = captured_calls[0][1]
    context = proposal_payload["discussion_context"]
    assert all(message["message_type"] == "discussion" for message in context)
    assert all(message["role"] == "user" for message in context)
    assert all("did not complete cleanly" not in message["text"].lower() for message in context)
    assert all("Hybrid board submission sent." not in message["text"] for message in context)
    assert all("Previous proposal summary." not in message["text"] for message in context)


def test_workspace_assess_routes_through_structured_lane_without_creating_proposal(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_workspace(monkeypatch, tmp_path)
    captured_calls: list[tuple[str, dict]] = []

    def _reply_factory(url: str, payload: dict) -> dict:
        captured_calls.append((url, payload))
        if url.endswith("/workspace/proposal"):
            return _proposal_reply(
                discussion_response="The Planning Surface shows a stable head-and-shoulders silhouette with room to refine the label box.",
                proposal_tier=1,
                tier_label="Advisory Suggestion",
                proposal_kind="advisory_only",
                quality_signal="advisory_only",
                operations=[],
                selected_route="architect",
                provider_used="anthropic",
            )
        raise AssertionError(f"Unexpected URL {url}")

    _fake_async_client(monkeypatch, avatar_app, _reply_factory)

    client.put("/api/workspace/board", json={"board_state": {"elements": [{"id": "shape_1", "type": "shape", "shape_kind": "rect", "x": 100, "y": 100, "width": 120, "height": 80, "text": "Robot"}]}})
    response = client.post("/api/workspace/assess", json={"operator_note": "Assess the current robot silhouette.", "model_role": "architect"})

    assert response.status_code == 200
    assert captured_calls[0][0].endswith("/workspace/proposal")
    assert captured_calls[0][1]["assessment_only"] is True
    state = client.get("/api/workspace/state").json()
    assert state["proposal_state"] is None
    assert state["discussion_state"]["messages"][-1]["message_type"] == "assessment"
    assert "Advisory Suggestion" in state["discussion_state"]["messages"][-1]["text"]


def test_station_activity_api_surfaces_avatar_active_tasks_and_recent_events(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_workspace(monkeypatch, tmp_path)
    monkeypatch.setattr(avatar_app, "_station_process_activity", lambda **kwargs: [])
    _write_station_runtime(
        tmp_path,
        events=[
            {
                "ts_utc": "2026-04-14T23:04:11Z",
                "component": "calyx_gateway",
                "event": "system.task.triggered",
                "level": "INFO",
                "msg": "System task heartbeat_push started",
                "corr_id": "task-1",
                "causal_envelope": {"task_corr_id": "task-1", "task_name": "heartbeat_push"},
                "data": {"task_name": "heartbeat_push"},
            },
            {
                "ts_utc": "2026-04-14T23:04:13Z",
                "component": "heartbeat",
                "event": "heartbeat.tick",
                "level": "INFO",
                "msg": "heartbeat tick",
                "data": {"checks": "dev_harness=ok,cbo_core=ok"},
            },
        ],
    )

    response = client.get("/api/station/activity?limit=12")

    assert response.status_code == 200
    body = response.json()
    assert body["station"]["avatar_emoji"] == "⚙️"
    assert body["station"]["active_task_count"] == 1
    assert body["station"]["active_process_count"] == 0
    assert body["active_tasks"][0]["task_name"] == "heartbeat_push"
    assert body["recent_events"][0]["event"] == "heartbeat.tick"


def test_station_activity_api_surfaces_active_processes_and_recent_artifacts(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_workspace(monkeypatch, tmp_path)
    monkeypatch.setattr(
        avatar_app,
        "_station_process_activity",
        lambda **kwargs: [
            {
                "pid": 4242,
                "component": "audit",
                "task_name": "Daily 24H Review generator",
                "started_at": "2026-04-14T23:05:00Z",
                "status": "running",
                "excerpt": "Active process Daily 24H Review generator",
            }
        ],
    )
    _write_station_runtime(tmp_path, events=[])
    audit_dir = tmp_path / "runtime" / "receipts" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "daily_24h_review__20260414_230600.json").write_text(
        json.dumps(
            {
                "ts_utc": "2026-04-14T23:06:00Z",
                "schema": "station.daily_24h_review.v1",
                "generator": {"script": "Scripts\\generate_daily_24h_review.py"},
            }
        ),
        encoding="utf-8",
    )

    response = client.get("/api/station/activity?limit=12")

    assert response.status_code == 200
    body = response.json()
    assert body["station"]["avatar_emoji"] == "⚙️"
    assert body["station"]["active_process_count"] == 1
    assert body["active_processes"][0]["task_name"] == "Daily 24H Review generator"
    assert any(item["event"] == "artifact.updated" for item in body["recent_events"])


def test_station_activity_groups_duplicate_process_variants_by_role(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_workspace(monkeypatch, tmp_path)
    monkeypatch.setattr(avatar_app, "_station_recent_events", lambda **kwargs: [])
    monkeypatch.setattr(avatar_app, "_station_recent_artifact_events", lambda **kwargs: [])
    monkeypatch.setattr(
        avatar_app,
        "_station_process_cache_rows",
        lambda definitions: [
            {"pid": 100, "component": "cbo", "task_name": "CBO Bridge Overseer", "started_at": "2026-04-14T23:05:00Z", "status": "running", "excerpt": "Active process CBO Bridge Overseer", "variant": "venv_cbohub311"},
            {"pid": 101, "component": "cbo", "task_name": "CBO Bridge Overseer", "started_at": "2026-04-14T23:05:30Z", "status": "running", "excerpt": "Active process CBO Bridge Overseer", "variant": "python311"},
            {"pid": 102, "component": "avatar", "task_name": "CLI Avatar", "started_at": "2026-04-14T23:06:00Z", "status": "running", "excerpt": "Active process CLI Avatar", "variant": "venv_cbohub311"},
        ],
    )

    response = client.get("/api/station/activity?limit=12")

    assert response.status_code == 200
    body = response.json()
    assert body["station"]["active_process_count"] == 2
    grouped = {item["task_name"]: item for item in body["active_processes"]}
    assert grouped["CBO Bridge Overseer"]["variant_count"] == 2
    assert grouped["CBO Bridge Overseer"]["variants"] == ["venv_cbohub311", "python311"]
    assert grouped["CBO Bridge Overseer"]["pids"] == [100, 101]


def test_workspace_invalid_geometry_proposal_is_visible_but_not_approvable(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_workspace(monkeypatch, tmp_path)

    def _reply_factory(url: str, payload: dict) -> dict:
        return _proposal_reply(
            discussion_response="Add an oversized banner card.",
            proposal_tier=3,
            tier_label="Structural Reorganization",
            operations=[
                {
                    "type": "add",
                    "summary": "Add an oversized card.",
                    "element": {"id": "banner_1", "type": "shape", "shape_kind": "rect", "x": 0, "y": 0, "width": 2200, "height": 200, "text": "Banner"},
                }
            ],
            selected_route="local",
            provider_used="local",
        )

    _fake_async_client(monkeypatch, avatar_app, _reply_factory)

    submit = client.post(
        "/api/workspace/submit",
        json={
            "board_state": {"elements": []},
            "board_snapshot_data_url": _PNG_DATA_URL,
            "operator_note": "Try an oversized banner.",
            "model_role": "local",
        },
    )

    assert submit.status_code == 200
    proposal = submit.json()["proposal_state"]
    assert proposal["geometry_status"] == "invalid"
    assert proposal["validation_result"]["geometry"]["status"] == "invalid"

    display = client.post("/api/workspace/proposal/displayed", json={"proposal_id": proposal["proposal_id"]})
    assert display.status_code == 200

    decision = client.post(
        "/api/workspace/proposal/decision",
        json={"proposal_id": proposal["proposal_id"], "action": "approve_all"},
    )
    assert decision.status_code == 409
    assert decision.json()["detail"] == "proposal_not_certified"


def test_workspace_reject_records_decision_timing_without_execution(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_workspace(monkeypatch, tmp_path)

    def _reply_factory(url: str, payload: dict) -> dict:
        return _proposal_reply(
            discussion_response="Decline the proposed frame.",
            proposal_tier=2,
            tier_label="Safe Refinement",
            operations=[
                {
                    "type": "add",
                    "summary": "Add a frame.",
                    "element": {"id": "frame_1", "type": "shape", "shape_kind": "rect", "x": 100, "y": 100, "width": 200, "height": 120, "text": "Frame"},
                }
            ],
        )

    _fake_async_client(monkeypatch, avatar_app, _reply_factory)

    submit = client.post(
        "/api/workspace/submit",
        json={
            "board_state": {"elements": []},
            "board_snapshot_data_url": _PNG_DATA_URL,
            "operator_note": "Reject this frame proposal.",
            "model_role": "local",
        },
    )
    proposal = submit.json()["proposal_state"]
    client.post("/api/workspace/proposal/displayed", json={"proposal_id": proposal["proposal_id"]})

    decision = client.post(
        "/api/workspace/proposal/decision",
        json={"proposal_id": proposal["proposal_id"], "action": "reject_all", "reason": "operator_rejected"},
    )

    assert decision.status_code == 200
    artifact = json.loads(Path(decision.json()["meta"]["last_decision"]["artifact_path"]).read_text(encoding="utf-8"))
    timing = artifact["governance_timing"]
    assert timing["approval_decision_at"] is not None
    assert timing["execution_started_at"] is None
    assert timing["execution_completed_at"] is None
    assert timing["queue_depth_observed"] == 1
    assert timing["queue_depth_after_decision"] == 0
    gov_receipts = _governance_receipts(tmp_path)
    assert any(item["receipt_type"] == "approval_rejected" for item in gov_receipts)
