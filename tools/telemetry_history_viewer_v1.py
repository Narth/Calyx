"""
Telemetry History Viewer v1 (frame: telemetry_history_viewer_v1)

Usage examples:
  python tools/telemetry_history_viewer_v1.py --mode timeline --last 10
  python tools/telemetry_history_viewer_v1.py --mode summary --since 2025-12-01 --out reports/telemetry/history/custom_report.md

Modes:
  timeline - render a markdown table of recent snapshots
  summary  - aggregate min/avg/max statistics over selected snapshots

Inputs:
  --last N           number of most recent snapshots (default 10)
  --since YYYY-MM-DD filter snapshots at or after this date (optional)
  --out PATH         optional report path; defaults to reports/telemetry/history/thv_<mode>_<timestamp>.md

Safe mode: read-only telemetry, append-only reports. No schedulers or background tasks.
"""
import argparse
import datetime as dt
import glob
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

DEFAULT_LOG_GLOB = "logs/telemetry/normalized/tnl_snapshot_*.jsonl"
DEFAULT_REPORT_DIR = Path("reports/telemetry/history")
INDEX_PATH = DEFAULT_REPORT_DIR / "index.md"
FRAME = "telemetry_history_viewer_v1"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Telemetry History Viewer v1", add_help=True)
    parser.add_argument("--mode", choices=["timeline", "summary"], required=True, help="View mode")
    parser.add_argument("--last", type=int, default=10, help="Number of most recent snapshots to include")
    parser.add_argument("--since", type=str, default=None, help="Filter snapshots since YYYY-MM-DD (optional)")
    parser.add_argument("--out", type=str, default=None, help="Optional output markdown path")
    return parser.parse_args()


def _to_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        fval = float(val)
    except (ValueError, TypeError):
        return None
    return fval


def _load_snapshots(pattern: str, since: Optional[dt.datetime], last: int) -> List[Dict[str, Any]]:
    files = sorted(glob.glob(pattern))
    snapshots: List[Dict[str, Any]] = []
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts_raw = data.get("timestamp")
            try:
                ts = dt.datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else None
            except Exception:
                ts = None
            data["_parsed_ts"] = ts
            snapshots.append(data)
    snapshots.sort(key=lambda x: x.get("_parsed_ts") or dt.datetime.min)
    if since:
        snapshots = [s for s in snapshots if s.get("_parsed_ts") and s["_parsed_ts"] >= since]
    if last and len(snapshots) > last:
        snapshots = snapshots[-last:]
    return snapshots


def _format_val(val: Any, suffix: str = "", precision: int = 1) -> str:
    fval = _to_float(val)
    if fval is None:
        return "n/a"
    if precision is None:
        return f"{fval}{suffix}"
    return f"{fval:.{precision}f}{suffix}"


def _format_bytes_per_sec(val: Any) -> str:
    fval = _to_float(val)
    if fval is None:
        return "n/a"
    units = ["B/s", "KB/s", "MB/s", "GB/s"]
    idx = 0
    while fval >= 1024 and idx < len(units) - 1:
        fval /= 1024.0
        idx += 1
    return f"{fval:.2f} {units[idx]}"


def _stats(values: Sequence[Any]) -> Optional[Dict[str, float]]:
    nums = [v for v in (_to_float(x) for x in values) if v is not None]
    if not nums:
        return None
    return {"min": min(nums), "avg": sum(nums) / len(nums), "max": max(nums)}


def _write_index(report_path: Path, count: int) -> None:
    DEFAULT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with INDEX_PATH.open("a", encoding="utf-8") as f:
        f.write(f"- {dt.datetime.now().isoformat()} :: {report_path.as_posix()} :: {count} snapshots\n")


