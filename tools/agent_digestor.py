"""
Agent digestor: consumes messages from outgoing/bus and generates
compact Markdown summaries under docs/agent_digests/.

Design goals
- Zero-LLM, fast, and safe (no repo modifications beyond docs/agent_digests)
- Writes its own heartbeat as agent{N}.lock so the Watcher shows activity
- Best-effort parsing of agent1's plan.json and audit.json

Usage examples
  # Run a single digest (if a message exists)
  python tools/agent_digestor.py --agent-id 2 --once

  # Loop forever, polling every 5s
  python tools/agent_digestor.py --agent-id 2 --poll-sec 5
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
DOCS = ROOT / "docs" / "agent_digests"
HB_PATH_TMPL = OUT / "{name}.lock"

# Local imports (no heavy deps)
try:
    from tools.agent_bus import list_messages, mark_processed
except Exception:
    def list_messages():  # type: ignore
        return []
    def mark_processed(p):  # type: ignore
        try:
            p.unlink(missing_ok=True)  # type: ignore[call-arg]
        except Exception:
            pass


def _write_hb(name: str, phase: str, status: str, extra: Optional[Dict[str, Any]] = None) -> None:
    try:
        d: Dict[str, Any] = {
            "name": name,
            "phase": phase,
            "status": status,
            "ts": time.time(),
        }
        if extra:
            d.update(extra)
        p = Path(str(HB_PATH_TMPL).format(name=name))
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _safe_read_json(p: Path) -> Dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _render_markdown(run_dir: Path, source_msg: Dict[str, Any]) -> str:
    audit = _safe_read_json(run_dir / "audit.json")
    plan = _safe_read_json(run_dir / "plan.json")
    goal = str(audit.get("goal") or source_msg.get("summary", {}).get("goal") or "(unknown)")
    steps = plan.get("steps") if isinstance(plan, dict) else []
    changed = audit.get("changed_files") if isinstance(audit, dict) else []
    status_message = audit.get("notes") or source_msg.get("summary", {}).get("status_message")
    ts = int(audit.get("timestamp") or source_msg.get("ts") or time.time())
    lines = [
        f"# Agent digest for run {run_dir.name}",
        "",
        f"- Timestamp: {ts}",
        f"- Goal: {goal}",
        f"- Status: {audit.get('backend', 'n/a')} | applied={audit.get('applied', False)}",
        "",
        "## Plan steps",
    ]
    if steps:
        for i, s in enumerate(steps, start=1):
            desc = s.get("description", "") if isinstance(s, dict) else str(s)
            files = ", ".join(s.get("files", [])) if isinstance(s, dict) else ""
            lines.append(f"{i}. {desc} ({files})")
    else:
        lines.append("(no steps available)")
    lines += [
        "",
        "## Changed files",
    ]
    if changed:
        for c in changed:
            lines.append(f"- {c}")
    else:
        lines.append("- (none)")
    if status_message:
        lines += [
            "",
            "## Status message",
            f"> {status_message}",
        ]
    # Quick links
    lines += [
        "",
        "## Artifacts",
        f"- Run directory: {run_dir}",
        f"- Audit: {run_dir / 'audit.json'}",
        f"- Plan: {run_dir / 'plan.json'}",
    ]
    return "\n".join(lines) + "\n"


def _process_one(agent_name: str, max_files: int) -> bool:
    msgs = list_messages()
    for p in msgs:
        try:
            raw = _safe_read_json(p)
            if not raw:
                mark_processed(p)
                continue
            # Only digest agent1 runs by default
            if str(raw.get("producer")) != "agent1":
                mark_processed(p)
                continue
            run_rel = raw.get("run_dir")
            run_dir = (ROOT / run_rel) if isinstance(run_rel, str) else None
            if not run_dir or not (run_dir / "audit.json").exists():
                mark_processed(p)
                continue
            # Reduce data assigned: skip heavy runs with too many changed files
            try:
                audit = _safe_read_json(run_dir / "audit.json")
                ch = audit.get("changed_files", []) if isinstance(audit, dict) else []
                if isinstance(ch, list) and len(ch) > int(max_files):
                    # Leave the message for a fuller agent later; do not consume
                    continue
            except Exception:
                pass
            _write_hb(agent_name, phase="digest", status="running", extra={"source": p.name, "run_dir": str(run_dir.relative_to(ROOT))})

            # Render summary
            DOCS.mkdir(parents=True, exist_ok=True)
            ts = int(time.time())
            out_file = DOCS / f"{run_dir.name}__{agent_name}__summary.md"
            md = _render_markdown(run_dir, raw)
            out_file.write_text(md, encoding="utf-8")

            _write_hb(agent_name, phase="digest", status="done", extra={"summary_file": str(out_file.relative_to(ROOT))})
            mark_processed(p)
            return True
        except Exception:
            try:
                _write_hb(agent_name, phase="digest", status="error", extra={"source": p.name})
            except Exception:
                pass
            # Do not requeue broken files; move on
            try:
                mark_processed(p)
            except Exception:
                pass
    return False


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Consume bus messages and write digest summaries")
    ap.add_argument("--agent-id", type=int, default=None, help="Heartbeat agent id (numeric)")
    ap.add_argument("--agent-name", type=str, default=None, help="Heartbeat agent name (e.g., agent1a)")
    ap.add_argument("--poll-sec", type=int, default=2, help="Polling interval in seconds (default 2)")
    ap.add_argument("--max-files", type=int, default=5, help="Maximum changed files allowed to digest (default 5)")
    ap.add_argument("--once", action="store_true", help="Process at most one message and exit")
    args = ap.parse_args(argv)

    if args.agent_name:
        agent_name = str(args.agent_name)
    else:
        aid = int(args.agent_id or 2)
        agent_name = f"agent{max(1, min(99, aid))}"
    _write_hb(agent_name, phase="idle", status="running")
    try:
        while True:
            found = _process_one(agent_name, max_files=int(args.max_files))
            if args.once:
                break
            time.sleep(max(1, int(args.poll_sec)))
    finally:
        _write_hb(agent_name, phase="idle", status="done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
