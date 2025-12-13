#!/usr/bin/env python3
"""
CAS Monitor: computes rolling Station CAS and writes reports/cas_status.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cas import load_config, station_cas, load_events

EVENT_LOG = ROOT / "logs" / "cas" / "events.jsonl"
OUT_REPORT = ROOT / "reports" / "cas_status.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CAS Monitor")
    parser.add_argument("--days", type=int, default=None, help="Override rolling window days")
    args = parser.parse_args(argv)

    cfg = load_config()
    rolling_days = args.days or int(cfg.get("rolling_days", 30))

    events = load_events(EVENT_LOG)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=rolling_days)
    recent = []
    for e in events:
        try:
            ts = datetime.fromisoformat(e.get("ended_at", "").replace("Z", "+00:00"))
        except Exception:
            continue
        if ts >= cutoff:
            recent.append(e)

    cas_result = station_cas(recent, days=rolling_days)
    sample_size = cas_result.get("sample_size", 0)
    data_note = None
    if sample_size < 3:
        data_note = "CAS_DATA_SPARE; sample_size < 3"

    report = {
        "timestamp": now.isoformat(),
        "station_cas": cas_result.get("station_cas", 0.0),
        "cas_level": cas_result.get("cas_level"),
        "window_days": cas_result.get("window_days", rolling_days),
        "sample_size": sample_size,
        "difficulty_weights": (cfg.get("difficulty_weights") or {}),
        "data_note": data_note,
        "per_agent": cas_result.get("per_agent", {}),
    }

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
