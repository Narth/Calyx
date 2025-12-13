"""
Update or inspect Outcome Density run tasks (jsonl) without automation.

Usage examples:
  python -m benchmarks.tools.update_task_entry --run-id CB-2025-Q1-OD-001 --list-pending
  python -m benchmarks.tools.update_task_entry --run-id CB-2025-Q1-OD-001 --task-id OD-CALYX-01 \
      --start 2025-12-11T02:10:00Z --end 2025-12-11T02:17:20Z \
      --gpu 6.0 --ram 18.0 --duration 440 --insight 8 \
      --hallucination false --incomplete false \
      --notes "Clear framing, no hallucinations."

By default, resource_units will be auto-computed if duration, gpu, and ram are provided:
  resource_units = duration_sec * (gpu_vram_gb_peak + 0.3 * ram_gb_peak)

The script rewrites the run file in-place after making a .bak copy.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_run(path: Path) -> List[Dict[str, Any]]:
    lines = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return lines


def save_run(path: Path, records: List[Dict[str, Any]]) -> None:
    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def list_pending(records: List[Dict[str, Any]]) -> None:
    pending = [r for r in records if r.get("entry_type") == "task" and r.get("insight_quality") is None]
    if not pending:
        print("No pending tasks (all have insight_quality).")
        return
    print("Pending tasks (insight_quality is None):")
    for r in pending:
        print(f"- {r.get('task_id')} ({r.get('category')})")


def list_all(records: List[Dict[str, Any]]) -> None:
    for r in records:
        if r.get("entry_type") != "task":
            continue
        status = "pending" if r.get("insight_quality") is None else "scored"
        print(f"{r.get('task_id')} [{r.get('category')}] status={status}")


def update_task(
    records: List[Dict[str, Any]],
    task_id: str,
    start: Optional[str],
    end: Optional[str],
    duration: Optional[float],
    gpu: Optional[float],
    ram: Optional[float],
    insight: Optional[int],
    hallucination: Optional[bool],
    incomplete: Optional[bool],
    notes: Optional[str],
    resource_units: Optional[float],
) -> bool:
    updated = False
    for rec in records:
        if rec.get("entry_type") != "task":
            continue
        if rec.get("task_id") != task_id:
            continue
        if start is not None:
            rec["start_ts"] = start
        if end is not None:
            rec["end_ts"] = end
        if duration is not None:
            rec["duration_sec"] = duration
        if gpu is not None:
            rec["gpu_vram_gb_peak"] = gpu
        if ram is not None:
            rec["ram_gb_peak"] = ram
        if insight is not None:
            rec["insight_quality"] = insight
        if hallucination is not None:
            rec["hallucination"] = hallucination
        if incomplete is not None:
            rec["incomplete"] = incomplete
        if notes is not None:
            rec["notes"] = notes
        # auto-compute if not explicitly provided
        if resource_units is not None:
            rec["resource_units"] = resource_units
        elif duration is not None and gpu is not None and ram is not None:
            rec["resource_units"] = duration * (gpu + 0.3 * ram)
        updated = True
        break
    return updated


def parse_bool(val: Optional[str]) -> Optional[bool]:
    if val is None:
        return None
    v = val.lower()
    if v in ("true", "t", "1", "yes", "y"):
        return True
    if v in ("false", "f", "0", "no", "n"):
        return False
    raise ValueError(f"Cannot parse boolean from: {val}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update or inspect Outcome Density run tasks (jsonl).")
    parser.add_argument("--run-id", default="CB-2025-Q1-OD-001", help="Benchmark run ID (default: CB-2025-Q1-OD-001)")
    parser.add_argument("--run-file", help="Path to run jsonl; overrides --run-id if provided.")
    parser.add_argument("--task-id", help="Task ID to update.")
    parser.add_argument("--start", help="Start timestamp ISO 8601")
    parser.add_argument("--end", help="End timestamp ISO 8601")
    parser.add_argument("--duration", type=float, help="Duration in seconds")
    parser.add_argument("--gpu", type=float, help="GPU VRAM peak (GB)")
    parser.add_argument("--ram", type=float, help="RAM peak (GB)")
    parser.add_argument("--insight", type=int, help="Insight quality score 1-10")
    parser.add_argument("--hallucination", help="true/false")
    parser.add_argument("--incomplete", help="true/false")
    parser.add_argument("--resource-units", type=float, help="Override resource_units (optional)")
    parser.add_argument("--notes", help="Notes string")
    parser.add_argument("--list-pending", action="store_true", help="List tasks missing insight_quality.")
    parser.add_argument("--list-all", action="store_true", help="List all tasks with status.")
    args = parser.parse_args()

    run_path = Path(args.run_file) if args.run_file else Path("benchmarks/runs") / f"{args.run_id}.jsonl"
    if not run_path.exists():
        raise SystemExit(f"Run file not found: {run_path}")

    records = load_run(run_path)

    if args.list_pending:
        list_pending(records)
        return
    if args.list_all:
        list_all(records)
        return

    if not args.task_id:
        raise SystemExit("Provide --task-id to update a task, or use --list-pending/--list-all.")

    hall = parse_bool(args.hallucination) if args.hallucination is not None else None
    inc = parse_bool(args.incomplete) if args.incomplete is not None else None

    ok = update_task(
        records,
        task_id=args.task_id,
        start=args.start,
        end=args.end,
        duration=args.duration,
        gpu=args.gpu,
        ram=args.ram,
        insight=args.insight,
        hallucination=hall,
        incomplete=inc,
        notes=args.notes,
        resource_units=args.resource_units,
    )
    if not ok:
        raise SystemExit(f"Task not found or not updated: {args.task_id}")

    save_run(run_path, records)
    print(f"Updated {args.task_id} in {run_path}")


if __name__ == "__main__":
    main()
