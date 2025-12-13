"""
Publish the most recent agent run to the file bus (outgoing/bus) as producer=agent1.

This avoids invoking the LLM and is safe to run even when llama-cpp isn't installed.
Digestors (agents 2–4) can consume the message and generate summaries.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
BUS = OUT / "bus"


def _latest_run_dir() -> Optional[Path]:
    runs = sorted([p for p in OUT.glob("agent_run_*") if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
    for rd in runs:
        if (rd / "audit.json").exists():
            return rd
    return None


def main(argv: list[str] | None = None) -> int:
    try:
        # Import locally to avoid hard dependency if the module layout changes.
        sys.path.append(str((ROOT / "tools").resolve()))
        from agent_bus import publish_message  # type: ignore
    except Exception as exc:
        print(f"Error: cannot import agent_bus: {exc}", file=sys.stderr)
        return 2

    rd = _latest_run_dir()
    if not rd:
        print("No recent agent_run_* with audit.json found; nothing to publish.")
        return 0

    rel = str(rd.relative_to(ROOT))
    # Try to extract a bit of context for the summary
    try:
        audit = json.loads((rd / "audit.json").read_text(encoding="utf-8"))
    except Exception:
        audit = {}
    summary = {
        "applied": bool(audit.get("applied")),
        "changed_files": audit.get("changed_files", []),
        "status_message": audit.get("notes", ""),
        "goal": audit.get("goal", "(unknown)"),
    }

    publish_message(producer="agent1", run_dir_rel=rel, status="done", summary=summary)
    BUS.mkdir(parents=True, exist_ok=True)
    print(f"Published last run to bus: {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
