#!/usr/bin/env python3
"""Poll the CBO report endpoint and write alerts when capacity is stressed."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "logs" / "capacity_alerts.jsonl"
REPORT_URL = "http://127.0.0.1:8080/report"


def fetch_report() -> dict:
    with urllib.request.urlopen(REPORT_URL, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def evaluate(report: dict) -> dict:
    policy = report.get("policy_flags", {})
    resource = report.get("resource_snapshot", {})
    tes_summary = report.get("tes_summary", {})

    cpu_cap = float(policy.get("max_cpu_pct", 100) or 100)
    cpu = float(resource.get("cpu_pct") or 0.0)
    ram_cap = float(policy.get("max_ram_pct", 100) or 100)
    ram = float(resource.get("ram_pct") or 0.0)
    velocity = float(tes_summary.get("velocity_last_20") or 0.0)
    trend = str(tes_summary.get("trend") or "unknown")

    alerts: list[str] = []
    if cpu >= cpu_cap:
        alerts.append("cpu_cap_exceeded")
    elif cpu >= cpu_cap * 0.95:
        alerts.append("cpu_near_cap")

    if ram >= ram_cap:
        alerts.append("ram_cap_exceeded")
    elif ram >= ram_cap * 0.95:
        alerts.append("ram_near_cap")

    if trend == "declining" or velocity < -1.0:
        alerts.append("tes_declining")

    if report.get("queue_depth", 0) > 0:
        alerts.append("queue_backlog")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "alerts": alerts,
        "cpu_pct": cpu,
        "ram_pct": ram,
        "cpu_cap": cpu_cap,
        "ram_cap": ram_cap,
        "tes_velocity": velocity,
        "tes_trend": trend,
        "queue_depth": report.get("queue_depth", 0),
        "objectives_pending": report.get("objectives_pending", 0),
    }


def log_result(entry: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def main() -> int:
    try:
        report = fetch_report()
    except Exception as exc:
        log_result({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "alerts": ["report_fetch_failed"],
            "error": str(exc),
        })
        return 1

    entry = evaluate(report)
    if not entry["alerts"]:
        entry["alerts"] = ["ok"]
    log_result(entry)
    return 0 if entry["alerts"] == ["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
