#!/usr/bin/env python3
"""
Bridge Pulse v2 - Macro Pulse (10-minute cadence)

Runs observability + TES monitor, records status deltas, and applies autonomy rules.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import re
import psutil
from pathlib import Path
from typing import Any, Dict, Tuple

ROOT = Path(__file__).resolve().parents[1]
PREFERRED_PY = ROOT / ".venv311" / "Scripts" / "python.exe"
STATE_DIR = ROOT / "state" / "bridge_pulse"
REPORT_DIR = ROOT / "reports" / "bridge_pulse"
LOG_DIR = ROOT / "logs" / "bridge_pulse"
OUT_PENDING = ROOT / "outgoing" / "pending_changes"
ALERTS_OUT = ROOT / "outgoing" / "alerts"

LAST_MACRO = STATE_DIR / "last_macro.json"
LAST_OBS = STATE_DIR / "last_observability.json"
LAST_TES = STATE_DIR / "last_tes_monitor.json"

OBSERVABILITY_SCRIPT = ROOT / "tools" / "observability_phase1.py"
TES_MONITOR_SCRIPT = ROOT / "tools" / "tes_monitor.py"
CAS_MONITOR_SCRIPT = ROOT / "tools" / "cas_monitor.py"

ROUTE_ALERT_THRESHOLD_PER_MIN = 30.0


def _ensure_dirs():
    for p in (STATE_DIR, REPORT_DIR, LOG_DIR, OUT_PENDING, ALERTS_OUT):
        p.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _last_metric_from_csv() -> float:
    csv_path = ROOT / "logs" / "agent_metrics.csv"
    if not csv_path.exists():
        return 0.0
    try:
        import csv

        rows = []
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
        if not rows:
            return 0.0
        return float(rows[-1].get("tes", 0.0))
    except Exception:
        return 0.0


def _latest_agii_score() -> float:
    report = None
    for path in sorted((ROOT / "reports").glob("agii_report_*.md"), reverse=True):
        report = path
        break
    if not report:
        return 0.0
    text = report.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"Overall AGII:\*\* ([0-9.]+)", text)
    if not m:
        m = re.search(r"Overall AGII:\s*([0-9.]+)", text)
    try:
        return float(m.group(1)) if m else 0.0
    except Exception:
        return 0.0


def _host_health() -> Dict[str, Any]:
    cpu_pct = None
    mem_pct = None
    gpu_pct = None
    try:
        cpu_pct = psutil.cpu_percent(interval=0.1)
    except Exception:
        cpu_pct = None
    try:
        mem_pct = psutil.virtual_memory().percent
    except Exception:
        mem_pct = None
    # Optional GPU best-effort via nvidia-smi if present
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0:
            vals = [v.strip() for v in res.stdout.splitlines() if v.strip()]
            if vals:
                gpu_pct = float(vals[0])
    except Exception:
        gpu_pct = None
    return {"cpu_percent": cpu_pct, "mem_percent": mem_pct, "gpu_percent": gpu_pct}


def _run_subprocess(cmd: list[str]) -> Tuple[int, str]:
    try:
        runner = str(PREFERRED_PY) if PREFERRED_PY.exists() else sys.executable
        res = subprocess.run([runner, *cmd[1:]], capture_output=True, text=True, cwd=str(ROOT))
        return res.returncode, res.stdout + res.stderr
    except Exception as e:
        return 1, str(e)


def _run_cas_monitor() -> Dict[str, Any]:
    rc, out = _run_subprocess([sys.executable, "-u", str(CAS_MONITOR_SCRIPT)])
    data: Dict[str, Any] = {"cas_level": "LOW", "station_cas": 0.0, "data_note": "CAS_MONITOR_ERROR"}
    # Try full JSON first
    try:
        data = json.loads(out)
    except Exception:
        lines = [ln for ln in out.splitlines() if ln.strip()]
        for ln in reversed(lines):
            try:
                data = json.loads(ln)
                break
            except Exception:
                continue
    data["_raw_output"] = out
    data["_rc"] = rc
    return data


def _overall_status(tes_delta: float, agii_delta: float, cas_ok: bool, tes_output: str, alerts: list[str]) -> str:
    if not cas_ok:
        return "YELLOW"
    if any("WARN" in a or "ERROR" in a for a in alerts):
        return "YELLOW"
    if "WARN" in tes_output or "ERROR" in tes_output:
        return "YELLOW"
    if tes_delta < -5.0 or agii_delta < -5.0:
        return "YELLOW"
    return "GREEN"


def main() -> int:
    _ensure_dirs()
    now_ts = time.time()
    prev = _read_json(LAST_MACRO)
    prev_tes = float(prev.get("tes", 0.0))
    prev_agii = float(prev.get("agii", 0.0))

    # Observability
    obs_rc, obs_out = _run_subprocess([sys.executable, "-u", str(OBSERVABILITY_SCRIPT)])
    _write_json(LAST_OBS, {"timestamp": now_ts})

    # TES monitor
    tes_rc, tes_out = _run_subprocess([sys.executable, "-u", str(TES_MONITOR_SCRIPT), "--once", "--tail", "5"])
    _write_json(LAST_TES, {"timestamp": now_ts})

    current_tes = _last_metric_from_csv()
    current_agii = _latest_agii_score()
    tes_delta = current_tes - prev_tes
    agii_delta = current_agii - prev_agii

    cas_ok = False
    cas_status = {}
    cas_data = _run_cas_monitor()
    cas_status = {
        "station_cas": cas_data.get("station_cas"),
        "cas_level": cas_data.get("cas_level"),
        "window_days": cas_data.get("window_days"),
        "sample_size": cas_data.get("sample_size"),
        "data_note": cas_data.get("data_note"),
    }
    cas_ok = cas_status.get("cas_level") is not None

    alerts: list[str] = []
    # route-rate alerts are written by observability; also scan output
    for line in obs_out.splitlines():
        if "WARN" in line and "route rate" in line:
            alerts.append(line.strip())

    overall = _overall_status(tes_delta, agii_delta, cas_ok, tes_out, alerts)

    # Reporting
    report_name = f"bridge_pulse_{time.strftime('%Y%m%d_%H%M', time.gmtime(now_ts))}.json"
    report_path = REPORT_DIR / report_name
    host_health = _host_health()
    report = {
        "timestamp": now_ts,
        "overall_status": overall,
        "tes_current": current_tes,
        "tes_delta": tes_delta,
        "agii_current": current_agii,
        "agii_delta": agii_delta,
        "cas": cas_status,
        "alerts_top": alerts[:3],
        "tes_monitor_output": tes_out.strip(),
        "observability_output_tail": obs_out.splitlines()[-10:],
        "actions": [],
        "pending_changes": [],
        "host_health": host_health,
    }

    # Autonomy rules
    if overall == "GREEN":
        # No automatic changes applied yet; ready slot for low-risk tweaks.
        pass
    elif overall == "YELLOW":
        pending_path = OUT_PENDING / f"bridge_pulse_{time.strftime('%Y%m%d_%H%M', time.gmtime(now_ts))}.md"
        pending = [
            "# Pending changes (YELLOW status)",
            "- CAS not wired; integrate CAS monitor hook.",
            "- High CBO route dominance; consider rate limiting/balancing once fresh SVF logs are available.",
        ]
        pending_path.parent.mkdir(parents=True, exist_ok=True)
        pending_path.write_text("\n".join(pending), encoding="utf-8")
        report["pending_changes"].append(str(pending_path))
    elif overall == "RED":
        alert_file = ALERTS_OUT / f"bridge_pulse_alert_{int(now_ts)}.json"
        _write_json(alert_file, {"ts": now_ts, "status": "RED", "reason": "macro pulse detected RED state"})

    _write_json(report_path, report)
    _write_json(LAST_MACRO, {"timestamp": now_ts, "tes": current_tes, "agii": current_agii, "overall_status": overall})

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (LOG_DIR / "autonomous_changes.log").open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now_ts))} status={overall} alerts={len(alerts)}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
