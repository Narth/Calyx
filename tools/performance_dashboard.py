#!/usr/bin/env python3
"""
Live Performance Dashboard Generator for Station Calyx.

Aggregates recent TES metrics, resource usage, and agent activity to produce a
lightweight HTML dashboard under reports/live_dashboard.html. The output page
includes a meta refresh (default 30 seconds) so operators can point a browser
at the file for near-real-time awareness.
"""

from __future__ import annotations

import argparse
import csv
import html
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import psutil

ROOT = Path(__file__).resolve().parents[1]
METRICS_CSV = ROOT / "logs" / "agent_metrics.csv"
OUTPUT_DEFAULT = ROOT / "reports" / "live_dashboard.html"


def _load_recent_metrics(limit: int) -> List[Dict[str, str]]:
    if not METRICS_CSV.exists():
        return []
    rows: List[Dict[str, str]] = []
    with METRICS_CSV.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        rows.extend(reader)
    return rows[-limit:] if rows else []


def _safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: str, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _percentiles(values: List[float], targets: Tuple[float, float]) -> Tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    sorted_vals = sorted(values)
    results = []
    for target in targets:
        idx = target * (len(sorted_vals) - 1)
        lower = int(idx)
        upper = min(lower + 1, len(sorted_vals) - 1)
        weight = idx - lower
        interp = sorted_vals[lower] * (1 - weight) + sorted_vals[upper] * weight
        results.append(interp)
    return (results[0], results[1])


def _aggregate_metrics(rows: List[Dict[str, str]]) -> Dict[str, object]:
    tes_values = [_safe_float(r.get("tes", "0")) for r in rows if r.get("tes")]
    duration_values = [_safe_float(r.get("duration_s", "0")) for r in rows if r.get("duration_s")]
    completion = sum(1 for r in rows if (r.get("status") or "").lower() == "done")
    changed_values = [_safe_int(r.get("changed_files", "0")) for r in rows if r.get("changed_files")]
    success_rate = (completion / len(rows)) * 100 if rows else 0.0
    tes_avg = (sum(tes_values) / len(tes_values)) if tes_values else 0.0
    tes_recent = tes_values[-1] if tes_values else 0.0
    duration_avg = (sum(duration_values) / len(duration_values)) if duration_values else 0.0
    footprint_avg = (sum(changed_values) / len(changed_values)) if changed_values else 0.0
    duration_p50, duration_p95 = _percentiles(duration_values, (0.5, 0.95))
    return {
        "tes_average": tes_avg,
        "tes_recent": tes_recent,
        "success_rate": success_rate,
        "duration_average": duration_avg,
        "duration_p50": duration_p50,
        "duration_p95": duration_p95,
        "footprint_average": footprint_avg,
        "sample": rows,
    }


def _system_snapshot() -> Dict[str, object]:
    vm = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)
    processes = list(psutil.process_iter(attrs=["pid", "name", "username"]))
    python_procs = [
        p.info for p in processes if "python" in (p.info.get("name") or "").lower()
    ]
    locks_dir = ROOT / "outgoing"
    lock_files = sorted(p.name for p in locks_dir.glob("*.lock")) if locks_dir.exists() else []
    return {
        "memory_percent": vm.percent,
        "memory_available_mb": round(vm.available / (1024 * 1024), 1),
        "cpu_percent": cpu,
        "process_count": len(processes),
        "python_process_count": len(python_procs),
        "lock_files": lock_files,
    }