def _timeline_table(snaps: List[Dict[str, Any]]) -> str:
    headers = [
        "Timestamp",
        "CPU%",
        "RAM used/total (GB)",
        "RAM%",
        "Disk R/W",
        "Net Rx/Tx",
        "GPU%",
        "Displays",
        "SimNodes",
    ]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join([" --- "] * len(headers)) + "|"]
    for s in snaps:
        ts = s.get("timestamp", "n/a")
        cpu = _format_val(s.get("cpu_load_pct"))
        ram_used = _format_val(s.get("ram_used_gb"), precision=2)
        ram_total = _format_val(s.get("ram_total_gb"), precision=2)
        ram_pct = _format_val(s.get("ram_load_pct"))
        disk = f"{_format_bytes_per_sec(s.get('disk_read_bps'))} / {_format_bytes_per_sec(s.get('disk_write_bps'))}"
        net = f"{_format_bytes_per_sec(s.get('net_rx_bps'))} / {_format_bytes_per_sec(s.get('net_tx_bps'))}"
        gpu = _format_val(s.get("gpu_load_pct")) if s.get("gpu_present") else "n/a"
        displays = str(s.get("display_count", "n/a"))
        sim = str(s.get("simulated_cluster_nodes", "n/a"))
        lines.append(
            f"| {ts} | {cpu} | {ram_used} / {ram_total} | {ram_pct} | {disk} | {net} | {gpu} | {displays} | {sim} |"
        )
    return "\n".join(lines)


def _summary_section(snaps: List[Dict[str, Any]]) -> str:
    def gather(key: str) -> List[Any]:
        return [s.get(key) for s in snaps if key in s]

    sections = ["## Telemetry Summary (THVv1)"]
    metrics = {
        "CPU load %": gather("cpu_load_pct"),
        "RAM load %": gather("ram_load_pct"),
        "Commit GB": gather("commit_gb"),
        "Disk read B/s": gather("disk_read_bps"),
        "Disk write B/s": gather("disk_write_bps"),
        "Net rx B/s": gather("net_rx_bps"),
        "Net tx B/s": gather("net_tx_bps"),
    }
    gpu_vals = [s.get("gpu_load_pct") for s in snaps if s.get("gpu_present")]
    if gpu_vals:
        metrics["GPU load %"] = gpu_vals

    for name, vals in metrics.items():
        stats = _stats(vals)
        if not stats:
            sections.append(f"- {name}: n/a")
            continue
        sections.append(f"- {name}: min {stats['min']:.2f}, avg {stats['avg']:.2f}, max {stats['max']:.2f}")
    return "\n".join(sections)


def _ensure_report_path(out_path: Optional[str], mode: str) -> Path:
    DEFAULT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if out_path:
        return Path(out_path)
    name = f"thv_{mode}_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    return DEFAULT_REPORT_DIR / name


def main() -> None:
    args = _parse_args()
    since_dt = None
    if args.since:
        try:
            since_dt = dt.datetime.fromisoformat(args.since)
        except ValueError:
            print("[WARN] --since not parseable; ignoring")
            since_dt = None

    snaps = _load_snapshots(DEFAULT_LOG_GLOB, since_dt, args.last)
    report_path = _ensure_report_path(args.out, args.mode)

    if not snaps:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("a", encoding="utf-8") as f:
            f.write(f"# Telemetry History Viewer (empty)\nNo snapshots found for pattern {DEFAULT_LOG_GLOB}.\n")
        print(f"[THV] No snapshots found. Empty report at {report_path}")
        return

    report_lines = [f"# Telemetry History Viewer v1 ({FRAME})", ""]
    report_lines.append(f"Snapshots included: {len(snaps)}")
    report_lines.append("")

    if args.mode == "timeline":
        report_lines.append("## Timeline")
        report_lines.append(_timeline_table(snaps))
        report_lines.append("")
        report_lines.append(_summary_section(snaps))
    elif args.mode == "summary":
        report_lines.append(_summary_section(snaps))
    else:
        report_lines.append("Unsupported mode")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    _write_index(report_path, len(snaps))

    print(f"[THV] Mode={args.mode} snapshots={len(snaps)} -> {report_path}")
    if args.mode == "timeline":
        print(_timeline_table(snaps))
    else:
        print(_summary_section(snaps))


if __name__ == "__main__":
    main()
