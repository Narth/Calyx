#!/usr/bin/env python3
"""
Log a free-model adversarial evaluation to logs/free_model_evals.jsonl.

Usage:
  python tools/log_free_model_eval.py --task-id adv-hc-001 --model-name "gpt-free" --raw-json-file resp.json --assessment drift --notes "auto-fixed timeline"

If --raw-json-file is omitted, the tool reads JSON from stdin.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "logs" / "free_model_evals.jsonl"


def load_raw_json(args: argparse.Namespace) -> str:
    if args.raw_json_file:
        return Path(args.raw_json_file).read_text(encoding="utf-8")
    data = sys.stdin.read()
    if not data.strip():
        raise SystemExit("No JSON provided (stdin is empty).")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description="Log free-model eval result")
    ap.add_argument("--task-id", required=True, help="Task ID (e.g., adv-hc-001)")
    ap.add_argument("--model-name", required=True, help="Model identifier (string)")
    ap.add_argument("--experiment", default="Adversarial Suite Cross-Eval v0", help="Experiment name")
    ap.add_argument("--raw-json-file", help="Path to JSON response file; if omitted, read from stdin")
    ap.add_argument("--assessment", choices=["aligned", "drift", "severe"], default="drift", help="Governance assessment flag")
    ap.add_argument("--notes", default="", help="Optional short notes")
    args = ap.parse_args()

    raw_text = load_raw_json(args)

    # hash
    hash_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    # attempt to parse to ensure valid JSON, but store raw
    try:
        parsed: Dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON: {e}")

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "experiment": args.experiment,
        "task_id": args.task_id,
        "model_name": args.model_name,
        "raw_output": parsed,
        "hash_sha256": hash_sha256,
        "governance_assessment": args.assessment,
        "notes": args.notes,
    }

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"[OK] Logged to {LOG_PATH} (hash {hash_sha256})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
