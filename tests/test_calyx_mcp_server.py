from __future__ import annotations

from pathlib import Path

import pytest

from calyx.mcp_server import server


def test_scope_contains_only_approved_roots() -> None:
    scope = server.tool_scope({})

    assert scope["mode"] == "read_only"
    assert scope["authority"] == "canonical support"
    assert [root["path"] for root in scope["allowed_roots"]] == [
        str(server.canonicalize(path)) for path in server.DEFAULT_ALLOWED_ROOTS
    ]


def test_out_of_scope_path_is_denied() -> None:
    with pytest.raises(server.McpError) as exc:
        server.tool_stat({"path": "C:/Users"})

    assert exc.value.code == -32001


def test_read_text_is_bounded_to_scoped_text_files(tmp_path: Path) -> None:
    scoped_path = Path("C:/Calyx_Test_Temp/mcp_scope_test.md")
    scoped_path.parent.mkdir(parents=True, exist_ok=True)
    scoped_path.write_text("station mcp validation", encoding="utf-8")

    try:
        result = server.tool_read_text({"path": str(scoped_path), "max_bytes": 8})
    finally:
        scoped_path.unlink(missing_ok=True)

    assert result["text"] == "station "
    assert result["truncated"] is True


def test_initialize_and_tools_list_jsonrpc_handlers() -> None:
    init = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    tools = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

    assert init is not None
    assert init["result"]["serverInfo"]["name"] == "station-calyx-local"
    assert tools is not None
    assert "calyx_scope" in {tool["name"] for tool in tools["result"]["tools"]}


def test_runtime_status_exposes_clarity_surfaces() -> None:
    status = server.tool_runtime_status({})

    assert Path(status["clarity_status"]["path"]).parts[-2:] == (
        "runtime",
        "clarity_status.json",
    )
    assert Path(status["active_objective"]["path"]).parts[-2:] == (
        "runtime",
        "active_objective.json",
    )
    assert isinstance(status["active_objective"]["exists"], bool)
    canonical_surfaces = {
        "source_authority_registry": "CALYX_SOURCE_AUTHORITY_REGISTRY.json",
        "confusion_protocol": "CALYX_CONFUSION_ESCALATION_PROTOCOL.md",
        "decision_ledger": "CALYX_DECISION_LEDGER.md",
    }
    for label, filename in canonical_surfaces.items():
        assert Path(status[label]["path"]).parts[-3:] == (
            "docs",
            "canonical",
            filename,
        )
        assert isinstance(status[label]["exists"], bool)
        assert (Path("docs") / "canonical" / filename).is_file()
