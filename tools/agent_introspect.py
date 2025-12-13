#!/usr/bin/env python3
"""
Agent Introspection Viewer (read-only)

Renders the latest introspection snapshot (and optional history tail) for a given agent.
Designed for Quiet Maintain oversight; no writes or behavior changes.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]
STATE_ROOT = ROOT / "state" / "agents"
SCHEMA_VIOLATION_LOG = ROOT / "logs" / "agent_schema_violations.jsonl"


def _log_schema_violation(agent_id: str, schema: str, errors: List[str], payload: dict) -> None:
    SCHEMA_VIOLATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id,
        "schema": schema,
        "errors": errors,
        "payload_excerpt": {k: payload.get(k) for k in list(payload)[:6]},
        "source": "agent_introspect",
    }
    with SCHEMA_VIOLATION_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _validate_introspection(snapshot: dict) -> Tuple[bool, List[str]]:
    required = [
        ("timestamp", str),
        ("agent_id", str),
        ("mandate_ref", str),
        ("lifecycle_phase", str),
        ("intent", str),
        ("current_task", str),
        ("inputs", dict),
        ("constraints", list),
        ("uncertainty", str),
        ("last_decision", str),
        ("planned_next_step", str),
        ("respect_frame", dict),
        ("health", dict),
    ]
    errors: List[str] = []
    for key, typ in required:
        if key not in snapshot:
            errors.append(f"missing field: {key}")
        elif not isinstance(snapshot[key], typ):
            errors.append(f"{key} type {type(snapshot[key]).__name__} != {typ.__name__}")
    rf = snapshot.get("respect_frame", {})
    if not isinstance(rf, dict):
        errors.append("respect_frame not object")
    else:
        if "laws" not in rf or not isinstance(rf.get("laws"), list):
            errors.append("respect_frame.laws missing/not list")
        if "respect_frame" not in rf or not isinstance(rf.get("respect_frame"), str):
            errors.append("respect_frame.respect_frame missing/not string")
    return (len(errors) == 0, errors)


def load_introspection(agent_id: str) -> dict:
    path = STATE_ROOT / agent_id / "introspection.json"
    if not path.exists():
        raise FileNotFoundError(f"introspection not found for agent {agent_id} at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    ok, errors = _validate_introspection(data)
    if not ok:
        _log_schema_violation(agent_id, "agent_introspection_v0.1", errors, data)
        data["_validation_warning"] = errors
    return data


def load_history(agent_id: str, tail: int) -> List[dict]:
    path = STATE_ROOT / agent_id / "introspection_history.jsonl"
    if not path.exists() or tail <= 0:
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    if tail < len(lines):
        lines = lines[-tail:]
    entries = []
    for line in lines:
        try:
            item = json.loads(line)
            ok, errors = _validate_introspection(item)
            if not ok:
                _log_schema_violation(agent_id, "agent_introspection_history_v0.1", errors, item)
                item["_validation_warning"] = errors
            entries.append(item)
        except json.JSONDecodeError:
            _log_schema_violation(agent_id, "agent_introspection_history_v0.1", ["json decode error"], {"raw": line})
            continue
    return entries


def render_snapshot(snapshot: dict) -> str:
    ordered_keys = [
        "timestamp",
        "agent_id",
        "mandate_ref",
        "lifecycle_phase",
        "intent",
        "current_task",
        "inputs",
        "constraints",
        "uncertainty",
        "last_decision",
        "planned_next_step",
        "respect_frame",
        "health",
    ]
    parts = []
    for key in ordered_keys:
        if key in snapshot:
            parts.append(f"{key}: {json.dumps(snapshot[key], ensure_ascii=False)}")
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render agent introspection (read-only)")
    ap.add_argument("--agent", required=True, help="Agent id (e.g., cp14_validator)")
    ap.add_argument("--history", type=int, default=0, help="Show the last N history entries")
    ap.add_argument("--raw", action="store_true", help="Print raw JSON instead of a human-friendly summary")
    args = ap.parse_args(argv)

    snapshot = load_introspection(args.agent)
    history = load_history(args.agent, args.history)

    if args.raw:
        print(json.dumps({"snapshot": snapshot, "history": history}, indent=2, ensure_ascii=False))
    else:
        print("=== current ===")
        print(render_snapshot(snapshot))
        if history:
            print("\n=== history tail ===")
            for idx, entry in enumerate(history, start=1):
                print(f"[{idx}] {entry.get('timestamp', '?')}: {entry.get('last_decision', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
