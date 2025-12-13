"""CLI wrapper for Station Orchestrator (reflection-only).

Provides manual entrypoints to:
- station routine v0.2
- gated CTL log read
- gated summary/cache/drift evidence writes
"""

from __future__ import annotations

import argparse
import json

from tools.station_orchestrator import (
    orchestrate_log_read,
    orchestrate_station_routine,
    orchestrate_write_cache,
    orchestrate_write_drift_evidence,
    orchestrate_write_summary,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Station Orchestrator (reflection-only)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    routine = subparsers.add_parser("routine", help="Run Station Routine v0.2")
    routine.add_argument("--mode", choices=["basic", "extended"], default="extended")
    routine.add_argument("--hours", type=int, default=4)
    routine.add_argument("--intent", type=str, default=None)
    routine.add_argument(
        "--run-health-probe", action="store_true", help="Run health probe (extended)"
    )
    routine.add_argument(
        "--no-os-metrics",
        action="store_true",
        help="Skip OS metrics in health probe",
    )

    logread = subparsers.add_parser("logread", help="Gated CTL log read")
    logread.add_argument("--path", required=True, help="Path under logs/calyx/")
    logread.add_argument("--bytes", type=int, default=None, help="Bytes to read")

    summary = subparsers.add_parser("write-summary", help="Gated summary write")
    summary.add_argument("--filename", required=True)
    summary.add_argument("--content", required=True)
    summary.add_argument("--timebox-hours", type=int, default=2)

    cache = subparsers.add_parser("write-cache", help="Gated cache write")
    cache.add_argument("--path", required=True, help="Relative path under logs/calyx/cache/")
    cache.add_argument("--content", required=True)
    cache.add_argument("--timebox-hours", type=int, default=2)

    drift = subparsers.add_parser("write-drift", help="Gated drift evidence write")
    drift.add_argument("--content", required=True, help="JSON evidence string")
    drift.add_argument("--timebox-hours", type=int, default=2)

    args = parser.parse_args()

    if args.command == "routine":
        res = orchestrate_station_routine(
            mode=args.mode,
            hours=args.hours,
            intent_text=args.intent,
            run_health_probe=args.run_health_probe,
            include_os_metrics=not args.no_os_metrics,
        )
        print(json.dumps(res, indent=2, default=str))
    elif args.command == "logread":
        res = orchestrate_log_read(path=args.path, bytes_length=args.bytes)
        print(json.dumps(res, indent=2, default=str))
    elif args.command == "write-summary":
        res = orchestrate_write_summary(
            filename=args.filename,
            content=args.content,
            timebox_hours=args.timebox_hours,
        )
        print(json.dumps(res, indent=2, default=str))
    elif args.command == "write-cache":
        res = orchestrate_write_cache(
            relative_path=args.path,
            content=args.content,
            timebox_hours=args.timebox_hours,
        )
        print(json.dumps(res, indent=2, default=str))
    elif args.command == "write-drift":
        try:
            evidence = json.loads(args.content)
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON for drift evidence"}))
            return
        res = orchestrate_write_drift_evidence(
            evidence=evidence, timebox_hours=args.timebox_hours
        )
        print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
