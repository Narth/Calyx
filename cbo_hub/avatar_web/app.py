"""
Browser-based CBO Avatar — web UI that proxies to CBO Core.
LLM-powered whiteboard: task list, agent roster, Run with CBO (serialized, one at a time).
Open in browser: http://127.0.0.1:7780/  (chat) or http://127.0.0.1:7780/whiteboard
Localhost only (STATION_STACK_POLICY). Run build_safety_check before heavy builds.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import hashlib
import subprocess
import uuid
from collections import deque
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional import guard
    psutil = None  # type: ignore

from .workspace_v0 import (
    apply_operations_to_board,
    board_state_hash,
    certify_workspace_proposal,
    default_board_state,
    default_discussion_state,
    default_workspace_meta,
    normalize_board_state,
    validate_workspace_proposal_response,
    validate_and_normalize_operations,
)

CBO_CHAT = "http://127.0.0.1:7778/chat"
CBO_WORKSPACE_PROPOSAL = "http://127.0.0.1:7778/workspace/proposal"
CBO_WORKSPACE_DISCUSSION = "http://127.0.0.1:7778/workspace/discussion"
_PHASE5_POCKET_CONTRACT = "whiteboard_pocket_contract"


def _emit(event: str, msg: str, level: str = "INFO", data: dict | None = None) -> None:
    """Emit to Station Event Ledger. Never throws."""
    try:
        from calyx.kernel.event_ledger import emit as _le
        _le(level=level, component="avatar", event=event, msg=msg, data=data or {})
    except Exception:
        pass

# Whiteboard state: tasks + agent roster. Serialized single LLM run (one at a time).
_WHITEBOARD_LOCK = asyncio.Lock()
_RUN_IN_PROGRESS = False
_TASKS: list[dict] = []
# Crew: simple, non-assuming — helpers with construction/pirate hats; room for human avatars (interwoven work forces).
_AGENTS = [
    {"id": "cbo", "display_name": "CBO", "avatar": "👷", "avatar_type": "construction", "current_task_id": None, "role": "Station Calyx — builder"},
    {"id": "placeholder_1", "display_name": "Crew (node)", "avatar": "🏴‍☠️", "avatar_type": "pirate", "current_task_id": None, "role": "Coming when hardware allows"},
    {"id": "placeholder_2", "display_name": "Crew (activity)", "avatar": "🔧", "avatar_type": "helper", "current_task_id": None, "role": "Coming when hardware allows"},
    {"id": "human", "display_name": "You", "avatar": "👤", "avatar_type": "human", "current_task_id": None, "role": "Human — plan & steer (avatar later)"},
]
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_TASKS_FILE = _DATA_DIR / "whiteboard_tasks.json"
_WORKSPACE_BOARD_FILE = _DATA_DIR / "workspace_live_board.json"
_WORKSPACE_PROPOSAL_FILE = _DATA_DIR / "workspace_proposal_state.json"
_WORKSPACE_DISCUSSION_FILE = _DATA_DIR / "workspace_discussion.json"
_WORKSPACE_META_FILE = _DATA_DIR / "workspace_meta.json"
_WORKSPACE_UNDO_FILE = _DATA_DIR / "workspace_undo_state.json"
_WORKSPACE_HTML_FILE = Path(__file__).resolve().with_name("workspace_v0.html")
_WORKSPACE_SESSION_ID = "workspace-v0"
_CBO_CORE_RECEIPTS_FILE = Path(__file__).resolve().parent.parent / "receipts" / "cbo_core.jsonl"
_STATION_PROCESS_CACHE: dict[str, object] = {"expires_at": None, "rows": []}


def _extract_contract_fields(payload: dict | None) -> dict:
    payload = payload or {}
    contract = payload.get("pocket_contract")
    if isinstance(contract, dict):
        return contract
    extracted: dict[str, object] = {}
    for key in (
        "OBJECTIVE",
        "ALLOWED_CONTEXT",
        "ALLOWED_TOOLS",
        "EXIT_CRITERIA",
        "MAX_RECURSION_DEPTH",
        "objective",
        "allowed_context",
        "allowed_tools",
        "exit_criteria",
        "max_recursion_depth",
    ):
        if key in payload:
            extracted[key] = payload[key]
    return extracted


def _coerce_depth(value: object, *, default: int = 0) -> int | None:
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def _with_pocket_contract_state(task: dict) -> dict:
    from calyx.kernel.pocket_contract import normalize_pocket_contract, validate_pocket_contract

    enriched = dict(task)
    title = str(enriched.get("title") or "").strip()
    contract = normalize_pocket_contract(enriched.get("pocket_contract"), fallback_objective=title)
    errors = validate_pocket_contract(contract)
    enriched["title"] = title or contract.get("OBJECTIVE") or "Untitled task"
    enriched["pocket_contract"] = contract
    enriched["pocket_contract_status"] = "ready" if not errors else "incomplete"
    enriched["pocket_contract_errors"] = errors
    enriched["current_recursion_depth"] = _coerce_depth(enriched.get("current_recursion_depth"), default=0) or 0
    return enriched


def _to_stored_task(task: dict) -> dict:
    enriched = _with_pocket_contract_state(task)
    return {
        "id": enriched["id"],
        "title": enriched["title"],
        "status": enriched["status"],
        "assigned_agent_id": enriched.get("assigned_agent_id"),
        "result_snippet": enriched.get("result_snippet"),
        "created_at": enriched["created_at"],
        "updated_at": enriched["updated_at"],
        "pocket_contract": enriched["pocket_contract"],
        "current_recursion_depth": enriched["current_recursion_depth"],
    }


def _append_whiteboard_receipt(
    *,
    receipt_type: str,
    status: str,
    task: dict | None = None,
    reason: str | None = None,
    signals: list[str] | None = None,
    details: dict | None = None,
) -> None:
    try:
        from calyx.kernel.failure_patterns import attach_failure_pattern_metadata
        from calyx.kernel.receipts import append_receipt_line

        payload = {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "phase": _PHASE5_POCKET_CONTRACT,
            "status": status,
            "receipt_type": receipt_type,
        }
        if reason:
            payload["reason"] = reason
        if task:
            task_view = _with_pocket_contract_state(task)
            payload["task_id"] = task_view.get("id")
            payload["title"] = task_view.get("title")
            payload["current_recursion_depth"] = task_view.get("current_recursion_depth")
            payload["pocket_contract"] = task_view.get("pocket_contract")
            payload["pocket_contract_status"] = task_view.get("pocket_contract_status")
        if details:
            payload.update(details)
        append_receipt_line(
            attach_failure_pattern_metadata(
                payload,
                signals=list(signals or []) + ([reason] if reason else []),
            ),
            prefix="avatar_whiteboard",
        )
    except Exception:
        pass


def _workspace_runtime_dir() -> Path:
    from calyx.kernel.paths import resolve_repo_root, resolve_runtime_dir

    return resolve_runtime_dir(resolve_repo_root(Path(__file__).resolve()))


def _station_ledger_dir() -> Path:
    path = _workspace_runtime_dir() / "ledger"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _station_read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return deepcopy(default)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return deepcopy(default)
    return payload if isinstance(payload, dict) else deepcopy(default)


def _station_recent_events(*, limit: int = 40) -> list[dict]:
    ledger_dir = _station_ledger_dir()
    recent_files = sorted(ledger_dir.glob("station_events__*.jsonl"))[-2:]
    lines: deque[str] = deque(maxlen=max(1, limit * 6))
    for path in recent_files:
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        lines.append(line.strip())
        except Exception:
            continue
    events: list[dict] = []
    for line in lines:
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        events.append(payload)
    events.sort(key=lambda item: str(item.get("ts_utc") or item.get("ts") or ""))
    return events[-limit:]


def _station_event_excerpt(event: dict) -> str:
    msg = str(event.get("msg") or "").strip()
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    if data:
        if "path" in data:
            msg = f"{msg} ({data['path']})" if msg else f"path={data['path']}"
        elif "task_name" in data:
            msg = f"{msg} ({data['task_name']})" if msg else f"task={data['task_name']}"
    return msg[:140]


def _station_is_passive_ui_poll(event: dict) -> bool:
    event_name = str(event.get("event") or "").strip()
    if event_name != "station.smoke":
        return False
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    path = str(data.get("path") or "").strip()
    return path in {"/api/station/activity"}


def _station_process_activity(*, limit: int = 12) -> list[dict]:
    definitions = [
        ("generate_daily_24h_review.py", "audit", "Daily 24H Review generator"),
        ("run_daily_24h_review_cycle.ps1", "audit", "Daily 24H Review cycle"),
        ("station_health_loop.ps1", "health", "Station health loop"),
        ("navigator_triage_loop.ps1", "navigator", "Navigator + triage loop"),
        ("energy_churn_cp9_loop.ps1", "energy", "Energy churn + CP9 loop"),
        ("cp6_cp7_loop.ps1", "memory", "CP6 + CP7 loop"),
        ("service_failure_watch.ps1", "health", "Service failure watcher"),
        ("calyx.cbo.bridge_overseer", "cbo", "CBO Bridge Overseer"),
        ("cbo_hub.cli_avatar.main", "avatar", "CLI Avatar"),
        ("cbo_hub.dev_harness.app:app", "dev_harness", "Dev Harness"),
        ("cbo_hub.cbo_core.app:app", "cbo", "CBO Core"),
        ("cbo_hub.avatar_web.app:app", "avatar", "Avatar Web"),
        ("cbo_hub.telemetry_gateway.app:app", "telemetry", "Telemetry Gateway"),
        ("calyx.cbo.discord_gateway", "discord_gateway", "Discord Gateway"),
    ]
    cached_rows = _station_process_cache_rows(definitions)
    return _station_group_process_rows(cached_rows)[:limit]


def _station_process_cache_rows(definitions: list[tuple[str, str, str]]) -> list[dict]:
    now = datetime.now(UTC)
    expires_at = _STATION_PROCESS_CACHE.get("expires_at")
    if isinstance(expires_at, datetime) and expires_at > now:
        rows = _STATION_PROCESS_CACHE.get("rows")
        return list(rows) if isinstance(rows, list) else []
    rows = _station_collect_process_rows(definitions)
    _STATION_PROCESS_CACHE["rows"] = rows
    _STATION_PROCESS_CACHE["expires_at"] = now + timedelta(seconds=12)
    return rows


def _station_collect_process_rows(definitions: list[tuple[str, str, str]]) -> list[dict]:
    rows = _station_collect_process_rows_psutil(definitions)
    if rows:
        return rows
    return _station_collect_process_rows_powershell(definitions)


def _station_collect_process_rows_psutil(definitions: list[tuple[str, str, str]]) -> list[dict]:
    if not psutil:
        return []
    seen: set[tuple[str, str]] = set()
    rows: list[dict] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            joined = " ".join(str(part) for part in cmdline).lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        if not joined:
            continue
        for needle, component, label in definitions:
            if needle.lower() not in joined:
                continue
            key = (needle, str(proc.info.get("pid") or ""))
            if key in seen:
                continue
            seen.add(key)
            created = proc.info.get("create_time")
            started_at = (
                datetime.fromtimestamp(float(created), tz=UTC).isoformat()
                if created
                else ""
            )
            variant = _station_process_variant(" ".join(str(part) for part in cmdline))
            rows.append(
                {
                    "pid": proc.info.get("pid"),
                    "component": component,
                    "task_name": label,
                    "started_at": started_at,
                    "status": "running",
                    "excerpt": f"Active process {label}",
                    "variant": variant,
                }
            )
            break
    rows.sort(key=lambda item: str(item.get("started_at") or ""), reverse=True)
    return rows


def _station_collect_process_rows_powershell(definitions: list[tuple[str, str, str]]) -> list[dict]:
    script = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -and ($_.CommandLine -like '*Calyx_Terminal*' -or $_.CommandLine -like '*calyx.cbo*' -or $_.CommandLine -like '*cbo_hub*') } | "
        "Select-Object ProcessId, CommandLine, CreationDate | ConvertTo-Json -Compress"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "-"],
            input=script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=6,
        )
    except Exception:
        return []
    if proc.returncode != 0 or not proc.stdout.strip():
        return []
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        return []
    items = payload if isinstance(payload, list) else [payload] if isinstance(payload, dict) else []
    seen: set[tuple[str, str]] = set()
    rows: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        cmdline = str(item.get("CommandLine") or "")
        lower_cmd = cmdline.lower()
        pid = str(item.get("ProcessId") or "")
        for needle, component, label in definitions:
            if needle.lower() not in lower_cmd:
                continue
            key = (needle, pid)
            if key in seen:
                continue
            seen.add(key)
            variant = _station_process_variant(cmdline)
            rows.append(
                {
                    "pid": item.get("ProcessId"),
                    "component": component,
                    "task_name": label,
                    "started_at": str(item.get("CreationDate") or ""),
                    "status": "running",
                    "excerpt": f"Active process {label}",
                    "variant": variant,
                }
            )
            break
    rows.sort(key=lambda entry: str(entry.get("started_at") or ""), reverse=True)
    return rows


def _station_process_variant(cmdline: str) -> str:
    lower = str(cmdline or "").lower()
    if ".venv_cbohub311" in lower:
        return "venv_cbohub311"
    if "python311" in lower:
        return "python311"
    if "powershell.exe" in lower:
        return "powershell"
    return "station"


def _station_group_process_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (str(row.get("component") or ""), str(row.get("task_name") or ""))
        entry = grouped.setdefault(
            key,
            {
                "component": row.get("component"),
                "task_name": row.get("task_name"),
                "status": "running",
                "started_at": row.get("started_at") or "",
                "variant_count": 0,
                "variants": [],
                "pids": [],
                "excerpt": "",
            },
        )
        started_at = str(row.get("started_at") or "")
        if started_at and started_at > str(entry.get("started_at") or ""):
            entry["started_at"] = started_at
        pid = row.get("pid")
        if pid and pid not in entry["pids"]:
            entry["pids"].append(pid)
        variant = str(row.get("variant") or "station")
        if variant not in entry["variants"]:
            entry["variants"].append(variant)
    output: list[dict] = []
    for entry in grouped.values():
        entry["variant_count"] = len(entry["variants"])
        entry["process_count"] = len(entry["pids"])
        variants = ", ".join(str(item) for item in entry["variants"])
        entry["excerpt"] = f"{entry['process_count']} process(es) across {entry['variant_count']} variant(s): {variants}" if variants else f"{entry['process_count']} process(es)"
        output.append(entry)
    output.sort(key=lambda item: str(item.get("started_at") or ""), reverse=True)
    return output


def _station_recent_artifact_events(*, limit: int = 16, window_minutes: int = 240) -> list[dict]:
    runtime_dir = _workspace_runtime_dir()
    now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=max(5, window_minutes))
    roots = [
        runtime_dir / "receipts" / "audit",
        runtime_dir / "receipts" / "security",
        runtime_dir / "receipts" / "budget",
        runtime_dir / "receipts" / "canonical",
        runtime_dir / "workspace_v0" / "failures",
        runtime_dir / "workspace_v0" / "proposals",
        runtime_dir / "workspace_v0" / "approvals",
        runtime_dir / "workspace_v0" / "submissions",
    ]
    rows: list[dict] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.glob("*.json*"):
            try:
                stat = path.stat()
            except OSError:
                continue
            modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
            if modified < cutoff:
                continue
            payload = _station_read_json(path, default={})
            schema = str(payload.get("schema") or "").strip()
            script = str(((payload.get("generator") or {}) if isinstance(payload.get("generator"), dict) else {}).get("script") or payload.get("script") or "").strip()
            summary_bits = []
            if path.stem:
                summary_bits.append(path.stem.replace("__", " "))
            if schema:
                summary_bits.append(schema)
            if script:
                summary_bits.append(Path(script).name)
            excerpt = " · ".join(summary_bits[:3]) or f"Artifact updated {path.name}"
            rows.append(
                {
                    "ts_utc": modified.isoformat(),
                    "component": "artifacts",
                    "event": "artifact.updated",
                    "level": "INFO",
                    "excerpt": excerpt[:180],
                    "corr_id": "",
                    "path": str(path),
                }
            )
    rows.sort(key=lambda item: str(item.get("ts_utc") or ""), reverse=True)
    return rows[:limit]


def _station_recent_history(*, limit: int = 24) -> dict:
    recent_events = _station_recent_events(limit=max(limit, 40))
    active_tasks: dict[str, dict] = {}
    for event in recent_events:
        event_name = str(event.get("event") or "").strip()
        envelope = event.get("causal_envelope") if isinstance(event.get("causal_envelope"), dict) else {}
        task_corr_id = str(event.get("corr_id") or envelope.get("task_corr_id") or "").strip()
        task_name = str((event.get("data") or {}).get("task_name") or envelope.get("task_name") or "").strip()
        if event_name == "system.task.triggered" and task_corr_id:
            active_tasks[task_corr_id] = {
                "task_corr_id": task_corr_id,
                "task_name": task_name or "task",
                "component": str(event.get("component") or "").strip(),
                "started_at": str(event.get("ts_utc") or event.get("ts") or ""),
                "status": "running",
                "excerpt": _station_event_excerpt(event),
            }
        elif event_name == "system.task.completed" and task_corr_id:
            active_tasks.pop(task_corr_id, None)
    history: list[dict] = []
    for event in reversed(recent_events[-limit:]):
        if _station_is_passive_ui_poll(event):
            continue
        history.append(
            {
                "ts_utc": str(event.get("ts_utc") or event.get("ts") or ""),
                "component": str(event.get("component") or "station"),
                "event": str(event.get("event") or ""),
                "level": str(event.get("level") or "INFO"),
                "excerpt": _station_event_excerpt(event),
                "corr_id": str(event.get("corr_id") or ""),
            }
        )
    history.extend(_station_recent_artifact_events(limit=limit))
    history.sort(key=lambda item: str(item.get("ts_utc") or ""), reverse=True)
    active_processes = _station_process_activity(limit=max(4, min(12, limit // 2 or 4)))
    return {
        "recent_events": history[:limit],
        "active_tasks": list(active_tasks.values()),
        "active_processes": active_processes,
    }


def _station_avatar_summary(history: dict | None = None) -> dict:
    runtime_dir = _workspace_runtime_dir()
    repo_root = runtime_dir.parent
    station_health = _station_read_json(runtime_dir / "station_health.json", default={})
    navigator = _station_read_json(repo_root / "outgoing" / "navigator.lock", default={})
    triage = _station_read_json(repo_root / "outgoing" / "triage.lock", default={})
    history = history or _station_recent_history(limit=20)
    active_tasks = history["active_tasks"]
    active_processes = history["active_processes"]
    health = str(station_health.get("health") or "unknown").lower()
    entropy = str(((station_health.get("entropy") or {}) if isinstance(station_health.get("entropy"), dict) else {}).get("tier") or "unknown").lower()
    navigator_interval = str(navigator.get("interval_status") or "unknown").lower()
    triage_status = str(triage.get("status") or "unknown").lower()
    if health == "fail":
        avatar = {"emoji": "🚨", "label": "Distressed"}
    elif navigator_interval == "pause":
        avatar = {"emoji": "🛑", "label": "Paused"}
    elif active_tasks or active_processes:
        avatar = {"emoji": "⚙️", "label": "Working"}
    elif entropy not in {"pass", "unknown"}:
        avatar = {"emoji": "🔥", "label": "Hot"}
    else:
        avatar = {"emoji": "👁️", "label": "Idle Watch"}
    return {
        "avatar_emoji": avatar["emoji"],
        "avatar_label": avatar["label"],
        "health": health,
        "entropy_tier": entropy,
        "navigator_interval": navigator_interval,
        "triage_status": triage_status,
        "cpu_pct": station_health.get("cpu_pct"),
        "ram_pct": station_health.get("ram_pct"),
        "truth_state": station_health.get("truth_state"),
        "last_health_ts": station_health.get("health_ts") or station_health.get("emitted_ts_utc"),
        "active_task_count": len(active_tasks),
        "active_process_count": len(active_processes),
    }


def _workspace_artifact_dir(kind: str) -> Path:
    path = _workspace_runtime_dir() / "workspace_v0" / kind
    path.mkdir(parents=True, exist_ok=True)
    return path


def _workspace_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _workspace_parse_iso(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _workspace_elapsed_seconds(start: str | None, end: str | None) -> float | None:
    start_dt = _workspace_parse_iso(start)
    end_dt = _workspace_parse_iso(end)
    if start_dt is None or end_dt is None:
        return None
    delta = (end_dt - start_dt).total_seconds()
    if delta < 0:
        return None
    return round(delta, 3)


def _workspace_elapsed_ms(start: str | None, end: str | None) -> int | None:
    seconds = _workspace_elapsed_seconds(start, end)
    if seconds is None:
        return None
    return max(0, int(round(seconds * 1000)))


def _workspace_governance_timing(
    proposal: dict | None,
    *,
    proposal_created_at: str | None = None,
    proposal_displayed_at: str | None = None,
    approval_decision_at: str | None = None,
    execution_started_at: str | None = None,
    execution_completed_at: str | None = None,
    queue_depth_observed: int | None = None,
    queue_depth_after_decision: int | None = None,
    outcome: str | None = None,
) -> dict:
    proposal = proposal or {}
    created_at = proposal_created_at or str(proposal.get("created_at") or "")
    displayed_at = proposal_displayed_at or str(proposal.get("displayed_at") or "")
    decision_at = approval_decision_at or ""
    execution_started = execution_started_at or ""
    execution_completed = execution_completed_at or ""
    queue_depth = queue_depth_observed if queue_depth_observed is not None else (1 if created_at else 0)
    return {
        "proposal_created_at": created_at,
        "proposal_displayed_at": displayed_at or None,
        "approval_decision_at": decision_at or None,
        "execution_started_at": execution_started or None,
        "execution_completed_at": execution_completed or None,
        "time_to_display_seconds": _workspace_elapsed_seconds(created_at, displayed_at),
        "proposal_dwell_seconds": _workspace_elapsed_seconds(created_at, decision_at),
        "display_dwell_seconds": _workspace_elapsed_seconds(displayed_at, decision_at),
        "execution_duration_ms": _workspace_elapsed_ms(execution_started, execution_completed),
        "queue_depth_observed": queue_depth,
        "queue_depth_after_decision": queue_depth_after_decision,
        "outcome": outcome,
    }


def _workspace_operator_path(session_id: str) -> dict:
    return {
        "surface": "workspace.whiteboard",
        "session_id": session_id,
        "interaction_kind": "proposal_review",
        "operator_present": True,
    }


def _workspace_write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _workspace_read_json(path: Path, default: dict | list):
    if not path.exists():
        return deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return deepcopy(default)


def _workspace_load_board_state() -> dict:
    return normalize_board_state(_workspace_read_json(_WORKSPACE_BOARD_FILE, default_board_state()))


def _workspace_save_board_state(board_state: dict) -> dict:
    normalized = normalize_board_state(board_state)
    normalized["updated_at"] = _workspace_now_iso()
    _workspace_write_json(_WORKSPACE_BOARD_FILE, normalized)
    return normalized


def _workspace_load_discussion_state() -> dict:
    payload = _workspace_read_json(_WORKSPACE_DISCUSSION_FILE, default_discussion_state())
    if not isinstance(payload, dict):
        payload = default_discussion_state()
    payload["session_id"] = str(payload.get("session_id") or _WORKSPACE_SESSION_ID)
    messages = payload.get("messages")
    if not isinstance(messages, list):
        messages = []
    payload["messages"] = [message for message in messages if isinstance(message, dict)]
    payload["updated_at"] = str(payload.get("updated_at") or _workspace_now_iso())
    return payload


def _workspace_save_discussion_state(payload: dict) -> dict:
    discussion = _workspace_load_discussion_state()
    discussion.update(payload or {})
    discussion["session_id"] = str(discussion.get("session_id") or _WORKSPACE_SESSION_ID)
    discussion["updated_at"] = _workspace_now_iso()
    discussion["messages"] = [message for message in discussion.get("messages", []) if isinstance(message, dict)][-40:]
    _workspace_write_json(_WORKSPACE_DISCUSSION_FILE, discussion)
    return discussion


def _workspace_append_discussion_message(
    role: str,
    text: str,
    *,
    source: str = "workspace",
    message_type: str = "discussion",
    details: dict | None = None,
) -> dict:
    discussion = _workspace_load_discussion_state()
    discussion["messages"] = discussion.get("messages", [])
    discussion["messages"].append(
        {
            "id": f"msg_{uuid.uuid4().hex[:10]}",
            "role": role,
            "text": text,
            "source": source,
            "message_type": message_type,
            "details": details or {},
            "timestamp_utc": _workspace_now_iso(),
        }
    )
    return _workspace_save_discussion_state(discussion)


def _workspace_short(value: str, length: int = 10) -> str:
    text = str(value or "").strip()
    if not text:
        return "n/a"
    if "_" in text:
        prefix, suffix = text.split("_", 1)
        alias = {
            "submission": "sub",
            "proposal": "prop",
            "operation": "op",
            "msg": "msg",
        }.get(prefix, prefix[:4] or "id")
        return f"{alias}_{suffix[-6:]}"
    return text[-length:]


def _workspace_route_label(route: str) -> str:
    mapping = {
        "local": "local",
        "workhorse": "workhorse",
        "architect": "architect",
        "second_opinion": "second opinion",
        "second": "second opinion",
    }
    key = str(route or "").strip().lower()
    return mapping.get(key, key or "unknown")


def _workspace_timeline_submission_text(*, selected_route: str, submission_id: str, board_hash: str, operator_note: str) -> str:
    lines = [
        "Hybrid board submission sent.",
        f"Route: {_workspace_route_label(selected_route)}",
        f"Submission: {_workspace_short(submission_id)}",
        f"Board hash: {_workspace_short(board_hash, 12)}",
    ]
    if operator_note:
        lines.append(f"Note: {operator_note}")
    return "\n".join(lines)


def _workspace_timeline_proposal_text(
    *,
    proposal_id: str,
    selected_route: str,
    actual_route: str,
    tier_label: str,
    proposal_kind: str,
    quality_signal: str,
    discussion_response: str,
) -> str:
    lines = [
        f"Proposal {_workspace_short(proposal_id)} ready.",
        f"Tier: {tier_label}",
        f"Route: {_workspace_route_label(actual_route)} (selected {_workspace_route_label(selected_route)})",
        f"Kind: {proposal_kind.replace('_', ' ')}",
        f"Quality: {quality_signal.replace('_', ' ')}",
    ]
    if discussion_response:
        lines.append(discussion_response)
    return "\n".join(lines)


def _workspace_timeline_decision_text(*, action: str, proposal_id: str, approved_count: int, rejected_count: int) -> str:
    return "\n".join(
        [
            f"Proposal decision: {action}",
            f"Proposal: {_workspace_short(proposal_id)}",
            f"Approved ops: {approved_count}",
            f"Rejected ops: {rejected_count}",
        ]
    )


def _workspace_timeline_failure_text(*, selected_route: str, submission_id: str, result_type: str, summary: str) -> str:
    return "\n".join(
        [
            "Workspace submission did not complete cleanly.",
            f"Route: {_workspace_route_label(selected_route)}",
            f"Submission: {_workspace_short(submission_id)}",
            f"Result: {result_type.replace('_', ' ')}",
            summary,
        ]
    )


def _workspace_active_proposal_summary() -> dict | None:
    proposal = _workspace_load_proposal_state()
    if not proposal:
        return None
    return {
        "proposal_id": proposal.get("proposal_id"),
        "proposal_tier": proposal.get("proposal_tier"),
        "tier_label": proposal.get("tier_label"),
        "proposal_kind": proposal.get("proposal_kind"),
        "quality_signal": proposal.get("quality_signal"),
        "selected_route": proposal.get("selected_route"),
        "actual_route": proposal.get("actual_route"),
        "operation_count": len(proposal.get("operations") or []),
        "discussion_response": proposal.get("discussion_response"),
    }


def _workspace_compact_context_message(message: dict) -> dict | None:
    if not isinstance(message, dict):
        return None
    text = str(message.get("text") or "").strip()
    if not text:
        return None
    return {
        "role": str(message.get("role") or "assistant"),
        "message_type": str(message.get("message_type") or "discussion"),
        "source": str(message.get("source") or "workspace"),
        "text": text[:280],
        "timestamp_utc": str(message.get("timestamp_utc") or ""),
    }


def _workspace_filtered_proposal_context(messages: list[dict], *, limit: int = 4) -> list[dict]:
    discussion_messages: list[dict] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        message_type = str(message.get("message_type") or "").strip().lower()
        role = str(message.get("role") or "").strip().lower()
        compact = _workspace_compact_context_message(message)
        if compact is None:
            continue
        if message_type == "discussion" and role == "user":
            discussion_messages.append(compact)
    filtered = discussion_messages[-limit:]
    seen: set[str] = set()
    ordered: list[dict] = []
    for message in filtered:
        signature = json.dumps(message, sort_keys=True, ensure_ascii=False)
        if signature in seen:
            continue
        seen.add(signature)
        ordered.append(message)
    return ordered[-limit:]


def _workspace_is_provider_overload(raw_excerpt: str) -> bool:
    blob = str(raw_excerpt or "").lower()
    return any(term in blob for term in ("overloaded_error", "overloaded", "error 529", "rate_limit", "rate limit"))


def _workspace_load_cbo_core_receipt(receipt_sha256: str) -> dict | None:
    target = str(receipt_sha256 or "").strip()
    if not target or not _CBO_CORE_RECEIPTS_FILE.exists():
        return None
    try:
        lines = _CBO_CORE_RECEIPTS_FILE.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if str(payload.get("receipt_sha256") or "").strip() == target:
            return payload
    return None


def _workspace_usage_telemetry(
    *,
    receipt_sha256: str | None,
    provider_used: str | None,
    selected_route: str | None,
    actual_route: str | None,
) -> dict | None:
    receipt = _workspace_load_cbo_core_receipt(str(receipt_sha256 or ""))
    if not receipt:
        return None
    providers_called = [str(item).strip() for item in receipt.get("providers_called") or [] if str(item).strip()]
    provider = str(provider_used or "").strip() or (providers_called[0] if providers_called else "")
    usage_map = receipt.get("usage") if isinstance(receipt.get("usage"), dict) else {}
    provider_usage = usage_map.get(provider) if isinstance(usage_map.get(provider), dict) else {}
    model_id = None
    if provider == "local":
        model_id = ((receipt.get("local_receipt") or {}) if isinstance(receipt.get("local_receipt"), dict) else {}).get("model_id")
    elif provider == "kimi":
        model_id = ((receipt.get("second_opinion_receipt") or {}) if isinstance(receipt.get("second_opinion_receipt"), dict) else {}).get("model_id")
    telemetry = {
        "receipt_sha256": str(receipt.get("receipt_sha256") or receipt_sha256 or ""),
        "provider": provider or None,
        "providers_called": providers_called,
        "selected_route": str(selected_route or receipt.get("selected_route") or ""),
        "actual_route": str(actual_route or receipt.get("actual_route") or ""),
        "model_id": str(model_id or "").strip() or None,
        "input_tokens": provider_usage.get("input_tokens"),
        "output_tokens": provider_usage.get("output_tokens"),
        "total_tokens": provider_usage.get("total_tokens"),
        "latency_ms": provider_usage.get("latency_ms") or receipt.get("request_latency_ms"),
        "cost_estimate_usd": provider_usage.get("cost_estimate_usd"),
        "request_latency_ms": receipt.get("request_latency_ms"),
        "endpoint": receipt.get("endpoint"),
        "ts_utc": receipt.get("ts_utc"),
    }
    if telemetry["cost_estimate_usd"] is None and receipt.get("cost_estimate_usd") is not None and len(providers_called) <= 1:
        telemetry["cost_estimate_usd"] = receipt.get("cost_estimate_usd")
    if telemetry["total_tokens"] is None and telemetry["input_tokens"] is not None and telemetry["output_tokens"] is not None:
        telemetry["total_tokens"] = int(telemetry["input_tokens"]) + int(telemetry["output_tokens"])
    return telemetry


def _workspace_load_meta_state() -> dict:
    payload = _workspace_read_json(_WORKSPACE_META_FILE, default_workspace_meta())
    if not isinstance(payload, dict):
        payload = default_workspace_meta()
    payload["session_id"] = str(payload.get("session_id") or _WORKSPACE_SESSION_ID)
    payload["updated_at"] = str(payload.get("updated_at") or _workspace_now_iso())
    return payload


def _workspace_save_meta_state(payload: dict) -> dict:
    meta = _workspace_load_meta_state()
    meta.update(payload or {})
    meta["session_id"] = str(meta.get("session_id") or _WORKSPACE_SESSION_ID)
    meta["updated_at"] = _workspace_now_iso()
    _workspace_write_json(_WORKSPACE_META_FILE, meta)
    return meta


def _workspace_load_proposal_state() -> dict | None:
    proposal = _workspace_read_json(_WORKSPACE_PROPOSAL_FILE, {})
    if not isinstance(proposal, dict) or not proposal:
        return None
    return proposal


def _workspace_save_proposal_state(payload: dict | None) -> dict | None:
    if not payload:
        if _WORKSPACE_PROPOSAL_FILE.exists():
            try:
                _WORKSPACE_PROPOSAL_FILE.unlink()
            except Exception:
                pass
        return None
    _workspace_write_json(_WORKSPACE_PROPOSAL_FILE, payload)
    return payload


def _workspace_load_undo_state() -> dict | None:
    payload = _workspace_read_json(_WORKSPACE_UNDO_FILE, {})
    if not isinstance(payload, dict) or not payload:
        return None
    return payload


def _workspace_save_undo_state(payload: dict | None) -> dict | None:
    if not payload:
        if _WORKSPACE_UNDO_FILE.exists():
            try:
                _WORKSPACE_UNDO_FILE.unlink()
            except Exception:
                pass
        return None
    _workspace_write_json(_WORKSPACE_UNDO_FILE, payload)
    return payload


def _workspace_write_artifact(kind: str, prefix: str, payload: dict) -> str:
    path = _workspace_artifact_dir(kind) / f"{prefix}__{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def _workspace_decode_snapshot(data_url: str) -> tuple[bytes, str]:
    if not isinstance(data_url, str) or not data_url.startswith("data:image/"):
        raise ValueError("snapshot_render_failure")
    try:
        header, encoded = data_url.split(",", 1)
    except ValueError as exc:
        raise ValueError("snapshot_render_failure") from exc
    extension = "png"
    if "image/jpeg" in header:
        extension = "jpg"
    try:
        return base64.b64decode(encoded), extension
    except Exception as exc:
        raise ValueError("snapshot_render_failure") from exc


def _workspace_write_snapshot(data_url: str, submission_id: str) -> tuple[str, str]:
    snapshot_bytes, extension = _workspace_decode_snapshot(data_url)
    snapshot_sha256 = hashlib.sha256(snapshot_bytes).hexdigest()
    path = _workspace_artifact_dir("snapshots") / f"{submission_id}.{extension}"
    path.write_bytes(snapshot_bytes)
    return str(path), snapshot_sha256


def _append_workspace_receipt(
    *,
    receipt_type: str,
    status: str,
    details: dict | None = None,
) -> None:
    try:
        from calyx.kernel.receipts import append_receipt_line

        append_receipt_line(
            {
                "timestamp_utc": _workspace_now_iso(),
                "phase": "workspace_v0",
                "status": status,
                "receipt_type": receipt_type,
                **(details or {}),
            },
            prefix="avatar_workspace",
        )
    except Exception:
        pass


def _emit_workspace_governance_receipt(
    *,
    receipt_type: str,
    proposal_id: str,
    reason: str | None = None,
    extra: dict | None = None,
) -> None:
    try:
        from calyx.governance.receipts import emit_governance_receipt, make_receipt

        receipt = make_receipt(
            receipt_type=receipt_type,
            corr_id=proposal_id,
            component="avatar.workspace",
            proposal_id=proposal_id,
            operator_path=_workspace_operator_path(_WORKSPACE_SESSION_ID) if receipt_type in {"approval_granted", "approval_rejected"} else None,
            reason=reason,
            extra=extra,
        )
        emit_governance_receipt(receipt, prefix="governance")
    except Exception:
        pass


def _workspace_record_failure(
    *,
    failure_type: str,
    reason: str,
    details: dict | None = None,
) -> str:
    payload = {
        "timestamp_utc": _workspace_now_iso(),
        "session_id": _WORKSPACE_SESSION_ID,
        "failure_type": failure_type,
        "reason": reason,
        "details": details or {},
    }
    artifact_path = _workspace_write_artifact("failures", failure_type, payload)
    _workspace_save_meta_state({"last_failure": {**payload, "artifact_path": artifact_path}})
    _append_workspace_receipt(
        receipt_type="avatar.workspace.failure",
        status="failed",
        details={"failure_type": failure_type, "reason": reason, "artifact_path": artifact_path},
    )
    return artifact_path


def _workspace_current_state() -> dict:
    return {
        "session_id": _WORKSPACE_SESSION_ID,
        "board_state": _workspace_load_board_state(),
        "proposal_state": _workspace_load_proposal_state(),
        "discussion_state": _workspace_load_discussion_state(),
        "meta": _workspace_load_meta_state(),
        "undo_state": _workspace_load_undo_state(),
    }


def _format_contract_for_prompt(task: dict) -> str:
    task_view = _with_pocket_contract_state(task)
    contract = task_view["pocket_contract"]
    lines = [
        "Whiteboard pocket contract:",
        f"OBJECTIVE: {contract['OBJECTIVE']}",
        "ALLOWED_CONTEXT:",
        *[f"- {item}" for item in contract["ALLOWED_CONTEXT"]],
        "ALLOWED_TOOLS:",
        *[f"- {item}" for item in contract["ALLOWED_TOOLS"]],
        "EXIT_CRITERIA:",
        *[f"- {item}" for item in contract["EXIT_CRITERIA"]],
        f"MAX_RECURSION_DEPTH: {contract['MAX_RECURSION_DEPTH']}",
        f"CURRENT_RECURSION_DEPTH: {task_view['current_recursion_depth']}",
    ]
    return "\n".join(lines)


def _load_tasks() -> None:
    global _TASKS
    if _TASKS_FILE.exists():
        try:
            loaded = json.loads(_TASKS_FILE.read_text(encoding="utf-8"))
            _TASKS = [_to_stored_task(task) for task in loaded if isinstance(task, dict)]
        except Exception:
            _TASKS = []
    else:
        _TASKS = []


def _save_tasks() -> None:
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _TASKS_FILE.write_text(json.dumps(_TASKS, indent=2), encoding="utf-8")
    except Exception:
        pass


_load_tasks()

app = FastAPI(title="CBO Avatar (Web)", version="0.2")

# WO_NERVOUS_SYSTEM_PHASE1: request-scoped corr_id + station.smoke at boundary
try:
    from calyx.kernel.ledger_middleware import LedgerCorrIdMiddleware
    app.add_middleware(LedgerCorrIdMiddleware, service_name="avatar")
except Exception:
    pass


@app.on_event("startup")
def _avatar_startup():
    try:
        from calyx.kernel.event_ledger import clear_system_phase, emit as _le, get_ledger_dir, set_system_phase
        set_system_phase("boot")
        try:
            _le("INFO", "avatar", "station.boot", "Avatar Web started", data={})
            _le("INFO", "avatar", "station.service.identity", "Avatar Web identity", data={
                "service": "avatar_web",
                "pid": os.getpid(),
                "cwd": str(Path.cwd()),
                "ledger_dir": str(get_ledger_dir()),
            })
        finally:
            clear_system_phase()
    except Exception:
        pass


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(INDEX_HTML)


@app.get("/whiteboard", response_class=HTMLResponse)
def whiteboard_page():
    html = _WORKSPACE_HTML_FILE.read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.post("/api/chat")
async def chat_proxy(payload: dict):
    """Proxy to CBO Core /chat. Payload: user_text, session_id?, mode?, allow_tools?, model_role?, allow_second_opinion?."""
    _emit("avatar.chat_proxy", "POST /api/chat → CBO Core", data={"session_id": (payload.get("session_id") or "home")[:32]})
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(CBO_CHAT, json=payload)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ---------- Whiteboard API (local browser only) ----------

@app.get("/api/whiteboard/tasks")
def list_tasks():
    return {"tasks": [_with_pocket_contract_state(task) for task in _TASKS]}


@app.post("/api/whiteboard/tasks")
def add_task(payload: dict):
    from calyx.kernel.pocket_contract import normalize_pocket_contract, validate_pocket_contract

    title = (payload.get("title") or "").strip()
    contract = normalize_pocket_contract(_extract_contract_fields(payload), fallback_objective=title)
    title = title or contract.get("OBJECTIVE") or "Untitled task"
    contract_errors = validate_pocket_contract(contract)
    if contract_errors:
        _append_whiteboard_receipt(
            receipt_type="avatar.whiteboard.pocket.denied",
            status="denied",
            reason="pocket_contract_incomplete",
            details={"title": title, "contract_errors": contract_errors},
            signals=["pocket_contract_incomplete"],
        )
        raise HTTPException(
            status_code=400,
            detail={"reason": "pocket_contract_incomplete", "contract_errors": contract_errors},
        )
    _emit("avatar.whiteboard.task_add", f"Whiteboard task added: {title[:50]}", data={"title": title[:100]})
    task_id = str(uuid.uuid4())[:8]
    now = datetime.now(UTC).isoformat()
    task = {
        "id": task_id,
        "title": title,
        "status": "pending",
        "assigned_agent_id": None,
        "result_snippet": None,
        "created_at": now,
        "updated_at": now,
        "pocket_contract": contract,
        "current_recursion_depth": 0,
    }
    stored_task = _to_stored_task(task)
    _TASKS.append(stored_task)
    _save_tasks()
    _append_whiteboard_receipt(
        receipt_type="avatar.whiteboard.pocket.created",
        status="ok",
        task=stored_task,
    )
    return _with_pocket_contract_state(stored_task)


@app.patch("/api/whiteboard/tasks/{task_id}")
def update_task(task_id: str, payload: dict):
    from calyx.kernel.pocket_contract import normalize_pocket_contract, validate_pocket_contract

    for t in _TASKS:
        if t.get("id") == task_id:
            if "title" in payload:
                t["title"] = (payload.get("title") or "").strip() or t["title"]
            if "status" in payload:
                t["status"] = payload["status"]
            if "result_snippet" in payload:
                t["result_snippet"] = payload["result_snippet"]
            if "assigned_agent_id" in payload:
                t["assigned_agent_id"] = payload["assigned_agent_id"]
            if "current_recursion_depth" in payload:
                next_depth = _coerce_depth(payload.get("current_recursion_depth"), default=0)
                if next_depth is None:
                    raise HTTPException(
                        status_code=400,
                        detail={"reason": "pocket_contract_incomplete", "contract_errors": ["MAX_RECURSION_DEPTH"]},
                    )
                t["current_recursion_depth"] = next_depth
            incoming_contract = _extract_contract_fields(payload)
            if incoming_contract:
                merged_contract = dict(t.get("pocket_contract") or {})
                merged_contract.update(incoming_contract)
                contract = normalize_pocket_contract(merged_contract, fallback_objective=t["title"])
                contract_errors = validate_pocket_contract(contract)
                if contract_errors:
                    _append_whiteboard_receipt(
                        receipt_type="avatar.whiteboard.pocket.denied",
                        status="denied",
                        task=t,
                        reason="pocket_contract_incomplete",
                        details={"contract_errors": contract_errors},
                        signals=["pocket_contract_incomplete"],
                    )
                    raise HTTPException(
                        status_code=400,
                        detail={"reason": "pocket_contract_incomplete", "contract_errors": contract_errors},
                    )
                t["pocket_contract"] = contract
            t["updated_at"] = datetime.now(UTC).isoformat()
            _save_tasks()
            updated = _with_pocket_contract_state(t)
            _append_whiteboard_receipt(
                receipt_type="avatar.whiteboard.pocket.updated",
                status="ok",
                task=updated,
            )
            return updated
    raise HTTPException(status_code=404, detail="Task not found")


@app.get("/api/whiteboard/agents")
def list_agents():
    return {"agents": _AGENTS}


@app.post("/api/whiteboard/tasks/{task_id}/run")
async def run_task_with_cbo(task_id: str, payload: dict):
    """Run one task with CBO (single LLM at a time). Respects build safety: no concurrent heavy runs."""
    from calyx.kernel.pocket_contract import current_depth_exceeds_contract, whiteboard_allows_live_tools

    _emit("avatar.whiteboard.task_run", f"Whiteboard task run: {task_id}", data={"task_id": task_id})
    global _RUN_IN_PROGRESS
    async with _WHITEBOARD_LOCK:
        if _RUN_IN_PROGRESS:
            raise HTTPException(status_code=409, detail="Another task is already running. One LLM run at a time (build safety).")
        task = next((t for t in _TASKS if t.get("id") == task_id), None)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        task_view = _with_pocket_contract_state(task)
        if task_view["pocket_contract_status"] != "ready":
            _append_whiteboard_receipt(
                receipt_type="avatar.whiteboard.pocket.run.denied",
                status="denied",
                task=task_view,
                reason="pocket_contract_incomplete",
                details={"contract_errors": task_view["pocket_contract_errors"]},
                signals=["pocket_contract_incomplete"],
            )
            raise HTTPException(
                status_code=400,
                detail={"reason": "pocket_contract_incomplete", "contract_errors": task_view["pocket_contract_errors"]},
            )
        requested_depth = _coerce_depth(payload.get("recursion_depth"), default=task_view["current_recursion_depth"])
        if requested_depth is None or current_depth_exceeds_contract(task_view["pocket_contract"], requested_depth):
            _append_whiteboard_receipt(
                receipt_type="avatar.whiteboard.pocket.run.denied",
                status="denied",
                task=task_view,
                reason="recursion_depth_exceeded",
                details={
                    "requested_recursion_depth": payload.get("recursion_depth"),
                    "max_recursion_depth": task_view["pocket_contract"]["MAX_RECURSION_DEPTH"],
                },
                signals=["recursion_depth_exceeded"],
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "reason": "recursion_depth_exceeded",
                    "requested_recursion_depth": payload.get("recursion_depth"),
                    "max_recursion_depth": task_view["pocket_contract"]["MAX_RECURSION_DEPTH"],
                },
            )
        if task.get("status") == "in_progress":
            raise HTTPException(status_code=409, detail="Task already in progress.")
        _RUN_IN_PROGRESS = True
        for a in _AGENTS:
            a["current_task_id"] = None
        for a in _AGENTS:
            if a.get("id") == "cbo":
                a["current_task_id"] = task_id
                break
        task["current_recursion_depth"] = requested_depth
        task["status"] = "in_progress"
        task["assigned_agent_id"] = "cbo"
        task["updated_at"] = datetime.now(UTC).isoformat()
        _save_tasks()

    try:
        task_view = _with_pocket_contract_state(task)
        allow_tools_requested = bool(payload.get("allow_tools", True))
        allow_tools = allow_tools_requested and whiteboard_allows_live_tools(task_view["pocket_contract"])
        user_text = (
            f"{_format_contract_for_prompt(task_view)}\n\n"
            f"Whiteboard task: {task_view['title']}\n\n"
            "Please help with this task briefly and stay inside the declared pocket contract."
        )
        model_role = payload.get("model_role") or "local"
        _append_whiteboard_receipt(
            receipt_type="avatar.whiteboard.pocket.run.started",
            status="started",
            task=task_view,
            details={
                "requested_allow_tools": allow_tools_requested,
                "effective_allow_tools": allow_tools,
                "model_role": model_role,
            },
        )
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                CBO_CHAT,
                json={
                    "user_text": user_text,
                    "session_id": payload.get("session_id") or "whiteboard",
                    "mode": "dev",
                    "allow_tools": allow_tools,
                    "model_role": model_role,
                    "allow_second_opinion": False,
                },
            )
            r.raise_for_status()
            data = r.json()
            reply = (data.get("reply_text") or "")[:500]
            task["status"] = "done"
            task["result_snippet"] = reply or "(No reply text)"
            _append_whiteboard_receipt(
                receipt_type="avatar.whiteboard.pocket.run.completed",
                status="completed",
                task=task,
                details={"reply_excerpt": task["result_snippet"]},
            )
    except Exception as e:
        task["status"] = "failed"
        task["result_snippet"] = str(e)[:300]
        _append_whiteboard_receipt(
            receipt_type="avatar.whiteboard.pocket.run.failed",
            status="failed",
            task=task,
            details={"error": task["result_snippet"]},
        )
    finally:
        async with _WHITEBOARD_LOCK:
            _RUN_IN_PROGRESS = False
            for a in _AGENTS:
                a["current_task_id"] = None
        task["updated_at"] = datetime.now(UTC).isoformat()
        _save_tasks()

    return {"task": _with_pocket_contract_state(task)}


@app.get("/api/workspace/state")
def workspace_state():
    return _workspace_current_state()


@app.get("/api/station/activity")
def station_activity(limit: int = 24):
    bounded_limit = max(8, min(80, int(limit or 24)))
    history = _station_recent_history(limit=bounded_limit)
    return {
        "station": _station_avatar_summary(history),
        "active_tasks": history["active_tasks"],
        "active_processes": history["active_processes"],
        "recent_events": history["recent_events"],
    }


@app.put("/api/workspace/board")
def persist_workspace_board(payload: dict):
    try:
        board_state = _workspace_save_board_state(payload.get("board_state") or payload)
    except ValueError as exc:
        artifact_path = _workspace_record_failure(
            failure_type="board_validation_failure",
            reason=str(exc),
            details={"payload_keys": sorted((payload or {}).keys()) if isinstance(payload, dict) else []},
        )
        raise HTTPException(status_code=400, detail={"reason": str(exc), "artifact_path": artifact_path})
    _append_workspace_receipt(
        receipt_type="avatar.workspace.board.persisted",
        status="ok",
        details={"board_state_hash": board_state_hash(board_state)},
    )
    return {"board_state": board_state, "board_state_hash": board_state_hash(board_state)}


@app.post("/api/workspace/discussion")
async def workspace_discussion(payload: dict):
    user_text = str((payload or {}).get("user_text") or "").strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="user_text_required")
    _workspace_append_discussion_message("user", user_text, source="operator", message_type="discussion")
    board_state = _workspace_load_board_state()
    meta = _workspace_load_meta_state()
    last_submission = meta.get("last_submission") if isinstance(meta, dict) else None
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                CBO_WORKSPACE_DISCUSSION,
                json={
                    "user_text": user_text,
                    "session_id": (payload or {}).get("session_id") or _WORKSPACE_SESSION_ID,
                    "model_role": (payload or {}).get("model_role") or "local",
                    "board_state": board_state,
                    "board_state_hash": board_state_hash(board_state),
                    "discussion_context": _workspace_load_discussion_state().get("messages", [])[-12:],
                    "board_snapshot_ref": (last_submission or {}).get("board_snapshot_ref"),
                    "active_proposal_summary": _workspace_active_proposal_summary(),
                },
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        artifact_path = _workspace_record_failure(
            failure_type="transport_failure",
            reason="discussion_transport_failure",
            details={"status_code": exc.response.status_code, "response": exc.response.text[:400]},
        )
        _workspace_append_discussion_message(
            "assistant",
            "Workspace discussion failed.\nResult: discussion transport failure",
            source="workspace.discussion",
            message_type="failure",
            details={"artifact_path": artifact_path, "failure_type": "discussion_transport_failure"},
        )
        raise HTTPException(status_code=exc.response.status_code, detail={"reason": "discussion_transport_failure", "artifact_path": artifact_path})
    except Exception as exc:
        artifact_path = _workspace_record_failure(
            failure_type="transport_failure",
            reason="discussion_transport_failure",
            details={"error": str(exc)[:400]},
        )
        _workspace_append_discussion_message(
            "assistant",
            "Workspace discussion failed.\nResult: discussion transport failure",
            source="workspace.discussion",
            message_type="failure",
            details={"artifact_path": artifact_path, "failure_type": "discussion_transport_failure"},
        )
        raise HTTPException(status_code=502, detail={"reason": "discussion_transport_failure", "artifact_path": artifact_path})
    reply_text = str(data.get("discussion_response") or "").strip()
    discussion = _workspace_append_discussion_message("assistant", reply_text or "(No reply text)", source="workspace.discussion", message_type="discussion")
    return {
        "assistant_message": discussion["messages"][-1],
        "receipt_sha256": data.get("receipt_sha256"),
        "discussion_state": discussion,
    }


@app.post("/api/workspace/submit")
async def submit_workspace_board(payload: dict):
    try:
        board_state = normalize_board_state((payload or {}).get("board_state"))
    except ValueError as exc:
        artifact_path = _workspace_record_failure(
            failure_type="board_validation_failure",
            reason=str(exc),
            details={"path": "submit.board_state"},
        )
        raise HTTPException(status_code=400, detail={"reason": str(exc), "artifact_path": artifact_path})
    board_state = _workspace_save_board_state(board_state)
    discussion_state = _workspace_load_discussion_state()
    raw_discussion_messages = discussion_state.get("messages", [])
    discussion_context = _workspace_filtered_proposal_context(raw_discussion_messages)
    operator_note = str((payload or {}).get("operator_note") or "").strip()
    selected_route = str((payload or {}).get("model_role") or "local").strip().lower() or "local"
    submission_id = f"submission_{uuid.uuid4().hex[:10]}"
    try:
        snapshot_path, snapshot_sha256 = _workspace_write_snapshot((payload or {}).get("board_snapshot_data_url"), submission_id)
    except ValueError as exc:
        artifact_path = _workspace_record_failure(
            failure_type=str(exc),
            reason=str(exc),
            details={"submission_id": submission_id},
        )
        _workspace_append_discussion_message(
            "assistant",
            _workspace_timeline_failure_text(
                selected_route=selected_route,
                submission_id=submission_id,
                result_type=str(exc),
                summary="Snapshot capture failed before the proposal lane could run.",
            ),
            source="workspace.submit",
            message_type="failure",
            details={"artifact_path": artifact_path, "failure_type": str(exc), "submission_id": submission_id, "selected_route": selected_route},
        )
        raise HTTPException(status_code=400, detail={"reason": str(exc), "artifact_path": artifact_path})
    submission_artifact = {
        "timestamp_utc": _workspace_now_iso(),
        "submission_id": submission_id,
        "session_id": _WORKSPACE_SESSION_ID,
        "board_state_hash": board_state_hash(board_state),
        "board_snapshot_ref": snapshot_path,
        "board_snapshot_sha256": snapshot_sha256,
        "discussion_context": raw_discussion_messages[-12:],
        "discussion_context_summary": [message.get("text", "")[:140] for message in raw_discussion_messages[-12:] if isinstance(message, dict)],
        "proposal_context": discussion_context,
        "proposal_context_summary": [message.get("text", "")[:140] for message in discussion_context],
        "operator_note": operator_note,
        "selected_route": selected_route,
    }
    submission_artifact_path = _workspace_write_artifact("submissions", submission_id, submission_artifact)
    _append_workspace_receipt(
        receipt_type="avatar.workspace.submission.recorded",
        status="recorded",
        details={"submission_id": submission_id, "artifact_path": submission_artifact_path, "board_state_hash": submission_artifact["board_state_hash"], "selected_route": selected_route},
    )
    _workspace_append_discussion_message(
        "user",
        _workspace_timeline_submission_text(
            selected_route=selected_route,
            submission_id=submission_id,
            board_hash=submission_artifact["board_state_hash"],
            operator_note=operator_note,
        ),
        source="workspace.submit",
        message_type="submission",
        details={
            "submission_id": submission_id,
            "selected_route": selected_route,
            "board_state_hash": submission_artifact["board_state_hash"],
        },
    )
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                CBO_WORKSPACE_PROPOSAL,
                json={
                    "session_id": _WORKSPACE_SESSION_ID,
                    "model_role": selected_route,
                    "board_state": board_state,
                    "board_state_hash": submission_artifact["board_state_hash"],
                    "board_snapshot_ref": snapshot_path,
                    "board_snapshot_sha256": snapshot_sha256,
                    "discussion_context": discussion_context,
                    "operator_note": operator_note,
                },
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text[:400]
        try:
            error_payload = exc.response.json()
        except Exception:
            error_payload = {}
        detail = error_payload.get("detail") if isinstance(error_payload, dict) else None
        if isinstance(detail, dict) and (
            detail.get("reason") == "provider_overload"
            or _workspace_is_provider_overload(detail.get("raw_model_text_excerpt", ""))
        ):
            artifact_path = _workspace_record_failure(
                failure_type="provider_overload",
                reason="provider_overload",
                details={
                    "submission_id": submission_id,
                    "raw_reply_excerpt": detail.get("raw_model_text_excerpt", ""),
                    "proposal_receipt_sha256": detail.get("receipt_sha256"),
                },
            )
            _workspace_append_discussion_message(
                "assistant",
                _workspace_timeline_failure_text(
                    selected_route=selected_route,
                    submission_id=submission_id,
                    result_type="provider_overload",
                    summary="The selected provider reported temporary overload before returning a structured proposal.",
                ),
                source="workspace.submit",
                message_type="failure",
                details={"artifact_path": artifact_path, "failure_type": "provider_overload", "submission_id": submission_id, "selected_route": selected_route},
            )
            raise HTTPException(status_code=503, detail={"reason": "provider_overload", "artifact_path": artifact_path, "raw_reply_excerpt": detail.get("raw_model_text_excerpt", "")[:400]})
        if exc.response.status_code == 422 and isinstance(detail, dict) and detail.get("reason") == "malformed_model_output":
            artifact_path = _workspace_record_failure(
                failure_type="malformed_model_output",
                reason="malformed_model_output",
                details={
                    "submission_id": submission_id,
                    "raw_reply_excerpt": detail.get("raw_model_text_excerpt", ""),
                    "proposal_receipt_sha256": detail.get("receipt_sha256"),
                },
            )
            _workspace_append_discussion_message(
                "assistant",
                _workspace_timeline_failure_text(
                    selected_route=selected_route,
                    submission_id=submission_id,
                    result_type="structured_validation_failure",
                    summary="The workspace proposal lane returned malformed structured output.",
                ),
                source="workspace.submit",
                message_type="failure",
                details={"artifact_path": artifact_path, "failure_type": "malformed_model_output", "submission_id": submission_id, "selected_route": selected_route},
            )
            raise HTTPException(status_code=422, detail={"reason": "malformed_model_output", "artifact_path": artifact_path, "raw_reply_excerpt": detail.get("raw_model_text_excerpt", "")[:400]})
        artifact_path = _workspace_record_failure(
            failure_type="transport_failure",
            reason="workspace_submit_transport_failure",
            details={"submission_id": submission_id, "status_code": exc.response.status_code, "response": response_text},
        )
        _workspace_append_discussion_message(
            "assistant",
            _workspace_timeline_failure_text(
                selected_route=selected_route,
                submission_id=submission_id,
                result_type="proposal_endpoint_failure",
                summary=f"Workspace proposal endpoint returned HTTP {exc.response.status_code}.",
            ),
            source="workspace.submit",
            message_type="failure",
            details={"artifact_path": artifact_path, "failure_type": "workspace_submit_transport_failure", "submission_id": submission_id, "selected_route": selected_route},
        )
        raise HTTPException(status_code=exc.response.status_code, detail={"reason": "workspace_submit_transport_failure", "artifact_path": artifact_path})
    except Exception as exc:
        artifact_path = _workspace_record_failure(
            failure_type="transport_failure",
            reason="workspace_submit_transport_failure",
            details={"submission_id": submission_id, "error": str(exc)[:400]},
        )
        _workspace_append_discussion_message(
            "assistant",
            _workspace_timeline_failure_text(
                selected_route=selected_route,
                submission_id=submission_id,
                result_type="submission_transport_failure",
                summary="The submission could not reach the workspace proposal lane.",
            ),
            source="workspace.submit",
            message_type="failure",
            details={"artifact_path": artifact_path, "failure_type": "workspace_submit_transport_failure", "submission_id": submission_id, "selected_route": selected_route},
        )
        raise HTTPException(status_code=502, detail={"reason": "workspace_submit_transport_failure", "artifact_path": artifact_path})
    try:
        parsed = validate_workspace_proposal_response(data)
        certification = certify_workspace_proposal(
            board_state=board_state,
            operations=parsed["operations"],
            intent_schema=parsed["intent_schema"],
            proposal_kind=parsed["proposal_kind"],
        )
        operations = certification["operations"]
    except ValueError as exc:
        artifact_path = _workspace_record_failure(
            failure_type="malformed_model_output",
            reason=str(exc),
            details={"submission_id": submission_id, "raw_reply_excerpt": json.dumps(data, ensure_ascii=False)[:1200]},
        )
        _workspace_append_discussion_message(
            "assistant",
            _workspace_timeline_failure_text(
                selected_route=selected_route,
                submission_id=submission_id,
                result_type="structured_validation_failure",
                summary="The structured proposal payload did not pass workspace validation.",
            ),
            source="workspace.submit",
            message_type="failure",
            details={"artifact_path": artifact_path, "failure_type": str(exc), "submission_id": submission_id, "selected_route": selected_route},
        )
        raise HTTPException(status_code=422, detail={"reason": str(exc), "artifact_path": artifact_path, "raw_reply_excerpt": json.dumps(data, ensure_ascii=False)[:400]})
    proposal_id = f"proposal_{uuid.uuid4().hex[:10]}"
    usage_telemetry = _workspace_usage_telemetry(
        receipt_sha256=data.get("receipt_sha256"),
        provider_used=data.get("provider_used"),
        selected_route=parsed["selected_route"],
        actual_route=parsed["actual_route"],
    )
    proposal_created_at = _workspace_now_iso()
    proposal_timing = _workspace_governance_timing(
        None,
        proposal_created_at=proposal_created_at,
        queue_depth_observed=1,
        outcome="pending_review",
    )
    proposal_state = {
        "proposal_id": proposal_id,
        "submission_id": submission_id,
        "session_id": _WORKSPACE_SESSION_ID,
        "created_at": proposal_created_at,
        "status": "pending_review",
        "displayed_at": None,
        "governance_timing": proposal_timing,
        "board_state_hash_before": submission_artifact["board_state_hash"],
        "discussion_response": parsed["discussion_response"],
        "operations": operations,
        "validation_result": {"valid": True, "operation_count": len(operations)},
        "submission_artifact_path": submission_artifact_path,
        "board_snapshot_ref": snapshot_path,
        "board_snapshot_sha256": snapshot_sha256,
        "raw_model_reply_excerpt": json.dumps(data, ensure_ascii=False)[:1200],
        "model_receipt_sha256": data.get("receipt_sha256"),
        "provider_used": data.get("provider_used"),
        "proposal_tier": parsed["proposal_tier"],
        "tier_label": parsed["tier_label"],
        "tier_rationale": parsed["tier_rationale"],
        "confidence_summary": parsed["confidence_summary"],
        "proposal_kind": parsed["proposal_kind"],
        "quality_signal": parsed["quality_signal"],
        "selected_route": parsed["selected_route"],
        "actual_route": parsed["actual_route"],
        "usage_telemetry": usage_telemetry,
        "intent_schema": certification["intent_schema"],
        "geometry_status": certification["geometry_status"],
        "constraint_summary": certification["constraint_summary"],
        "solver_strategy_used": certification["solver_strategy_used"],
        "solver_diagnostics": certification["solver_diagnostics"],
    }
    proposal_state["validation_result"] = {
        "valid": certification["geometry_status"] in {"certified", "repaired"},
        "operation_count": len(operations),
        "geometry": certification["validation_result"],
    }
    proposal_artifact_path = _workspace_write_artifact(
        "proposals",
        proposal_id,
        {
            "timestamp_utc": proposal_created_at,
            "proposal_id": proposal_id,
            "originating_submission_ref": submission_artifact_path,
            "model_response_summary": parsed["discussion_response"],
            "intent_schema": certification["intent_schema"],
            "solver_output": {"strategy": certification["solver_strategy_used"], "diagnostics": certification["solver_diagnostics"]},
            "structured_operations_payload": operations,
            "validation_result": proposal_state["validation_result"],
            "raw_model_reply_excerpt": json.dumps(data, ensure_ascii=False)[:1200],
            "selected_route": parsed["selected_route"],
            "actual_route": parsed["actual_route"],
            "provider_used": data.get("provider_used"),
            "proposal_tier": parsed["proposal_tier"],
            "tier_label": parsed["tier_label"],
            "tier_rationale": parsed["tier_rationale"],
            "confidence_summary": parsed["confidence_summary"],
            "proposal_kind": parsed["proposal_kind"],
            "quality_signal": parsed["quality_signal"],
            "usage_telemetry": usage_telemetry,
            "geometry_status": certification["geometry_status"],
            "constraint_summary": certification["constraint_summary"],
            "solver_strategy_used": certification["solver_strategy_used"],
            "governance_timing": proposal_timing,
        },
    )
    proposal_state["proposal_artifact_path"] = proposal_artifact_path
    if certification["geometry_status"] == "invalid":
        geometry_failure_path = _workspace_record_failure(
            failure_type="geometry_validation_failure",
            reason="constraint_violations",
            details={
                "submission_id": submission_id,
                "proposal_id": proposal_id,
                "validation_result": certification["validation_result"],
                "solver_diagnostics": certification["solver_diagnostics"],
            },
        )
        proposal_state["geometry_failure_artifact_path"] = geometry_failure_path
    _workspace_save_proposal_state(proposal_state)
    _workspace_save_meta_state(
        {
            "last_submission": {
                "submission_id": submission_id,
                "artifact_path": submission_artifact_path,
                "board_state_hash": submission_artifact["board_state_hash"],
                "board_snapshot_ref": snapshot_path,
                "selected_route": selected_route,
            },
            "last_proposal": {
                "proposal_id": proposal_id,
                "artifact_path": proposal_artifact_path,
                "proposal_tier": parsed["proposal_tier"],
                "tier_label": parsed["tier_label"],
                "selected_route": parsed["selected_route"],
                "actual_route": parsed["actual_route"],
                "proposal_kind": parsed["proposal_kind"],
                "quality_signal": parsed["quality_signal"],
                "usage_telemetry": usage_telemetry,
                "geometry_status": certification["geometry_status"],
                "constraint_summary": certification["constraint_summary"],
                "solver_strategy_used": certification["solver_strategy_used"],
                "governance_timing": proposal_timing,
            }
        }
    )
    _workspace_append_discussion_message(
        "assistant",
        _workspace_timeline_proposal_text(
            proposal_id=proposal_id,
            selected_route=parsed["selected_route"],
            actual_route=parsed["actual_route"],
            tier_label=parsed["tier_label"],
            proposal_kind=parsed["proposal_kind"],
            quality_signal=parsed["quality_signal"],
            discussion_response=parsed["discussion_response"],
        ),
        source="workspace.proposal",
        message_type="proposal",
        details={
            "proposal_id": proposal_id,
            "proposal_tier": parsed["proposal_tier"],
            "tier_label": parsed["tier_label"],
            "selected_route": parsed["selected_route"],
            "actual_route": parsed["actual_route"],
            "proposal_kind": parsed["proposal_kind"],
            "quality_signal": parsed["quality_signal"],
            "geometry_status": certification["geometry_status"],
            "constraint_summary": certification["constraint_summary"],
            "solver_strategy_used": certification["solver_strategy_used"],
        },
    )
    _append_workspace_receipt(
        receipt_type="avatar.workspace.proposal.created",
        status="recorded",
        details={"proposal_id": proposal_id, "submission_id": submission_id, "artifact_path": proposal_artifact_path, "operation_count": len(operations), "proposal_tier": parsed["proposal_tier"], "selected_route": parsed["selected_route"], "actual_route": parsed["actual_route"], "geometry_status": certification["geometry_status"], "solver_strategy_used": certification["solver_strategy_used"]},
    )
    _emit_workspace_governance_receipt(
        receipt_type="proposal_created",
        proposal_id=proposal_id,
        extra={
            "submission_id": submission_id,
            "proposal_artifact_path": proposal_artifact_path,
            "governance_timing": proposal_timing,
        },
    )
    return {
        "proposal_state": proposal_state,
        "discussion_state": _workspace_load_discussion_state(),
        "meta": _workspace_load_meta_state(),
    }


@app.post("/api/workspace/assess")
async def assess_workspace_board(payload: dict):
    board_state = _workspace_load_board_state()
    meta = _workspace_load_meta_state()
    last_submission = meta.get("last_submission") if isinstance(meta, dict) else None
    selected_route = str((payload or {}).get("model_role") or "local").strip().lower() or "local"
    assessment_note = str((payload or {}).get("operator_note") or "").strip() or "Assess the current Planning Surface state."
    assessment_id = f"assessment_{uuid.uuid4().hex[:10]}"
    board_hash_value = board_state_hash(board_state)
    _workspace_append_discussion_message(
        "user",
        "\n".join(
            [
                "Planning Surface assessment requested.",
                f"Route: {_workspace_route_label(selected_route)}",
                f"Assessment: {_workspace_short(assessment_id)}",
                f"Board hash: {_workspace_short(board_hash_value, 12)}",
                f"Note: {assessment_note}",
            ]
        ),
        source="workspace.assess",
        message_type="assessment_request",
        details={"assessment_id": assessment_id, "selected_route": selected_route, "board_state_hash": board_hash_value},
    )
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                CBO_WORKSPACE_PROPOSAL,
                json={
                    "session_id": _WORKSPACE_SESSION_ID,
                    "model_role": selected_route,
                    "board_state": board_state,
                    "board_state_hash": board_hash_value,
                    "board_snapshot_ref": (last_submission or {}).get("board_snapshot_ref") or "workspace://no-snapshot",
                    "board_snapshot_sha256": (last_submission or {}).get("board_snapshot_sha256") or "workspace-no-snapshot",
                    "discussion_context": _workspace_filtered_proposal_context(_workspace_load_discussion_state().get("messages", [])),
                    "operator_note": assessment_note,
                    "assessment_only": True,
                },
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        try:
            error_payload = exc.response.json()
        except Exception:
            error_payload = {}
        detail = error_payload.get("detail") if isinstance(error_payload, dict) else None
        if isinstance(detail, dict) and (
            detail.get("reason") == "provider_overload"
            or _workspace_is_provider_overload(detail.get("raw_model_text_excerpt", ""))
        ):
            artifact_path = _workspace_record_failure(
                failure_type="provider_overload",
                reason="provider_overload",
                details={"assessment_id": assessment_id, "status_code": exc.response.status_code, "raw_reply_excerpt": detail.get("raw_model_text_excerpt", "")},
            )
            _workspace_append_discussion_message(
                "assistant",
                _workspace_timeline_failure_text(
                    selected_route=selected_route,
                    submission_id=assessment_id,
                    result_type="provider_overload",
                    summary="Planning Surface assessment hit a temporary provider overload before structured output was returned.",
                ),
                source="workspace.assess",
                message_type="failure",
                details={"artifact_path": artifact_path, "failure_type": "provider_overload", "assessment_id": assessment_id, "selected_route": selected_route},
            )
            raise HTTPException(status_code=503, detail={"reason": "provider_overload", "artifact_path": artifact_path})
        artifact_path = _workspace_record_failure(
            failure_type="assessment_failure",
            reason="workspace_assessment_transport_failure",
            details={"assessment_id": assessment_id, "status_code": exc.response.status_code, "response": exc.response.text[:400]},
        )
        _workspace_append_discussion_message(
            "assistant",
            _workspace_timeline_failure_text(
                selected_route=selected_route,
                submission_id=assessment_id,
                result_type="assessment_failure",
                summary=f"Planning Surface assessment failed with HTTP {exc.response.status_code}.",
            ),
            source="workspace.assess",
            message_type="failure",
            details={"artifact_path": artifact_path, "failure_type": "assessment_failure", "assessment_id": assessment_id, "selected_route": selected_route},
        )
        raise HTTPException(status_code=exc.response.status_code, detail={"reason": "workspace_assessment_transport_failure", "artifact_path": artifact_path})
    except Exception as exc:
        artifact_path = _workspace_record_failure(
            failure_type="assessment_failure",
            reason="workspace_assessment_transport_failure",
            details={"assessment_id": assessment_id, "error": str(exc)[:400]},
        )
        _workspace_append_discussion_message(
            "assistant",
            _workspace_timeline_failure_text(
                selected_route=selected_route,
                submission_id=assessment_id,
                result_type="assessment_failure",
                summary="Planning Surface assessment could not reach the structured lane.",
            ),
            source="workspace.assess",
            message_type="failure",
            details={"artifact_path": artifact_path, "failure_type": "assessment_failure", "assessment_id": assessment_id, "selected_route": selected_route},
        )
        raise HTTPException(status_code=502, detail={"reason": "workspace_assessment_transport_failure", "artifact_path": artifact_path})
    try:
        parsed = validate_workspace_proposal_response(data)
    except ValueError as exc:
        artifact_path = _workspace_record_failure(
            failure_type="assessment_failure",
            reason=str(exc),
            details={"assessment_id": assessment_id, "raw_reply_excerpt": json.dumps(data, ensure_ascii=False)[:1200]},
        )
        _workspace_append_discussion_message(
            "assistant",
            _workspace_timeline_failure_text(
                selected_route=selected_route,
                submission_id=assessment_id,
                result_type="structured_validation_failure",
                summary="Planning Surface assessment returned malformed structured output.",
            ),
            source="workspace.assess",
            message_type="failure",
            details={"artifact_path": artifact_path, "failure_type": str(exc), "assessment_id": assessment_id, "selected_route": selected_route},
        )
        raise HTTPException(status_code=422, detail={"reason": str(exc), "artifact_path": artifact_path})
    _workspace_append_discussion_message(
        "assistant",
        "\n".join(
            [
                f"Planning Surface assessment {_workspace_short(assessment_id)} ready.",
                f"Tier: {parsed['tier_label']}",
                f"Route: {_workspace_route_label(parsed['actual_route'])} (selected {_workspace_route_label(parsed['selected_route'])})",
                f"Kind: {parsed['proposal_kind'].replace('_', ' ')}",
                f"Quality: {parsed['quality_signal'].replace('_', ' ')}",
                parsed["discussion_response"],
            ]
        ),
        source="workspace.assess",
        message_type="assessment",
        details={
            "assessment_id": assessment_id,
            "proposal_tier": parsed["proposal_tier"],
            "tier_label": parsed["tier_label"],
            "selected_route": parsed["selected_route"],
            "actual_route": parsed["actual_route"],
        },
    )
    _append_workspace_receipt(
        receipt_type="avatar.workspace.assessment.recorded",
        status="recorded",
        details={"assessment_id": assessment_id, "selected_route": parsed["selected_route"], "actual_route": parsed["actual_route"], "proposal_tier": parsed["proposal_tier"]},
    )
    return {"assessment_id": assessment_id, "discussion_state": _workspace_load_discussion_state(), "meta": _workspace_load_meta_state()}


@app.post("/api/workspace/proposal/displayed")
def mark_workspace_proposal_displayed(payload: dict):
    proposal = _workspace_load_proposal_state()
    proposal_id = str((payload or {}).get("proposal_id") or "").strip()
    if not proposal or proposal.get("proposal_id") != proposal_id:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if not proposal.get("displayed_at"):
        displayed_at = _workspace_now_iso()
        proposal["displayed_at"] = displayed_at
        proposal["governance_timing"] = _workspace_governance_timing(
            proposal,
            proposal_displayed_at=displayed_at,
            queue_depth_observed=1,
            outcome="displayed",
        )
        _workspace_save_proposal_state(proposal)
        _append_workspace_receipt(
            receipt_type="avatar.workspace.proposal.displayed",
            status="displayed",
            details={"proposal_id": proposal_id},
        )
        _emit_workspace_governance_receipt(
            receipt_type="proposal_displayed",
            proposal_id=proposal_id,
            extra={"governance_timing": proposal.get("governance_timing")},
        )
    return {"proposal_state": proposal}


@app.post("/api/workspace/proposal/decision")
def decide_workspace_proposal(payload: dict):
    proposal = _workspace_load_proposal_state()
    if not proposal:
        raise HTTPException(status_code=404, detail="No active proposal")
    proposal_id = str((payload or {}).get("proposal_id") or "").strip()
    if proposal.get("proposal_id") != proposal_id:
        raise HTTPException(status_code=409, detail="Proposal superseded")
    action = str((payload or {}).get("action") or "").strip().lower()
    selected_operation_ids = {
        str(operation_id).strip()
        for operation_id in ((payload or {}).get("selected_operation_ids") or [])
        if str(operation_id).strip()
    }
    all_operations = proposal.get("operations") or []
    if action not in {"approve_all", "approve_selected", "reject_all"}:
        raise HTTPException(status_code=400, detail="unsupported_action")
    if not proposal.get("displayed_at"):
        raise HTTPException(status_code=409, detail="proposal_not_displayed")
    if proposal.get("geometry_status") == "invalid" and action != "reject_all":
        raise HTTPException(status_code=409, detail="proposal_not_certified")
    if action == "reject_all":
        decision_ts = _workspace_now_iso()
        governance_timing = _workspace_governance_timing(
            proposal,
            approval_decision_at=decision_ts,
            queue_depth_observed=1,
            queue_depth_after_decision=0,
            outcome="rejected",
        )
        rejected_ids = [operation["operation_id"] for operation in all_operations]
        approval_artifact = {
            "timestamp_utc": decision_ts,
            "proposal_id": proposal_id,
            "approved_operations": [],
            "rejected_operations": rejected_ids,
            "resulting_board_state_hash": board_state_hash(_workspace_load_board_state()),
            "approval_action": action,
            "geometry_status": proposal.get("geometry_status"),
            "governance_timing": governance_timing,
        }
        artifact_path = _workspace_write_artifact("approvals", proposal_id, approval_artifact)
        _workspace_save_meta_state({"last_decision": {**approval_artifact, "artifact_path": artifact_path}})
        _workspace_save_proposal_state(None)
        _append_workspace_receipt(
            receipt_type="avatar.workspace.approval.recorded",
            status="rejected",
            details={"proposal_id": proposal_id, "artifact_path": artifact_path, "approved_count": 0, "rejected_count": len(rejected_ids)},
        )
        _emit_workspace_governance_receipt(
            receipt_type="approval_rejected",
            proposal_id=proposal_id,
            reason=str((payload or {}).get("reason") or "operator_rejected"),
            extra={"approval_artifact_path": artifact_path, "governance_timing": governance_timing},
        )
        _workspace_append_discussion_message(
            "user",
            _workspace_timeline_decision_text(action=action, proposal_id=proposal_id, approved_count=0, rejected_count=len(rejected_ids)),
            source="workspace.decision",
            message_type="decision",
            details={"proposal_id": proposal_id, "action": action, "approved_count": 0, "rejected_count": len(rejected_ids)},
        )
        return {"proposal_state": None, "board_state": _workspace_load_board_state(), "meta": _workspace_load_meta_state(), "discussion_state": _workspace_load_discussion_state()}
    approved_operations = all_operations if action == "approve_all" else [operation for operation in all_operations if operation["operation_id"] in selected_operation_ids]
    if action == "approve_selected" and not approved_operations:
        raise HTTPException(status_code=400, detail="selected_operation_ids_required")
    rejected_ids = [operation["operation_id"] for operation in all_operations if operation not in approved_operations]
    board_before = _workspace_load_board_state()
    decision_ts = _workspace_now_iso()
    execution_started_at = _workspace_now_iso()
    attempt_timing = _workspace_governance_timing(
        proposal,
        approval_decision_at=decision_ts,
        execution_started_at=execution_started_at,
        queue_depth_observed=1,
        queue_depth_after_decision=0,
        outcome="execution_attempted",
    )
    _emit_workspace_governance_receipt(
        receipt_type="execution_attempted",
        proposal_id=proposal_id,
        extra={
            "action": action,
            "approved_operation_ids": [operation["operation_id"] for operation in approved_operations],
            "governance_timing": attempt_timing,
        },
    )
    try:
        next_board = apply_operations_to_board(board_before, approved_operations)
    except ValueError as exc:
        failure_timing = _workspace_governance_timing(
            proposal,
            approval_decision_at=decision_ts,
            execution_started_at=execution_started_at,
            execution_completed_at=_workspace_now_iso(),
            queue_depth_observed=1,
            queue_depth_after_decision=1,
            outcome="execution_failed",
        )
        artifact_path = _workspace_record_failure(
            failure_type="board_application_failure",
            reason=str(exc),
            details={
                "proposal_id": proposal_id,
                "approved_operation_ids": [operation["operation_id"] for operation in approved_operations],
                "governance_timing": failure_timing,
            },
        )
        _emit_workspace_governance_receipt(
            receipt_type="execution_failed",
            proposal_id=proposal_id,
            reason=str(exc),
            extra={
                "action": action,
                "failure_artifact_path": artifact_path,
                "approved_operation_ids": [operation["operation_id"] for operation in approved_operations],
                "governance_timing": failure_timing,
            },
        )
        raise HTTPException(status_code=409, detail={"reason": str(exc), "artifact_path": artifact_path})
    _workspace_save_undo_state(
        {
            "proposal_id": proposal_id,
            "created_at": _workspace_now_iso(),
            "board_state": board_before,
            "approved_operation_ids": [operation["operation_id"] for operation in approved_operations],
        }
    )
    next_board = _workspace_save_board_state(next_board)
    execution_completed_at = _workspace_now_iso()
    governance_timing = _workspace_governance_timing(
        proposal,
        approval_decision_at=decision_ts,
        execution_started_at=execution_started_at,
        execution_completed_at=execution_completed_at,
        queue_depth_observed=1,
        queue_depth_after_decision=0,
        outcome="approved",
    )
    approval_artifact = {
        "timestamp_utc": decision_ts,
        "proposal_id": proposal_id,
        "approved_operations": [operation["operation_id"] for operation in approved_operations],
        "rejected_operations": rejected_ids,
        "resulting_board_state_hash": board_state_hash(next_board),
        "approval_action": action,
        "geometry_status": proposal.get("geometry_status"),
        "execution_completed_at": execution_completed_at,
        "governance_timing": governance_timing,
    }
    artifact_path = _workspace_write_artifact("approvals", proposal_id, approval_artifact)
    _workspace_save_meta_state({"last_decision": {**approval_artifact, "artifact_path": artifact_path}})
    _workspace_save_proposal_state(None)
    _append_workspace_receipt(
        receipt_type="avatar.workspace.approval.recorded",
        status="approved",
        details={"proposal_id": proposal_id, "artifact_path": artifact_path, "approved_count": len(approved_operations), "rejected_count": len(rejected_ids)},
    )
    _emit_workspace_governance_receipt(
        receipt_type="approval_granted",
        proposal_id=proposal_id,
        extra={
            "approval_artifact_path": artifact_path,
            "approved_operation_ids": approval_artifact["approved_operations"],
            "governance_timing": governance_timing,
        },
    )
    _emit_workspace_governance_receipt(
        receipt_type="execution_succeeded",
        proposal_id=proposal_id,
        extra={
            "approval_artifact_path": artifact_path,
            "approved_operation_ids": approval_artifact["approved_operations"],
            "governance_timing": governance_timing,
        },
    )
    _workspace_append_discussion_message(
        "user",
        _workspace_timeline_decision_text(
            action=action,
            proposal_id=proposal_id,
            approved_count=len(approved_operations),
            rejected_count=len(rejected_ids),
        ),
        source="workspace.decision",
        message_type="decision",
        details={"proposal_id": proposal_id, "action": action, "approved_count": len(approved_operations), "rejected_count": len(rejected_ids)},
    )
    return {"proposal_state": None, "board_state": next_board, "meta": _workspace_load_meta_state(), "undo_state": _workspace_load_undo_state(), "discussion_state": _workspace_load_discussion_state()}


@app.post("/api/workspace/undo")
def undo_workspace_last_apply():
    undo_state = _workspace_load_undo_state()
    if not undo_state:
        raise HTTPException(status_code=404, detail="No undo state available")
    restored = _workspace_save_board_state(undo_state.get("board_state") or default_board_state())
    _workspace_save_undo_state(None)
    _append_workspace_receipt(
        receipt_type="avatar.workspace.undo.applied",
        status="reconciled",
        details={"proposal_id": undo_state.get("proposal_id"), "board_state_hash": board_state_hash(restored)},
    )
    _workspace_append_discussion_message(
        "user",
        f"Undo applied.\nProposal: {_workspace_short(str(undo_state.get('proposal_id') or ''))}",
        source="workspace.undo",
        message_type="decision",
        details={"proposal_id": undo_state.get("proposal_id"), "action": "undo"},
    )
    return {"board_state": restored, "undo_state": None, "meta": _workspace_load_meta_state(), "discussion_state": _workspace_load_discussion_state()}


# Single-page chat UI (inline so no static path / CORS)
INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CBO Avatar — Station Calyx</title>
  <style>
    :root {
      --bg: #0f1419;
      --surface: #1a2332;
      --border: #2d3a4d;
      --text: #e6edf3;
      --muted: #8b949e;
      --accent: #58a6ff;
      --green: #3fb950;
      --magenta: #d2a8ff;
      --red: #f85149;
    }
    * { box-sizing: border-box; }
    body {
      font-family: ui-monospace, "Cascadia Code", "SF Mono", Monaco, monospace;
      font-size: 14px;
      line-height: 1.5;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }
    header h1 { margin: 0; font-size: 1rem; font-weight: 600; }
    .controls {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    label { color: var(--muted); margin-right: 4px; }
    select, input[type="text"] {
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 6px 10px;
      border-radius: 6px;
      font-family: inherit;
    }
    select { min-width: 120px; }
    input[type="text"] { min-width: 80px; }
    #sessionId { width: 100px; }
    #sendBtn {
      background: var(--accent);
      color: var(--bg);
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
      font-family: inherit;
    }
    #sendBtn:hover { filter: brightness(1.1); }
    #sendBtn:disabled { opacity: 0.5; cursor: not-allowed; }
    main {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .msg { padding: 12px 16px; border-radius: 8px; max-width: 90%; }
    .msg.user { background: var(--surface); border: 1px solid var(--border); align-self: flex-end; }
    .msg.cbo { background: var(--surface); border-left: 3px solid var(--green); align-self: flex-start; white-space: pre-wrap; word-break: break-word; }
    .msg.second { background: var(--surface); border-left: 3px solid var(--magenta); align-self: flex-start; white-space: pre-wrap; word-break: break-word; }
    .msg .meta { font-size: 11px; color: var(--muted); margin-bottom: 6px; }
    .msg.error { border-left-color: var(--red); }
    footer {
      padding: 12px 16px;
      border-top: 1px solid var(--border);
      display: flex;
      gap: 8px;
      align-items: flex-start;
    }
    #userInput {
      flex: 1;
      min-height: 44px;
      max-height: 120px;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 10px 12px;
      border-radius: 8px;
      font-family: inherit;
      font-size: 14px;
      resize: vertical;
    }
    #userInput:focus { outline: none; border-color: var(--accent); }
  </style>
</head>
<body>
  <header>
    <h1>🍀 CBO Avatar — Station Calyx</h1>
    <nav style="margin-right:12px;"><a href="/" style="color:var(--accent);">Chat</a> | <a href="/whiteboard" style="color:var(--muted);">Whiteboard</a></nav>
    <div class="controls">
      <label>Model</label>
      <select id="modelRole">
        <option value="none">none (no LLM)</option>
        <option value="architect">architect (Claude)</option>
        <option value="workhorse">workhorse (OpenAI)</option>
        <option value="second_opinion">second (Kimi)</option>
        <option value="local">local (Ollama)</option>
      </select>
      <label>Tools</label>
      <select id="allowTools">
        <option value="on">on</option>
        <option value="off">off</option>
      </select>
      <label>Session</label>
      <input type="text" id="sessionId" value="home" placeholder="session id">
      <button id="sendBtn" type="button">Send</button>
    </div>
  </header>
  <main id="messages"></main>
  <footer>
    <textarea id="userInput" placeholder="Type a message or /search &lt;query&gt;…" rows="2"></textarea>
    <button id="sendBtn2" type="button">Send</button>
  </footer>
  <script>
    const messagesEl = document.getElementById("messages");
    const userInput = document.getElementById("userInput");
    const sessionId = document.getElementById("sessionId");
    const modelRole = document.getElementById("modelRole");
    const allowTools = document.getElementById("allowTools");
    const sendBtn = document.getElementById("sendBtn");
    const sendBtn2 = document.getElementById("sendBtn2");

    function append(className, body, meta) {
      const div = document.createElement("div");
      div.className = "msg " + className;
      if (meta) {
        const m = document.createElement("div");
        m.className = "meta";
        m.textContent = meta;
        div.appendChild(m);
      }
      const content = document.createElement("div");
      content.textContent = body;
      div.appendChild(content);
      messagesEl.appendChild(div);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    async function send() {
      const text = userInput.value.trim();
      if (!text) return;
      userInput.value = "";
      let userText = text;
      if (text.startsWith("/search ")) userText = "Please search the repo for: " + text.slice(8).trim();
      append("user", userText, "You");
      sendBtn.disabled = true;
      sendBtn2.disabled = true;
      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_text: userText,
            session_id: sessionId.value || "home",
            mode: "dev",
            allow_tools: allowTools.value === "on",
            model_role: modelRole.value,
            allow_second_opinion: modelRole.value === "second_opinion"
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || res.statusText);
        append("cbo", data.reply_text, "CBO · receipt " + (data.receipt_sha256 || "").slice(0, 12) + "…");
        if (data.second_opinion_text && data.second_opinion_text.trim())
          append("second", data.second_opinion_text.trim(), "Second opinion (Kimi)");
      } catch (e) {
        append("msg error", (e.message || String(e)), "Error");
      }
      sendBtn.disabled = false;
      sendBtn2.disabled = false;
    }

    sendBtn.addEventListener("click", send);
    sendBtn2.addEventListener("click", send);
    userInput.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } });
  </script>
</body>
</html>
"""

