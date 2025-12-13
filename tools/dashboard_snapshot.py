#!/usr/bin/env python3
"""
Dashboard Snapshot Aggregator v0

Reads dispersed status artifacts and writes a unified snapshot to state/dashboard_snapshot.json
Non-LLM, best-effort, safe to run frequently.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "state"
REPORTS_DIR = ROOT / "reports"
OUTGOING_DIR = ROOT / "outgoing"

LIVE_STATUS = STATE_DIR / "bridge_pulse" / "live_status.json"
LAST_MACRO = STATE_DIR / "bridge_pulse" / "last_macro.json"
CAS_STATUS = REPORTS_DIR / "cas_status.json"
COMM_PATTERN_DIR = REPORTS_DIR
PENDING_DIR = OUTGOING_DIR / "pending_changes"
ALERTS_DIR = OUTGOING_DIR / "alerts"
SNAPSHOT_OUT = STATE_DIR / "dashboard_snapshot.json"


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _latest_bridge_pulse_report() -> Path | None:
    paths = sorted((REPORTS_DIR / "bridge_pulse").glob("bridge_pulse_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return paths[0] if paths else None


def _latest_comm_pattern() -> Path | None:
    paths = sorted(COMM_PATTERN_DIR.glob("comm_pattern_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return paths[0] if paths else None


def _parse_comm_pattern(path: Path) -> Dict[str, Any]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    window = "unknown"
    routes: List[Dict[str, Any]] = []
    for ln in lines:
        if "window=" in ln:
            window = ln.split("window=", 1)[-1].strip(")# ")
        if "->" in ln and ":" in ln:
            try:
                left, count = ln.split(":")
                route = left.strip().lstrip("-").strip()
                cnt = int(count.strip())
                routes.append({"route": route, "count": cnt})
            except Exception:
                continue
    return {"window": window, "top_routes": routes}


def _list_files(dir_path: Path) -> List[str]:
    if not dir_path.exists():
        return []
    return [str(p) for p in sorted(dir_path.glob("*"))]


def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    live = _read_json(LIVE_STATUS)
    last_macro = _read_json(LAST_MACRO)
    cas = _read_json(CAS_STATUS)

    bp_report_path = _latest_bridge_pulse_report()
    bp_report = _read_json(bp_report_path) if bp_report_path else {}

    host_health = bp_report.get("host_health", {})
    bp_status = {
        "status": live.get("status"),
        "last_micro": datetime.utcfromtimestamp(live.get("timestamp", 0)).replace(tzinfo=timezone.utc).isoformat() if live.get("timestamp") else None,
        "last_macro": datetime.utcfromtimestamp(last_macro.get("timestamp", 0)).replace(tzinfo=timezone.utc).isoformat() if last_macro.get("timestamp") else None,
        "overall_status": bp_report.get("overall_status") or last_macro.get("overall_status"),
    }

    comm_note = None
    comm_data = {"window": None, "top_routes": []}
    comm_path = _latest_comm_pattern()
    if comm_path and comm_path.exists():
        comm_data = _parse_comm_pattern(comm_path)
    else:
        comm_note = "COMM_DATA_SPARE"
    comm_data["data_note"] = comm_note

    pending_items = _list_files(PENDING_DIR)
    alerts_items = _list_files(ALERTS_DIR)

    snapshot = {
        "timestamp": now,
        "bridge_pulse": bp_status,
        "host_health": host_health,
        "cas": {
            "station_cas": cas.get("station_cas"),
            "cas_level": cas.get("cas_level"),
            "window_days": cas.get("window_days"),
            "sample_size": cas.get("sample_size"),
            "data_note": cas.get("data_note"),
        },
        "comms": comm_data,
        "pending_changes": {"count": len(pending_items), "items": pending_items},
        "alerts": {"count": len(alerts_items), "items": alerts_items},
    }

    SNAPSHOT_OUT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_OUT.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"Wrote snapshot -> {SNAPSHOT_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
