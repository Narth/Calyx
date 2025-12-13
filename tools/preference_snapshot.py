#!/usr/bin/env python3
"""
Preference Snapshot Generator

Reads lightweight interaction context and writes a snapshot to outgoing/preferences/.
Intended for weekly alignment: captures participants, last tone map, and LLM readiness.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
STATE_COMM = ROOT / "state" / "comm_context.json"
LOCK_LLM = ROOT / "outgoing" / "llm_ready.lock"
OUT_DIR = ROOT / "outgoing" / "preferences"


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def generate_snapshot() -> Path:
    ts = datetime.now(timezone.utc)
    comm = _read_json(STATE_COMM)
    llm = _read_json(LOCK_LLM)

    participants = comm.get("participants", [])
    tone = comm.get("last_tone", {})

    llm_status = llm.get("status")
    llm_msg = llm.get("status_message")
    llm_probe_ms = llm.get("probe_latency_ms")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fname = OUT_DIR / f"preference_snapshot_{ts.strftime('%Y%m%dT%H%M%SZ')}.md"

    lines = [
        f"# Preference Snapshot — {ts.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## Participants",
        f"- Count: {len(participants)}",
        f"- List: {', '.join(participants) if participants else 'none'}",
        "",
        "## Last Tone Map",
        *(f"- {agent}: {tone.get(agent)}" for agent in sorted(tone.keys())),
        "",
        "## LLM Readiness",
        f"- status: {llm_status}",
        f"- message: {llm_msg}",
        f"- probe_latency_ms: {llm_probe_ms}",
    ]
    fname.write_text("\n".join(lines), encoding="utf-8")
    return fname


def main() -> int:
    path = generate_snapshot()
    print(f"Wrote snapshot: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
