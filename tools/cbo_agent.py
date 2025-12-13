#!/usr/bin/env python3
"""Simple CBO agent runner (dry-run by default).

Reads `outgoing/cbo/agent_tasks.json`, lists tasks, and for each task owned by this agent
it will "claim" it by writing an entry under `outgoing/cbo/claims/` and write a result
under `outgoing/cbo/results/`. By default the agent only simulates action (dry-run).

Usage:
  python -u tools/cbo_agent.py --owner cbo-agent
  python -u tools/cbo_agent.py --owner maintenance-agent --execute
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
AGENT_TASKS = ROOT / "outgoing" / "cbo" / "agent_tasks.json"
CLAIMS_DIR = ROOT / "outgoing" / "cbo" / "claims"
RESULTS_DIR = ROOT / "outgoing" / "cbo" / "results"


def load_tasks() -> Dict[str, Any]:
    try:
        return json.loads(AGENT_TASKS.read_text(encoding="utf-8"))
    except Exception:
        return {"tasks": []}


def ensure_dirs() -> None:
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def claim_task(task: Dict[str, Any], owner: str) -> Path:
    ts = int(time.time())
    claim_path = CLAIMS_DIR / f"claim_{task['id']}_{owner}_{ts}.json"
    payload = {"task_id": task['id'], "owner": owner, "claimed_at": ts}
    claim_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return claim_path


def write_result(task: Dict[str, Any], owner: str, success: bool, dry_run: bool, note: str = "") -> Path:
    ts = int(time.time())
    res_path = RESULTS_DIR / f"result_{task['id']}_{owner}_{ts}.json"
    payload = {
        "task_id": task['id'],
        "owner": owner,
        "ts": ts,
        "dry_run": bool(dry_run),
        "success": bool(success),
        "note": note,
    }
    res_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return res_path


def perform_task(task: Dict[str, Any], owner: str, execute: bool) -> tuple[bool, str]:
    # For safety, we don't execute arbitrary commands. If execute=True you could
    # add safe handlers for whitelisted commands. For now, just simulate and report.
    if execute:
        # Here we could inspect task['commands'] and run whitelisted actions.
        note = "EXECUTE requested but agent is in conservative mode; no commands executed"
        return False, note
    else:
        note = f"Dry-run: would run {len(task.get('commands', []))} commands; sample: {task.get('commands', [])[:1]}"
        return True, note


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cbo_agent")
    ap.add_argument("--owner", required=True, help="Owner name for this agent (e.g., cbo-agent)")
    ap.add_argument("--execute", action="store_true", help="If set, agent will execute whitelisted commands (NOT RECOMMENDED)")
    args = ap.parse_args(argv)

    ensure_dirs()
    data = load_tasks()
    tasks = data.get("tasks", [])
    owned = [t for t in tasks if t.get("owner") == args.owner]

    if not owned:
        print(f"No tasks for owner={args.owner}")
        return 0

    for t in owned:
        print(f"Claiming task {t['id']} ({t['title']})")
        claim_path = claim_task(t, args.owner)
        ok, note = perform_task(t, args.owner, args.execute)
        res_path = write_result(t, args.owner, ok, not args.execute, note)
        print(f"  Claimed: {claim_path.name}; Result: {res_path.name} -> success={ok}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
