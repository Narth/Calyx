"""
OD Prompt Phase Logger

Append-only helper to mark PROMPT_START and PROMPT_END for Outcome Density runs.
This is the ground-truth source for prompt timing; no heuristics required.

Usage:
  python benchmarks/tools/od_phase_logger.py --run-id OD-2025-12-13T06-00-UTC --prompt-id OD-01 --event PROMPT_START
  python benchmarks/tools/od_phase_logger.py --run-id OD-2025-12-13T06-00-UTC --prompt-id OD-01 --event PROMPT_END

Fields:
  timestamp (ISO8601 UTC, ms)
  event: PROMPT_START | PROMPT_END
  run_id: shared across the OD session
  prompt_id: e.g., OD-01 .. OD-20

Output:
  logs/system/prompt_phases.jsonl (append-only)
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def log_phase(event: str, run_id: str, prompt_id: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "timestamp": now_iso(),
        "event": event,
        "run_id": run_id,
        "prompt_id": prompt_id,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Logged {event} for {prompt_id} run {run_id} -> {path}")


def main():
    parser = argparse.ArgumentParser(description="Append prompt phase markers for OD runs.")
    parser.add_argument("--run-id", required=True, help="Shared run ID, e.g., OD-2025-12-13T06-00-UTC")
    parser.add_argument("--prompt-id", required=True, help="Prompt ID, e.g., OD-01")
    parser.add_argument(
        "--event",
        required=True,
        choices=["PROMPT_START", "PROMPT_END"],
        help="Phase marker event",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("logs/system/prompt_phases.jsonl"),
        help="Append-only phase log (default logs/system/prompt_phases.jsonl)",
    )
    args = parser.parse_args()
    log_phase(args.event, args.run_id, args.prompt_id, args.output)


if __name__ == "__main__":
    main()
