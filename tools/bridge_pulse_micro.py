#!/usr/bin/env python3
"""
Bridge Pulse v2 - Micro Pulse (1-minute cadence)

Lightweight heartbeat: verifies core flags and recent macro/observability activity.
No LLM, heavy diagnostics, or expensive I/O.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Tuple

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "state"
BP_STATE = STATE_DIR / "bridge_pulse"
LIVE_STATUS = BP_STATE / "live_status.json"
MICRO_LOG = ROOT / "logs" / "bridge_pulse" / "micro_events.log"

# Expected files
RESEARCH_FLAG = STATE_DIR / "research_mode.flag"
RESEARCH_JSON = STATE_DIR / "research_mode_active.json"
NETWORK_GATE_STATE = STATE_DIR / "network_gate.json"
NETWORK_GATE_FILE = ROOT / "outgoing" / "gates" / "network.ok"
LAST_MACRO = BP_STATE / "last_macro.json"
LAST_OBS = BP_STATE / "last_observability.json"
LAST_TES = BP_STATE / "last_tes_monitor.json"

# Thresholds
MACRO_OVERDUE_SEC = 20 * 60  # 20 minutes


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _compute_network_state() -> Dict[str, Any]:
    state = {"gate_exists": NETWORK_GATE_FILE.exists()}
    try:
        state["timestamp"] = time.time()
        _write_json(NETWORK_GATE_STATE, state)
    except Exception:
        pass
    return state


def _load_ts(rec: Dict[str, Any]) -> float:
    try:
        return float(rec.get("timestamp", 0))
    except Exception:
        return 0.0


def _status_reason() -> Tuple[str, str]:
    now = time.time()
    research_flag = RESEARCH_FLAG.exists()
    research_json_ok = RESEARCH_JSON.exists()
    net_state = _read_json(NETWORK_GATE_STATE) if NETWORK_GATE_STATE.exists() else _compute_network_state()
    macro_rec = _read_json(LAST_MACRO)
    obs_rec = _read_json(LAST_OBS)
    tes_rec = _read_json(LAST_TES)

    last_macro_ts = _load_ts(macro_rec)
    last_obs_ts = _load_ts(obs_rec)
    last_tes_ts = _load_ts(tes_rec)

    missing_required = not LAST_MACRO.exists()
    if missing_required or (now - last_macro_ts) > MACRO_OVERDUE_SEC:
        return "DOWN_SUSPECTED", "macro pulse overdue or missing"

    degraded_reasons = []
    if not research_flag or not research_json_ok:
        degraded_reasons.append("research flags missing")
    if not obs_rec:
        degraded_reasons.append("observability missing")
    if not tes_rec:
        degraded_reasons.append("tes monitor missing")

    if degraded_reasons:
        return "DEGRADED", "; ".join(degraded_reasons)
    return "UP", "all expected signals present"


def main() -> int:
    status, reason = _status_reason()
    now = time.time()
    prev = _read_json(LIVE_STATUS) if LIVE_STATUS.exists() else {}
    prev_status = prev.get("status")
    payload = {"timestamp": now, "status": status, "reason": reason}
    _write_json(LIVE_STATUS, payload)

    # log only on change
    if prev_status != status:
        MICRO_LOG.parent.mkdir(parents=True, exist_ok=True)
        with MICRO_LOG.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now))} status={status} reason={reason}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