def _render_dashboard(
    metrics: Dict[str, object],
    system: Dict[str, object],
    rows: List[Dict[str, str]],
    refresh_seconds: int,
) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    recent_rows_html = "\n".join(
        f"<tr><td>{html.escape(r.get('iso_ts', ''))}</td>"
        f"<td>{html.escape(r.get('tes', ''))}</td>"
        f"<td>{html.escape(r.get('status', ''))}</td>"
        f"<td>{html.escape(r.get('autonomy_mode', ''))}</td>"
        f"<td>{html.escape(r.get('duration_s', ''))}</td>"
        f"<td>{html.escape(r.get('changed_files', ''))}</td>"
        f"<td>{html.escape(r.get('run_dir', ''))}</td></tr>"
        for r in rows
    )
    lock_list_html = "".join(f"<li>{html.escape(lock)}</li>" for lock in system["lock_files"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="{refresh_seconds}">
  <title>Station Calyx Performance Dashboard</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 1.5rem;
      background-color: #0b0d11;
      color: #e4e6eb;
    }}
    h1 {{
      margin-bottom: 0.5rem;
    }}
    .card {{
      background: #151821;
      border-radius: 8px;
      padding: 1rem;
      margin-bottom: 1rem;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 0.5rem;
    }}
    th, td {{
      padding: 0.5rem;
      text-align: left;
      border-bottom: 1px solid #262a36;
      font-size: 0.9rem;
    }}
    th {{
      background-color: #1d2230;
    }}
    ul {{
      margin: 0.5rem 0 0 1.25rem;
    }}
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
    }}
    .metric {{
      background: #1d2230;
      border-radius: 8px;
      padding: 0.75rem;
    }}
    .metric span {{
      display: block;
      font-size: 0.9rem;
      color: #8f9bb7;
    }}
    .metric strong {{
      font-size: 1.5rem;
      margin-top: 0.25rem;
      display: block;
    }}
  </style>
</head>
<body>
  <h1>Station Calyx Performance Dashboard</h1>
  <p>Generated: {generated}</p>

  <div class="card">
    <h2>Key Metrics (last {len(rows)} runs)</h2>
    <div class="metrics-grid">
      <div class="metric"><span>TES average</span><strong>{metrics['tes_average']:.1f}</strong></div>
      <div class="metric"><span>TES latest</span><strong>{metrics['tes_recent']:.1f}</strong></div>
      <div class="metric"><span>Success rate</span><strong>{metrics['success_rate']:.1f}%</strong></div>
      <div class="metric"><span>Avg duration</span><strong>{metrics['duration_average']:.1f}s</strong></div>
      <div class="metric"><span>Duration p50</span><strong>{metrics['duration_p50']:.1f}s</strong></div>
      <div class="metric"><span>Duration p95</span><strong>{metrics['duration_p95']:.1f}s</strong></div>
      <div class="metric"><span>Avg footprint</span><strong>{metrics['footprint_average']:.1f} files</strong></div>
    </div>
  </div>

  <div class="card">
    <h2>Resource Snapshot</h2>
    <div class="metrics-grid">
      <div class="metric"><span>CPU usage</span><strong>{system['cpu_percent']:.1f}%</strong></div>
      <div class="metric"><span>Memory usage</span><strong>{system['memory_percent']:.1f}%</strong></div>
      <div class="metric"><span>Memory available</span><strong>{system['memory_available_mb']:.1f} MB</strong></div>
      <div class="metric"><span>Total processes</span><strong>{system['process_count']}</strong></div>
      <div class="metric"><span>Python processes</span><strong>{system['python_process_count']}</strong></div>
    </div>
    <h3>Active Lock Files</h3>
    <ul>
      {lock_list_html or "<li>None</li>"}
    </ul>
  </div>

  <div class="card">
    <h2>Recent Runs</h2>
    <table>
      <thead>
        <tr>
          <th>Timestamp</th>
          <th>TES</th>
          <th>Status</th>
          <th>Mode</th>
          <th>Duration (s)</th>
          <th>Files Changed</th>
          <th>Run Dir</th>
        </tr>
      </thead>
      <tbody>
        {recent_rows_html or "<tr><td colspan='7'>No data</td></tr>"}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


def generate_dashboard(output_path: Path, tail: int, refresh: int) -> Path:
    rows = _load_recent_metrics(limit=tail)
    metrics = _aggregate_metrics(rows)
    system = _system_snapshot()
    html_doc = _render_dashboard(metrics, system, rows, refresh_seconds=refresh)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_doc, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Station Calyx dashboard")
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT, help="Output HTML file")
    parser.add_argument("--tail", type=int, default=20, help="Number of recent runs to include (default 20)")
    parser.add_argument("--refresh", type=int, default=30, help="Auto-refresh interval in seconds (default 30)")
    args = parser.parse_args()
    path = generate_dashboard(output_path=args.output, tail=args.tail, refresh=args.refresh)
    print(f"Dashboard written to {path}")


if __name__ == "__main__":
    main()
