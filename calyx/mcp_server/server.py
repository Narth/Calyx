from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO


PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "station-calyx-local"
SERVER_VERSION = "0.1.0"
MAX_READ_BYTES = 1_000_000
MAX_LIST_ENTRIES = 500

DEFAULT_ALLOWED_ROOTS = (
    Path("C:/Calyx_Terminal"),
    Path("C:/Calyx_Test_Temp"),
    Path("C:/Calyx_Parking"),
    Path("C:/Calyx_Federation_Inbox"),
    Path("D:/Calyx_Data"),
)

TEXT_SUFFIXES = {
    ".bat",
    ".cfg",
    ".cmd",
    ".csv",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".ps1",
    ".py",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
}


class McpError(Exception):
    def __init__(self, code: int, message: str, data: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


@dataclass(frozen=True)
class AllowedRoot:
    name: str
    path: Path
    exists: bool


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def canonicalize(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def allowed_roots() -> list[AllowedRoot]:
    roots: list[AllowedRoot] = []
    for path in DEFAULT_ALLOWED_ROOTS:
        resolved = canonicalize(path)
        roots.append(AllowedRoot(name=resolved.name, path=resolved, exists=resolved.exists()))
    return roots


def is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_scoped_path(path_value: str | None) -> Path:
    if not path_value:
        raise McpError(-32602, "path is required")
    candidate = canonicalize(Path(path_value))
    for root in allowed_roots():
        if is_relative_to(candidate, root.path):
            return candidate
    raise McpError(
        -32001,
        "path outside approved Station Calyx MCP scope",
        {
            "path": str(candidate),
            "allowed_roots": [str(root.path) for root in allowed_roots()],
        },
    )


def relative_display(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return str(path)
    return "." if str(rel) == "." else str(rel).replace("\\", "/")


def root_for(path: Path) -> AllowedRoot | None:
    for root in allowed_roots():
        if is_relative_to(path, root.path):
            return root
    return None


def write_receipt(event: str, payload: dict[str, Any]) -> None:
    receipt_dir = repo_root() / "runtime" / "receipts" / "mcp"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    receipt_path = receipt_dir / f"{event}__{stamp}.json"
    body = {
        "schema": "station.mcp_server_receipt.v1",
        "ts_utc": utc_now(),
        "event": event,
        "server": SERVER_NAME,
        "scope": [str(root.path) for root in allowed_roots()],
        **payload,
    }
    receipt_path.write_text(json.dumps(body, indent=2), encoding="utf-8")


def read_json_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    try:
        return {"exists": True, "path": str(path), "value": json.loads(path.read_text(encoding="utf-8"))}
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(path), "error": f"invalid json: {exc}"}


def tool_scope(_: dict[str, Any]) -> dict[str, Any]:
    return {
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
        "mode": "read_only",
        "authority": "canonical support",
        "authority_note": "Local stdio MCP access is bounded to approved workstation folders and is not runtime continuity authority.",
        "allowed_roots": [
            {"name": root.name, "path": str(root.path), "exists": root.exists}
            for root in allowed_roots()
        ],
        "limits": {"max_read_bytes": MAX_READ_BYTES, "max_list_entries": MAX_LIST_ENTRIES},
    }


def tool_stat(arguments: dict[str, Any]) -> dict[str, Any]:
    path = resolve_scoped_path(arguments.get("path"))
    root = root_for(path)
    if root is None:
        raise McpError(-32001, "path outside approved Station Calyx MCP scope")
    exists = path.exists()
    stat = path.stat() if exists else None
    return {
        "path": str(path),
        "root": str(root.path),
        "relative_path": relative_display(path, root.path),
        "exists": exists,
        "kind": "directory" if exists and path.is_dir() else "file" if exists and path.is_file() else "missing",
        "size_bytes": stat.st_size if stat else None,
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat().replace("+00:00", "Z") if stat else None,
    }


def tool_list(arguments: dict[str, Any]) -> dict[str, Any]:
    path = resolve_scoped_path(arguments.get("path"))
    if not path.exists():
        raise McpError(-32002, "path does not exist", {"path": str(path)})
    if not path.is_dir():
        raise McpError(-32602, "path must be a directory", {"path": str(path)})
    root = root_for(path)
    if root is None:
        raise McpError(-32001, "path outside approved Station Calyx MCP scope")
    entries = []
    for index, child in enumerate(sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))):
        if index >= MAX_LIST_ENTRIES:
            break
        stat = child.stat()
        entries.append(
            {
                "name": child.name,
                "path": str(child),
                "relative_path": relative_display(child, root.path),
                "kind": "directory" if child.is_dir() else "file",
                "size_bytes": stat.st_size,
                "modified_utc": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat().replace("+00:00", "Z"),
            }
        )
    return {
        "path": str(path),
        "root": str(root.path),
        "relative_path": relative_display(path, root.path),
        "entry_count": len(entries),
        "truncated": len(entries) >= MAX_LIST_ENTRIES,
        "entries": entries,
    }