# LLM-powered whiteboard: literal canvas (pointer + keyboard), tasks, crew. Local only.
WHITEBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Whiteboard — Station Calyx</title>
  <style>
    :root {
      --bg: #0f1419;
      --surface: #1a2332;
      --border: #2d3a4d;
      --text: #e6edf3;
      --muted: #8b949e;
      --accent: #58a6ff;
      --green: #3fb950;
      --red: #f85149;
      --amber: #d29922;
    }
    * { box-sizing: border-box; }
    body { font-family: ui-monospace, "Cascadia Code", monospace; font-size: 14px; line-height: 1.5; background: var(--bg); color: var(--text); margin: 0; min-height: 100vh; display: flex; flex-direction: column; }
    header { padding: 12px 16px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
    header h1 { margin: 0; font-size: 1rem; font-weight: 600; }
    nav a { color: var(--accent); text-decoration: none; }
    nav a.active { color: var(--text); }
    main { flex: 1; display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 16px; padding: 16px; overflow: hidden; }
    @media (max-width: 800px) { main { grid-template-columns: 1fr; } }
    .panel { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px; display: flex; flex-direction: column; overflow: hidden; }
    .panel h2 { margin: 0 0 10px 0; font-size: 0.9rem; color: var(--muted); }
    .canvas-panel { grid-row: span 2; min-height: 200px; }
    #whiteboardCanvas { display: block; width: 100%; height: 280px; min-height: 200px; background: var(--bg); border-radius: 6px; cursor: crosshair; touch-action: none; user-select: none; -webkit-user-select: none; pointer-events: auto; }
    .canvas-toolbar { display: flex; gap: 8px; align-items: center; margin-top: 8px; }
    .canvas-toolbar button { background: var(--border); color: var(--text); border: none; padding: 4px 10px; border-radius: 4px; font-size: 12px; cursor: pointer; font-family: inherit; }
    .canvas-toolbar button.primary { background: var(--green); color: var(--bg); }
    .whiteboard-notes { margin-top: 8px; }
    .whiteboard-notes label { font-size: 11px; color: var(--muted); }
    .whiteboard-notes textarea { width: 100%; min-height: 56px; margin-top: 4px; background: var(--bg); border: 1px solid var(--border); color: var(--text); padding: 8px; border-radius: 6px; font-family: inherit; font-size: 13px; resize: vertical; }
    .task-list { flex: 1; overflow-y: auto; }
    .task { padding: 8px 10px; margin-bottom: 6px; border-radius: 6px; border-left: 3px solid var(--border); background: var(--bg); display: flex; justify-content: space-between; align-items: center; gap: 8px; transition: background 0.2s; }
    .task.just-added { background: rgba(63, 185, 80, 0.15); }
    .task.pending { border-left-color: var(--muted); }
    .task.in_progress { border-left-color: var(--amber); }
    .task.done { border-left-color: var(--green); }
    .task.failed { border-left-color: var(--red); }
    .task .title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .task .meta-line { font-size: 11px; color: var(--muted); margin-top: 4px; white-space: pre-wrap; word-break: break-word; }
    .task .result { font-size: 12px; color: var(--muted); margin-top: 4px; white-space: pre-wrap; word-break: break-word; max-height: 60px; overflow-y: auto; }
    .agent-list { display: flex; flex-direction: column; gap: 8px; }
    .agent { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 6px; background: var(--bg); border: 1px solid var(--border); }
    .agent .avatar { font-size: 1.5rem; width: 2rem; text-align: center; line-height: 1; }
    .agent.human .avatar { filter: sepia(0.3); }
    .agent .info { flex: 1; min-width: 0; }
    .agent .name { font-weight: 600; }
    .agent .role { font-size: 11px; color: var(--muted); }
    .agent .busy { font-size: 11px; color: var(--amber); }
    .add-task { display: flex; gap: 8px; margin-top: 8px; }
    .contract-form { display: grid; gap: 8px; margin-top: 8px; }
    .contract-form label { font-size: 11px; color: var(--muted); }
    .contract-form input, .contract-form textarea { width: 100%; background: var(--bg); border: 1px solid var(--border); color: var(--text); padding: 6px 10px; border-radius: 6px; font-family: inherit; }
    .contract-form textarea { min-height: 54px; resize: vertical; }
    .contract-form .inline-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
    .contract-form button { background: var(--accent); color: var(--bg); border: none; padding: 6px 12px; border-radius: 6px; font-weight: 600; cursor: pointer; font-family: inherit; }
    .add-task button:disabled { opacity: 0.5; cursor: not-allowed; }
    .contract-form button:disabled { opacity: 0.5; cursor: not-allowed; }
    .run-btn { font-size: 12px; padding: 4px 8px; background: var(--green); color: var(--bg); border: none; border-radius: 4px; cursor: pointer; font-family: inherit; }
    .run-btn:disabled { opacity: 0.5; cursor: not-allowed; background: var(--muted); }
    .run-btn.running { background: var(--amber); }
    .toast { position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%); background: var(--green); color: var(--bg); padding: 8px 16px; border-radius: 8px; font-size: 13px; z-index: 100; animation: fadeOut 2s ease 1s forwards; }
    @keyframes fadeOut { to { opacity: 0; pointer-events: none; } }
    .safety-note { font-size: 11px; color: var(--muted); margin-top: 8px; }
  </style>
