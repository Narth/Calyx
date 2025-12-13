#!/usr/bin/env python3
"""Station Calyx maintenance runner."""

from __future__ import annotations

import sys
import argparse
import json
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
if str(DEFAULT_ROOT) not in sys.path:
    sys.path.insert(0, str(DEFAULT_ROOT))

from calyx.cbo import MaintenanceCycle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Station Calyx maintenance cycle")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Repository root path")
    parser.add_argument("--max-jsonl", type=int, default=500, help="Maximum JSONL rows to retain")
    parser.add_argument("--max-metrics", type=int, default=1000, help="Maximum metrics CSV rows to retain")
    parser.add_argument("--json", action="store_true", help="Print JSON summary instead of human text")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    cycle = MaintenanceCycle(root, max_jsonl_rows=args.max_jsonl, max_metrics_rows=args.max_metrics)
    result = cycle.run()

    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    else:
        print("Maintenance cycle complete.")
        if result.archived:
            print("  Archived:")
            for name in result.archived:
                print(f"    - {name}")
        if result.truncated:
            print("  Truncated:")
            for name in result.truncated:
                print(f"    - {name}")
        print(f"  Requeued failed tasks: {result.requeued}")
        print(f"  Vacuumed sqlite: {'yes' if result.vacuumed else 'no'}")
        if result.notes:
            print("  Notes:")
            for note in result.notes:
                print(f"    - {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