def tool_read_text(arguments: dict[str, Any]) -> dict[str, Any]:
    path = resolve_scoped_path(arguments.get("path"))
    if not path.exists():
        raise McpError(-32002, "path does not exist", {"path": str(path)})
    if not path.is_file():
        raise McpError(-32602, "path must be a file", {"path": str(path)})
    if path.suffix.lower() not in TEXT_SUFFIXES:
        raise McpError(-32003, "refusing to read file without approved text suffix", {"path": str(path)})
    stat = path.stat()
    limit = int(arguments.get("max_bytes") or MAX_READ_BYTES)
    limit = max(1, min(limit, MAX_READ_BYTES))
    read_size = min(stat.st_size, limit)
    raw = path.read_bytes()[:read_size]
    text = raw.decode("utf-8", errors="replace")
    root = root_for(path)
    if root is None:
        raise McpError(-32001, "path outside approved Station Calyx MCP scope")
    return {
        "path": str(path),
        "root": str(root.path),
        "relative_path": relative_display(path, root.path),
        "size_bytes": stat.st_size,
        "bytes_returned": len(raw),
        "truncated": stat.st_size > len(raw),
        "text": text,
    }


def tool_runtime_status(_: dict[str, Any]) -> dict[str, Any]:
    root = canonicalize(Path("C:/Calyx_Terminal"))
    state_path = root / "STATE.md"
    topology_path = root / "runtime" / "runtime_topology_snapshot.json"
    failure_path = root / "runtime" / "service_failure_status.json"
    clarity_path = root / "runtime" / "clarity_status.json"
    active_objective_path = root / "runtime" / "active_objective.json"
    source_registry_path = root / "docs" / "canonical" / "CALYX_SOURCE_AUTHORITY_REGISTRY.json"
    confusion_protocol_path = root / "docs" / "canonical" / "CALYX_CONFUSION_ESCALATION_PROTOCOL.md"
    decision_ledger_path = root / "docs" / "canonical" / "CALYX_DECISION_LEDGER.md"
    result: dict[str, Any] = {
        "authority": "advisory runtime truth surface",
        "authority_note": "MCP reports existing Station truth files; it does not become liveness authority.",
        "state_path": str(state_path),
        "state_exists": state_path.exists(),
        "clarity_status": read_json_status(clarity_path),
        "active_objective": read_json_status(active_objective_path),
        "source_authority_registry": read_json_status(source_registry_path),
        "confusion_protocol": {
            "exists": confusion_protocol_path.exists(),
            "path": str(confusion_protocol_path),
        },
        "decision_ledger": {
            "exists": decision_ledger_path.exists(),
            "path": str(decision_ledger_path),
        },
    }
    if state_path.exists():
        result["state_text"] = state_path.read_text(encoding="utf-8", errors="replace")
    for label, path in (("topology", topology_path), ("service_failure", failure_path)):
        if path.exists():
            try:
                result[label] = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                result[label] = {"error": f"invalid json: {exc}"}
        else:
            result[label] = {"exists": False, "path": str(path)}
    return result


TOOLS = {
    "calyx_scope": {
        "description": "Report Station Calyx MCP authority, mode, limits, and approved local roots.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "handler": tool_scope,
    },
    "calyx_stat": {
        "description": "Return metadata for one path inside the approved Station Calyx MCP scope.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
        "handler": tool_stat,
    },
    "calyx_list": {
        "description": "List one directory inside the approved Station Calyx MCP scope.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
        "handler": tool_list,
    },
    "calyx_read_text": {
        "description": "Read an approved text file inside the Station Calyx MCP scope.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "max_bytes": {"type": "integer", "minimum": 1, "maximum": MAX_READ_BYTES}},
            "required": ["path"],
            "additionalProperties": False,
        },
        "handler": tool_read_text,
    },
    "calyx_runtime_status": {
        "description": "Return existing Station runtime truth surfaces through MCP as advisory status.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "handler": tool_runtime_status,
    },
}


