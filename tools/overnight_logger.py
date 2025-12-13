"""Standalone snapshot logger that reuses overnight_shift utilities."""
from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path
from typing import Optional

try:
    from tools.overnight_shift import _snapshot  # type: ignore
except ImportError:
    from overnight_shift import _snapshot  # type: ignore

ROOT = Path(__file__).resolve().parents[1]


def _run(interval: int, output: Path, stop_event: threading.Event) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    while not stop_event.is_set():
        entry = _snapshot()
        with output.open("a", encoding="utf-8") as fh:
            fh.write(entry)
        if stop_event.wait(interval):
            break


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Capture overnight status snapshots.")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between snapshots (default 300).")
    parser.add_argument("--duration", type=int, default=0, help="Total run time seconds (0 = run indefinitely).")
    parser.add_argument(
        "--output",
        default="logs/overnight/overnight_shift.md",
        help="Relative path to the markdown log file.",
    )
    parser.add_argument("--once", action="store_true", help="Capture a single snapshot and exit.")
    args = parser.parse_args(argv)

    interval = max(10, int(args.interval))
    output = (ROOT / args.output).resolve()

    if args.once:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("a", encoding="utf-8") as fh:
            fh.write(_snapshot())
        return 0

    stop_event = threading.Event()
    thread = threading.Thread(target=_run, args=(interval, output, stop_event), daemon=True)
    thread.start()

    try:
        if args.duration > 0:
            time.sleep(args.duration)
            stop_event.set()
        else:
            while not stop_event.is_set():
                time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
    thread.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
