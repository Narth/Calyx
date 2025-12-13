#!/usr/bin/env python3
"""
CAS ingestion: read completed task events, compute CAS, append to logs/cas/events.jsonl

Usage:
  python -u tools/cas_ingest.py --event-file path/to/event.json
  # or feed JSON via stdin
  cat event.json | python -u tools/cas_ingest.py
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cas import cas_for_task, load_config, normalize_ctc

EVENT_LOG = ROOT / "logs" / "cas" / "events.jsonl"


def _read_event_from_file(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_event_from_stdin() -> Dict[str, Any]:
    return json.loads(sys.stdin.read())


def ingest(event: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load_config()
    medians = cfg.get("medians", {}) or {}

    metrics = event.get("metrics", {}) or {}
    # If CTC missing but cost present, compute it
    if metrics.get("CTC") is None:
        cost = event.get("cost", {}) or {}
        usd = float(cost.get("usd", 0.0))
        sec = float(cost.get("wall_time_sec", 0.0))
        toks = float(cost.get("tokens", 0.0))
        metrics["CTC"] = normalize_ctc(usd, sec, toks, medians)
    event["metrics"] = metrics

    cas_val = cas_for_task(metrics, medians)
    event["cas"] = cas_val
    event["cas_version"] = cfg.get("version", "0.1")
    if "ended_at" not in event:
        event["ended_at"] = datetime.now(timezone.utc).isoformat()

    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    return event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CAS ingest")
    parser.add_argument("--event-file", help="Path to event JSON; otherwise read stdin")
    args = parser.parse_args(argv)

    if args.event_file:
        event = _read_event_from_file(Path(args.event_file))
    else:
        event = _read_event_from_stdin()

    enriched = ingest(event)
    print(json.dumps(enriched, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
