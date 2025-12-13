#!/usr/bin/env python3
"""
Bloom-mode dispatcher for Station Calyx.

Reads bloom objectives from config.yaml and triggers targeted agent_scheduler
runs so each multimodal pillar receives the intended curriculum task.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.yaml"
SCHEDULER = ROOT / "tools" / "agent_scheduler.py"


def load_objectives() -> Dict[str, Dict[str, str]]:
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    scheduler = (data.get("settings", {}) or {}).get("scheduler", {}) if "settings" in data else data.get("scheduler", {})
    bloom = scheduler.get("bloom_mode", {}) if scheduler else {}
    if not bloom.get("enabled"):
        raise RuntimeError("Bloom mode disabled in config.yaml; refusing to dispatch.")
    objectives = bloom.get("objectives") or {}
    if not objectives:
        raise RuntimeError("No bloom objectives defined in config.yaml under scheduler.bloom_mode.objectives.")
    return objectives


def _normalize_agent_id(agent_id: str) -> int:
    try:
        return int(agent_id)
    except ValueError:
        stripped = agent_id.lower().replace("agent", "")
        return int(stripped)


def build_command(agent_id: str, objective: Dict[str, str]) -> List[str]:
    numeric_id = _normalize_agent_id(agent_id)
    cmd = [
        sys.executable,
        str(SCHEDULER),
        "--run-once",
        "--agent-id",
        str(numeric_id),
        "--mode",
        objective.get("mode", "tests"),
        "--goal",
        objective["goal"],
    ]
    agent_args = objective.get("agent_args")
    if agent_args:
        cmd.extend(["--agent-args", agent_args])
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch bloom-mode objectives via agent_scheduler.")
    parser.add_argument("--agents", nargs="*", help="Subset of agent ids to run (default: all defined).")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing.")
    args = parser.parse_args()

    objectives = load_objectives()
    target_agents = args.agents or list(objectives.keys())

    results = []
    for agent_id in target_agents:
        if agent_id not in objectives:
            print(f"[skip] Agent {agent_id} not defined in bloom objectives.")
            continue
        objective = objectives[agent_id]
        cmd = build_command(agent_id, objective)
        if args.dry_run:
            print("[dry-run]", " ".join(f'"{c}"' if " " in c else c for c in cmd))
            results.append((agent_id, 0, "dry-run"))
            continue
        print(f"[dispatch] agent {agent_id} -> {objective['goal'][:80]}...")
        proc = subprocess.run(cmd, cwd=ROOT)
        results.append((agent_id, proc.returncode, "ok" if proc.returncode == 0 else "error"))

    print("\nSummary:")
    for agent_id, rc, status in results:
        print(f"  agent {agent_id}: rc={rc} status={status}")
    failures = [r for r in results if r[1] != 0]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