</head>
<body>
  <header>
    <h1>Whiteboard — Station Calyx</h1>
    <nav><a href="/" style="color:var(--muted);">Chat</a> | <a href="/whiteboard" class="active">Whiteboard</a></nav>
  </header>
  <main>
    <div class="panel canvas-panel">
      <h2>Draw (pointer) + Notes (keyboard)</h2>
      <canvas id="whiteboardCanvas" width="600" height="280"></canvas>
      <div class="canvas-toolbar">
        <button type="button" id="clearCanvasBtn">Clear</button>
        <button type="button" class="primary" id="addFromWhiteboardBtn">Add as task from whiteboard</button>
      </div>
      <div class="whiteboard-notes">
        <label for="whiteboardNotes">Notes (keyboard) — shared with crew when you add as task or send to CBO:</label>
        <textarea id="whiteboardNotes" placeholder="Type notes, plans, or a task description…"></textarea>
      </div>
    </div>
    <div class="panel">
      <h2>Tasks</h2>
      <div class="contract-form">
        <div>
          <label for="taskTitle">OBJECTIVE</label>
          <input type="text" id="taskTitle" placeholder="Pocket objective…" />
        </div>
        <div class="inline-fields">
          <div>
            <label for="taskAllowedContext">ALLOWED_CONTEXT</label>
            <textarea id="taskAllowedContext" placeholder="One path, note, or scope line per row"></textarea>
          </div>
          <div>
            <label for="taskAllowedTools">ALLOWED_TOOLS</label>
            <textarea id="taskAllowedTools" placeholder="One tool per row. Use reason_only for no tools."></textarea>
          </div>
        </div>
        <div class="inline-fields">
          <div>
            <label for="taskExitCriteria">EXIT_CRITERIA</label>
            <textarea id="taskExitCriteria" placeholder="One completion check per row"></textarea>
          </div>
          <div>
            <label for="taskMaxRecursionDepth">MAX_RECURSION_DEPTH</label>
            <input type="number" id="taskMaxRecursionDepth" min="0" value="0" />
          </div>
        </div>
        <button type="button" id="addTaskBtn">Add pocket</button>
      </div>
      <div class="task-list" id="taskList"></div>
      <p class="safety-note">One task runs at a time (build safety). Run build_safety_check.ps1 before heavy builds.</p>
    </div>
    <div class="panel">
      <h2>The crew</h2>
      <div class="agent-list" id="agentList"></div>
    </div>
  </main>
  <div id="toast" class="toast" style="display:none;"></div>
  <script>
    const taskListEl = document.getElementById("taskList");
    const taskTitleEl = document.getElementById("taskTitle");
    const taskAllowedContextEl = document.getElementById("taskAllowedContext");
    const taskAllowedToolsEl = document.getElementById("taskAllowedTools");
    const taskExitCriteriaEl = document.getElementById("taskExitCriteria");
    const taskMaxRecursionDepthEl = document.getElementById("taskMaxRecursionDepth");
    const addTaskBtn = document.getElementById("addTaskBtn");
    const agentListEl = document.getElementById("agentList");
    const toastEl = document.getElementById("toast");
    const canvas = document.getElementById("whiteboardCanvas");
    const whiteboardNotes = document.getElementById("whiteboardNotes");
    const addFromWhiteboardBtn = document.getElementById("addFromWhiteboardBtn");
    const clearCanvasBtn = document.getElementById("clearCanvasBtn");
    let runInProgress = false;

    function showToast(msg) {
      toastEl.textContent = msg;
      toastEl.style.display = "block";
      toastEl.style.opacity = "1";
      setTimeout(function() { toastEl.style.display = "none"; }, 2500);
    }

    function parseList(raw) {
      return (raw || "").split(/\n|,/).map(function(item) { return item.trim(); }).filter(Boolean);
    }

    function pocketContractFromForm(objectiveFallback) {
      return {
        OBJECTIVE: (taskTitleEl.value || objectiveFallback || "").trim(),
        ALLOWED_CONTEXT: parseList(taskAllowedContextEl.value),
        ALLOWED_TOOLS: parseList(taskAllowedToolsEl.value),
        EXIT_CRITERIA: parseList(taskExitCriteriaEl.value),
        MAX_RECURSION_DEPTH: Number(taskMaxRecursionDepthEl.value || 0)
      };
    }

    function formatErrorDetail(detail) {
      if (!detail) return "Request failed";
      if (typeof detail === "string") return detail;
      if (detail.reason && Array.isArray(detail.contract_errors))
        return detail.reason + ": " + detail.contract_errors.join(", ");
      if (detail.reason && detail.max_recursion_depth !== undefined)
        return detail.reason + ": " + detail.requested_recursion_depth + " > " + detail.max_recursion_depth;
      if (detail.reason) return detail.reason;
      return JSON.stringify(detail);
    }

    function setupCanvas() {
      const ctx = canvas.getContext("2d");
      ctx.strokeStyle = "#e6edf3";
      ctx.lineWidth = 3;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      let drawing = false;
      let lastPoint = null;
      function pos(e) {
        const r = canvas.getBoundingClientRect();
        const scaleX = canvas.width / r.width, scaleY = canvas.height / r.height;
        const ev = e.touches ? e.touches[0] : e.changedTouches ? e.changedTouches[0] : e;
        return { x: (ev.clientX - r.left) * scaleX, y: (ev.clientY - r.top) * scaleY };
      }
      function startDraw(p) {
        drawing = true;
        lastPoint = p;
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
      }
      function continueDraw(p) {
        if (!drawing || !lastPoint) return;
        ctx.beginPath();
        ctx.moveTo(lastPoint.x, lastPoint.y);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
        lastPoint = p;
      }
      function endDraw() {
        drawing = false;
        lastPoint = null;
      }
      canvas.addEventListener("pointerdown", function(e) { e.preventDefault(); startDraw(pos(e)); });
      canvas.addEventListener("pointermove", function(e) { continueDraw(pos(e)); });
      canvas.addEventListener("pointerup", endDraw);
      canvas.addEventListener("pointerleave", endDraw);
    }
    setupCanvas();

    async function fetchTasks() {
      const r = await fetch("/api/whiteboard/tasks");
      if (!r.ok) throw new Error("Tasks API " + r.status + " " + r.statusText);
      const data = await r.json();
      return data.tasks || [];
    }

    async function fetchAgents() {
      const r = await fetch("/api/whiteboard/agents");
      if (!r.ok) throw new Error("Agents API " + r.status + " " + r.statusText);
      const data = await r.json();
      return data.agents || [];
    }

    function renderTask(task) {
      const div = document.createElement("div");
      div.className = "task " + (task.status || "pending");
      div.dataset.id = task.id;
      const contract = task.pocket_contract || {};
      const contractStatus = task.pocket_contract_status === "ready"
        ? "Contract ready · depth " + (task.current_recursion_depth || 0) + "/" + (contract.MAX_RECURSION_DEPTH ?? 0)
        : "Contract incomplete: " + ((task.pocket_contract_errors || []).join(", ") || "missing fields");
      const inner = document.createElement("div");
      inner.innerHTML = "<span class=\"title\">" + escapeHtml(task.title) + "</span>" +
        "<div class=\"meta-line\">" + escapeHtml(contractStatus) + "</div>" +
        "<div class=\"meta-line\">Tools: " + escapeHtml((contract.ALLOWED_TOOLS || []).join(", ") || "none declared") + "</div>" +
        (task.result_snippet ? "<div class=\"result\">" + escapeHtml(task.result_snippet) + "</div>" : "");
      div.appendChild(inner);
      const runBtn = document.createElement("button");
      runBtn.className = "run-btn" + (task.status === "in_progress" ? " running" : "");
      runBtn.textContent = task.pocket_contract_status !== "ready"
        ? "Contract required"
        : task.status === "in_progress"
        ? "Running…"
        : task.status === "done"
        ? "Re-run"
        : "Run with CBO";
      runBtn.disabled = runInProgress || task.pocket_contract_status !== "ready";
      runBtn.onclick = function() { runTask(task.id); };
      div.appendChild(runBtn);
      return div;
    }

    function escapeHtml(s) {
      const d = document.createElement("div");
      d.textContent = s;
      return d.innerHTML;
    }

    function renderAgent(agent, tasks) {
      const div = document.createElement("div");
      div.className = "agent" + (agent.avatar_type === "human" ? " human" : "");
      const currentId = agent.current_task_id;
      const currentTask = currentId ? tasks.find(function(t) { return t.id === currentId; }) : null;
      div.innerHTML = "<span class=\"avatar\">" + escapeHtml(agent.avatar || "") + "</span>" +
        "<div class=\"info\">" +
        "<div class=\"name\">" + escapeHtml(agent.display_name || "") + "</div>" +
        "<div class=\"role\">" + escapeHtml(agent.role || "") + "</div>" +
        (currentTask ? "<div class=\"busy\">Working on: " + escapeHtml(currentTask.title) + "</div>" : "") +
        "</div>";
      return div;
    }

    async function refresh() {
      try {
        const tasks = await fetchTasks();
        const agents = await fetchAgents();
        taskListEl.innerHTML = "";
        (tasks || []).forEach(function(t) { taskListEl.appendChild(renderTask(t)); });
        agentListEl.innerHTML = "";
        (agents || []).forEach(function(a) { agentListEl.appendChild(renderAgent(a, tasks || [])); });
      } catch (e) {
        showToast("Could not load tasks/crew: " + (e.message || String(e)));
      }
    }

    async function addTask(titleFromInput) {
      const title = (typeof titleFromInput === "string" ? titleFromInput : taskTitleEl.value).trim();
      if (!title) return null;
      const r = await fetch("/api/whiteboard/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title, pocket_contract: pocketContractFromForm(title) })
      });
      if (!r.ok) { var d = await r.json(); throw new Error(formatErrorDetail(d.detail)); }
      const task = await r.json();
      if (!titleFromInput) taskTitleEl.value = "";
      await refresh();
      return task.id;
    }

    function scrollToTaskAndHighlight(taskId) {
      var el = taskListEl.querySelector("[data-id=\"" + taskId + "\"]");
      if (el) { el.scrollIntoView({ behavior: "smooth", block: "nearest" }); el.classList.add("just-added"); setTimeout(function() { el.classList.remove("just-added"); }, 2500); }
    }

    async function onAddTaskClick() {
      const title = taskTitleEl.value.trim();
      if (!title) { showToast("Enter a task title"); return; }
      try {
        var id = await addTask(title);
        if (id) { showToast("Added"); scrollToTaskAndHighlight(id); }
      } catch (e) { showToast("Error: " + (e.message || String(e))); }
    }

    async function onAddFromWhiteboard() {
      var notes = whiteboardNotes.value.trim();
      var title = notes || "Whiteboard sketch / notes";
      try {
        var id = await addTask(title);
        if (id) { showToast("Added as task"); scrollToTaskAndHighlight(id); whiteboardNotes.value = ""; }
      } catch (e) { showToast("Error: " + (e.message || String(e))); }
    }

    clearCanvasBtn.addEventListener("click", function() {
      var ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      showToast("Canvas cleared");
    });

    async function runTask(taskId) {
      if (runInProgress) return;
      runInProgress = true;
      addTaskBtn.disabled = true;
      addFromWhiteboardBtn.disabled = true;
      await refresh();
      try {
        var r = await fetch("/api/whiteboard/tasks/" + taskId + "/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model_role: "local", allow_tools: true, session_id: "whiteboard", recursion_depth: 0 })
        });
        var data = await r.json();
        if (!r.ok) throw new Error(formatErrorDetail(data.detail));
        await refresh();
      } catch (e) {
        await refresh();
        showToast(e.message || String(e));
      } finally {
        runInProgress = false;
        addTaskBtn.disabled = false;
        addFromWhiteboardBtn.disabled = false;
        await refresh();
      }
    }

    addTaskBtn.addEventListener("click", onAddTaskClick);
    taskTitleEl.addEventListener("keydown", function(e) { if (e.key === "Enter") { e.preventDefault(); onAddTaskClick(); } });
    addFromWhiteboardBtn.addEventListener("click", onAddFromWhiteboard);
    refresh().catch(function() {});
  </script>
</body>
</html>
"""
