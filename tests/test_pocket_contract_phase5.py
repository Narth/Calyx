from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient


def _setup_avatar_runtime(monkeypatch, tmp_path: Path):
    import cbo_hub.avatar_web.app as avatar_app

    monkeypatch.setenv("CALYX_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setattr(avatar_app, "_emit", lambda *args, **kwargs: None)
    avatar_app._TASKS = []
    avatar_app._DATA_DIR = tmp_path / "data"
    avatar_app._TASKS_FILE = avatar_app._DATA_DIR / "whiteboard_tasks.json"
    return avatar_app, TestClient(avatar_app.app)


def _read_avatar_receipts(tmp_path: Path) -> list[dict]:
    receipts_dir = tmp_path / "runtime" / "receipts"
    payloads: list[dict] = []
    for path in sorted(receipts_dir.glob("avatar_whiteboard__*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                payloads.append(json.loads(line))
    return payloads


def _contract_payload(*, max_depth: int = 0, tools: list[str] | None = None) -> dict:
    return {
        "ALLOWED_CONTEXT": ["docs/planning/WHITEBOARD_ROOMS_DECKS.md"],
        "ALLOWED_TOOLS": tools or ["repo_search", "repo_read"],
        "EXIT_CRITERIA": ["Return one bounded result snippet"],
        "MAX_RECURSION_DEPTH": max_depth,
    }


def test_add_task_requires_complete_pocket_contract(monkeypatch, tmp_path: Path) -> None:
    _, client = _setup_avatar_runtime(monkeypatch, tmp_path)

    response = client.post("/api/whiteboard/tasks", json={"title": "Review whiteboard pocket"})

    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "pocket_contract_incomplete"
    receipts = _read_avatar_receipts(tmp_path)
    assert receipts[-1]["reason"] == "pocket_contract_incomplete"
    assert "scope_drift" in receipts[-1]["failure_pattern_ids"]


def test_add_task_persists_normalized_pocket_contract(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_avatar_runtime(monkeypatch, tmp_path)

    response = client.post(
        "/api/whiteboard/tasks",
        json={
            "title": "Audit routing proof pocket",
            "pocket_contract": _contract_payload(max_depth=0),
        },
    )

    assert response.status_code == 200
    task = response.json()
    assert task["pocket_contract_status"] == "ready"
    assert task["pocket_contract"]["OBJECTIVE"] == "Audit routing proof pocket"
    persisted = json.loads(avatar_app._TASKS_FILE.read_text(encoding="utf-8"))
    assert persisted[0]["pocket_contract"]["MAX_RECURSION_DEPTH"] == 0


def test_run_task_denies_when_recursion_depth_exceeds_contract(monkeypatch, tmp_path: Path) -> None:
    _, client = _setup_avatar_runtime(monkeypatch, tmp_path)

    created = client.post(
        "/api/whiteboard/tasks",
        json={"title": "Depth-bound pocket", "pocket_contract": _contract_payload(max_depth=0)},
    ).json()

    response = client.post(
        f"/api/whiteboard/tasks/{created['id']}/run",
        json={"model_role": "local", "allow_tools": True, "session_id": "whiteboard", "recursion_depth": 1},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["reason"] == "recursion_depth_exceeded"
    receipts = _read_avatar_receipts(tmp_path)
    assert receipts[-1]["reason"] == "recursion_depth_exceeded"
    assert "recursion_loops" in receipts[-1]["failure_pattern_ids"]


def test_run_task_embeds_contract_and_disables_tools_for_reason_only(monkeypatch, tmp_path: Path) -> None:
    avatar_app, client = _setup_avatar_runtime(monkeypatch, tmp_path)
    captured_posts: list[dict] = []

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"reply_text": "Bounded pocket reply."}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict):
            captured_posts.append({"url": url, "json": json})
            return _FakeResponse()

    monkeypatch.setattr(avatar_app.httpx, "AsyncClient", _FakeAsyncClient)
    created = client.post(
        "/api/whiteboard/tasks",
        json={
            "title": "Reason-only pocket",
            "pocket_contract": _contract_payload(max_depth=0, tools=["reason_only"]),
        },
    ).json()

    response = client.post(
        f"/api/whiteboard/tasks/{created['id']}/run",
        json={"model_role": "local", "allow_tools": True, "session_id": "whiteboard", "recursion_depth": 0},
    )

    assert response.status_code == 200
    assert captured_posts
    forwarded = captured_posts[-1]["json"]
    assert forwarded["allow_tools"] is False
    assert "Whiteboard pocket contract:" in forwarded["user_text"]
    assert "MAX_RECURSION_DEPTH: 0" in forwarded["user_text"]
