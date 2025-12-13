"""One-click Station startup (reflection-only).

Runs Station Routine v0.2 in extended mode with health probe by default,
and surfaces gated helpers via station orchestrator.
"""

from __future__ import annotations

import argparse
import json

from tools.station_orchestrator import orchestrate_station_routine


def main() -> None:
    parser = argparse.ArgumentParser(description="One-click Station Startup (reflection-only)")
    parser.add_argument("--hours", type=int, default=4, help="Lookback window for summaries")
    parser.add_argument("--intent", type=str, default=None, help="Optional session intent")
    parser.add_argument(
        "--no-health-probe", action="store_true", help="Skip health probe if desired"
    )
    args = parser.parse_args()

    res = orchestrate_station_routine(
        mode="extended",
        hours=args.hours,
        intent_text=args.intent,
        run_health_probe=not args.no_health_probe,
        include_os_metrics=True,
    )
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
