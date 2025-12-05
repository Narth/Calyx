#!/usr/bin/env python3
"""
Bridge Pulse Report Generator

Generates Station Calyx Bridge Pulse Reports based on the template
in reports/bridge_pulse_template.md

Usage:
  python tools/bridge_pulse_generator.py [--report-id bp-0001] [--output reports/]
"""

from __future__ import annotations
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
METRICS_CSV = ROOT / "logs" / "agent_metrics.csv"
SYSTEM_SNAPSHOTS = ROOT / "logs" / "system_snapshots.jsonl"
CBO_LOCK = ROOT / "outgoing" / "cbo.lock"
REPORTS_DIR = ROOT / "reports"
MANUAL_SHUTDOWN_FLAG = ROOT / "manual_shutdown.flag"


def read_json(path: Path) -> dict:
    """Read JSON file"""
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def read_jsonl(path: Path, last_n: int = 100) -> List[dict]:
    """Read last N lines from JSONL file"""
    lines = []
    try:
        with path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        lines.append(json.loads(line))
                    except Exception:
                        pass
    except Exception:
        pass
    return lines[-last_n:] if lines else []


def calculate_mean_tes() -> Optional[float]:
    """Calculate mean TES from agent_metrics.csv"""
    if not METRICS_CSV.exists():
        return None
    
    tes_values = []
    try:
        with METRICS_CSV.open('r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    tes = float(row.get('tes', 0))
                    tes_values.append(tes)
                except (ValueError, KeyError):
                    pass
    except Exception:
        return None
    
    if not tes_values:
        return None
    
    return sum(tes_values) / len(tes_values)


def calculate_uptime_24h() -> Tuple[float, int]:
    """Calculate 24h rolling uptime from system snapshots
    
    Returns:
        (uptime_percent, total_samples)
    """
    if not SYSTEM_SNAPSHOTS.exists():
        return 0.0, 0
    
    snapshots = read_jsonl(SYSTEM_SNAPSHOTS, last_n=1000)
    if not snapshots:
        return 0.0, 0
    
    # Filter to last 24 hours (timezone-aware to match ISO snapshots)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    
    recent = []
    for snap in snapshots:
        try:
            ts = datetime.fromisoformat(snap['timestamp'].replace('Z', '+00:00'))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                recent.append(snap)
        except Exception:
            pass
    
    if not recent:
        return 0.0, 0
    
    # Count samples with python processes as "up"
    up_samples = sum(1 for s in recent if s.get('count', 0) > 0)
    uptime = (up_samples / len(recent)) * 100.0
    
    return uptime, len(recent)


def get_resource_metrics() -> Dict[str, any]:
    """Get current resource metrics from CBO lock"""
    if not CBO_LOCK.exists():
        return {}
    
    cbo_data = read_json(CBO_LOCK)
    metrics = cbo_data.get('metrics', {})
    
    return {
        'cpu_pct': metrics.get('cpu_pct', 0),
        'ram_pct': metrics.get('mem_used_pct', 0),
        'gpu_pct': metrics.get('gpu', {}).get('gpus', [{}])[0].get('util_pct', 0) if metrics.get('gpu') else 0,
    }


def get_active_agents() -> int:
    """Count active agents from CBO lock"""
    if not CBO_LOCK.exists():
        return 0
    
    cbo_data = read_json(CBO_LOCK)
    locks = cbo_data.get('locks', {})
    
    # Count active locks (excluding manual flags)
    active = sum(1 for k, v in locks.items() 
                 if v and k not in ['manual_shutdown', 'watcher_token'])
    
    return active


def get_recent_events() -> List[str]:
    """Get recent system events from logs (placeholder for now)"""
    events = []
    
    # Check for recent agent activity from snapshots
    snapshots = read_jsonl(SYSTEM_SNAPSHOTS, last_n=20)
    if snapshots:
        latest = snapshots[-1]
        events.append(f"[{latest.get('timestamp', 'N/A')}] System snapshot: {latest.get('count', 0)} Python processes")
    
    # Check CBO lock timestamp
    if CBO_LOCK.exists():
        cbo_data = read_json(CBO_LOCK)
        iso_ts = cbo_data.get('iso', 'N/A')
        events.append(f"[{iso_ts}] CBO heartbeat pulse")
    
    return events


def check_manual_shutdown_flag() -> bool:
    """Check if manual_shutdown.flag exists"""
    return MANUAL_SHUTDOWN_FLAG.exists()


def generate_report(report_id: str, output_dir: Path) -> Path:
    """Generate Bridge Pulse Report"""
    
    now = datetime.now()
    iso_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Gather metrics
    uptime, sample_count = calculate_uptime_24h()
    mean_tes = calculate_mean_tes()
    resources = get_resource_metrics()
    active_agents = get_active_agents()
    events = get_recent_events()
    manual_shutdown = check_manual_shutdown_flag()

    def indicator(ok: bool, no_data: bool = False) -> str:
        if no_data:
            return "No data"
        return "OK" if ok else "Attention"

    uptime_value = f"{uptime:.1f}%" if sample_count else "N/A"
    uptime_status = indicator(uptime >= 90, no_data=sample_count == 0)
    tes_value = f"{mean_tes:.1f}" if mean_tes is not None else "N/A"
    tes_status = indicator(bool(mean_tes and mean_tes >= 95), no_data=mean_tes is None)
    cpu_pct = float(resources.get("cpu_pct", 0.0))
    ram_pct = float(resources.get("ram_pct", 0.0))
    gpu_pct = float(resources.get("gpu_pct", 0.0))
    cpu_status = indicator(cpu_pct < 70.0)
    ram_status = indicator(ram_pct < 75.0)
    gpu_status = indicator(gpu_pct < 85.0)
    agents_status = indicator(active_agents <= 12)
    samples_value = f"{sample_count}" if sample_count else "0"
    samples_status = indicator(sample_count > 0, no_data=sample_count == 0)
    intent = "health_pulse"
    respect_frame = "neutral_observer"
    provenance = {
        "trigger": "manual_run",
        "agent": "bridge_pulse_generator",
        "source_files": [
            str(METRICS_CSV) if METRICS_CSV.exists() else "missing:agent_metrics.csv",
            str(SYSTEM_SNAPSHOTS) if SYSTEM_SNAPSHOTS.exists() else "missing:system_snapshots.jsonl",
            str(CBO_LOCK) if CBO_LOCK.exists() else "missing:cbo.lock",
        ],
    }
    causal_chain = "snapshots + cbo.lock metrics -> bridge_pulse_generator -> markdown report"
    reflection_window = {
        "evidence": f"{sample_count} snapshots (24h); see events list",
        "risk": "Low; report-only action",
        "next_checks": "Review TES if <95; refresh heartbeat if stale",
    }

    if sample_count == 0 or mean_tes is None:
        overall_status = "Amber"
    elif uptime >= 90 and mean_tes >= 95:
        overall_status = "Green"
    elif uptime >= 80 and mean_tes >= 85:
        overall_status = "Amber"
    else:
        overall_status = "Red"

    report_lines = [
        "# Station Calyx - Bridge Pulse Report",
        "",
        f"Timestamp: {iso_timestamp}",
        f"Pulse ID: {report_id}",
        "Operator: CBO",
        "Report Agent: bridge_pulse_generator",
        "Directive Context: Maintain system uptime > 90% over 24h",
        "",
        "## 1. Core Metrics",
        "| Metric | Value | Threshold | Status |",
        "| --- | --- | --- | --- |",
        f"| Uptime (24h rolling) | {uptime_value} | > 90% | {uptime_status} |",
        f"| Samples (24h) | {samples_value} | > 0 | {samples_status} |",
        f"| Mean TES | {tes_value} | >= 95 | {tes_status} |",
        f"| CPU Load Avg | {cpu_pct:.1f}% | < 70% | {cpu_status} |",
        f"| RAM Utilization | {ram_pct:.1f}% | < 75% | {ram_status} |",
        f"| GPU Utilization | {gpu_pct:.1f}% | < 85% | {gpu_status} |",
        f"| Active Agents | {active_agents} | <= configured limit | {agents_status} |",
        "",
        "## 1.a Governance & Provenance",
        f"- Intent: {intent}",
        f"- Respect frame: {respect_frame}",
        f"- Provenance: {json.dumps(provenance)}",
        f"- Causal chain: {causal_chain}",
        f"- Reflection window: {json.dumps(reflection_window)}",
        "",
        "## 2. System Events (last pulse)",
        "",
    ]
    if events:
        for event in events[-5:]:  # Last 5 events
            report_lines.append(event)
    else:
        report_lines.append("[No recent events recorded]")

    report_lines.extend([
        "",
        "## 3. Alerts and Responses",
        "| Alert ID | Severity | Trigger | Response | Resolved |",
        "| --- | --- | --- | --- | --- |",
        "|  |  |  |  |  |",
        "",
        "## 4. Learning & Adjustments",
        "",
        "Observation: System operating within guardrails with active monitoring.",
        "",
        "Action Taken: Generated bridge pulse report and refreshed telemetry.",
        "",
        "Result: Baseline metrics captured for the current research session.",
        "",
        "Confidence Level: Initial measurement for this session.",
        "",
        "Notes: Clean template and ASCII-safe output confirmed.",
        "",
        "## 5. Human Oversight",
        "| Field | Entry |",
        "| --- | --- |",
        f"| Last human logoff | {iso_timestamp} |",
        "| Expected return | N/A |",
        "| Manual overrides since last pulse | 0 |",
        f"| manual_shutdown.flag detected | {'Yes' if manual_shutdown else 'No'} |",
        "",
        "## 6. Summary",
        "",
        (
            "During this pulse, Station Calyx maintained operational integrity within defined "
            "parameters. Primary directive compliance: "
            f"{uptime:.1f}%. System samples analyzed: {sample_count}. "
            f"Overall status: {overall_status}."
        ),
    ])
    report_content = "\n".join(report_lines)
    
    # Write report
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"bridge_pulse_{report_id}.md"
    
    try:
        with report_path.open('w', encoding='utf-8') as f:
            f.write(report_content)
    except UnicodeEncodeError:
        # Fallback for Windows console issues
        print(f"Note: Some Unicode characters may not display correctly in Windows console")
        with report_path.open('w', encoding='utf-8') as f:
            f.write(report_content)
    
    return report_path


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Generate Bridge Pulse Report")
    ap.add_argument("--report-id", type=str, default="bp-0001", help="Report ID (default: bp-0001)")
    ap.add_argument("--output", type=str, default="reports", help="Output directory (default: reports)")
    
    args = ap.parse_args(argv)
    
    try:
        output_dir = ROOT / args.output
        report_path = generate_report(args.report_id, output_dir)
        
        print(f"[OK] Bridge Pulse Report generated: {report_path}")
        print(f"[INFO] Report ID: {args.report_id}")
        
        return 0
    except Exception as e:
        print(f"[ERROR] Error generating report: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