def text_content(value: Any) -> list[dict[str, str]]:
    return [{"type": "text", "text": json.dumps(value, indent=2, ensure_ascii=False)}]


def list_tools() -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["inputSchema"],
            }
            for name, spec in TOOLS.items()
        ]
    }


def list_resources() -> dict[str, Any]:
    resources = []
    for root in allowed_roots():
        resources.append(
            {
                "uri": f"calyx://root/{root.name}",
                "name": root.name,
                "description": f"Approved Station Calyx local MCP root: {root.path}",
                "mimeType": "application/json",
            }
        )
    return {"resources": resources}


def read_resource(uri: str) -> dict[str, Any]:
    if not uri.startswith("calyx://root/"):
        raise McpError(-32602, "unsupported resource uri", {"uri": uri})
    name = uri.removeprefix("calyx://root/")
    for root in allowed_roots():
        if root.name == name:
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(
                            {"name": root.name, "path": str(root.path), "exists": root.exists, "mode": "read_only"},
                            indent=2,
                        ),
                    }
                ]
            }
    raise McpError(-32002, "unknown approved root resource", {"uri": uri})


def handle_request(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    if request_id is None:
        return None

    try:
        if method == "initialize":
            result = {
                "protocolVersion": params.get("protocolVersion") or PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}, "resources": {"subscribe": False, "listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": "Read-only local Station Calyx MCP server scoped to approved workstation folders only.",
            }
        elif method == "tools/list":
            result = list_tools()
        elif method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if name not in TOOLS:
                raise McpError(-32601, "unknown tool", {"name": name})
            value = TOOLS[name]["handler"](arguments)
            result = {"content": text_content(value), "isError": False}
            write_receipt("tool_call", {"tool": name, "arguments": safe_arguments(arguments), "result_summary": summarize_result(value)})
        elif method == "resources/list":
            result = list_resources()
        elif method == "resources/read":
            result = read_resource(str(params.get("uri") or ""))
            write_receipt("resource_read", {"uri": str(params.get("uri") or "")})
        elif method in {"ping", "$/ping"}:
            result = {}
        else:
            raise McpError(-32601, "method not found", {"method": method})
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except McpError as exc:
        write_receipt("error", {"method": method, "error": exc.message, "data": exc.data})
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": exc.code, "message": exc.message, "data": exc.data}}
    except Exception as exc:  # defensive boundary for MCP clients
        write_receipt("error", {"method": method, "error": str(exc)})
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": "internal error", "data": str(exc)}}


def safe_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    return {key: ("<omitted>" if key.lower() in {"text", "content"} else value) for key, value in arguments.items()}


def summarize_result(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        summary = {key: value[key] for key in ("path", "root", "entry_count", "truncated", "exists", "mode") if key in value}
        if "allowed_roots" in value:
            summary["allowed_root_count"] = len(value["allowed_roots"])
        return summary
    return {"type": type(value).__name__}


def read_message(stream: BinaryIO) -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if line == b"":
            return None
        line = line.decode("ascii", errors="replace").strip()
        if not line:
            break
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = stream.read(length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def write_message(stream: BinaryIO, message: dict[str, Any]) -> None:
    body = json.dumps(message, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    stream.write(header + body)
    stream.flush()


def run_stdio() -> int:
    write_receipt("server_start", {"mode": "stdio", "pid": os.getpid()})
    while True:
        message = read_message(sys.stdin.buffer)
        if message is None:
            break
        response = handle_request(message)
        if response is not None:
            write_message(sys.stdout.buffer, response)
    write_receipt("server_stop", {"mode": "stdio", "pid": os.getpid()})
    return 0


def validate_once() -> int:
    checks = {
        "scope": tool_scope({}),
        "terminal_stat": tool_stat({"path": "C:/Calyx_Terminal"}),
        "data_stat": tool_stat({"path": "D:/Calyx_Data"}),
    }
    denied = False
    try:
        tool_stat({"path": "C:/Users"})
    except McpError:
        denied = True
    checks["outside_scope_denied"] = denied
    print(json.dumps(checks, indent=2))
    return 0 if denied else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Station Calyx local read-only MCP server")
    parser.add_argument("--stdio", action="store_true", help="Run stdio MCP transport")
    parser.add_argument("--validate", action="store_true", help="Run local scope validation and exit")
    args = parser.parse_args(argv)
    if args.validate:
        return validate_once()
    if args.stdio:
        return run_stdio()
    parser.error("one of --stdio or --validate is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
