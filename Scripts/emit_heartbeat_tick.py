#!/usr/bin/env python3
"""Emit heartbeat.tick to Station Event Ledger. Called by update_state_checks.ps1."""
from __future__ import annotations

import sys
import json
from pathlib import Path

# Ensure repo root on path
_repo = Path(__file__).resolve().parents[1]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))


def _parse_args(argv: list[str]) -> dict:
    out = {"checks": "", "health": "", "heartbeat_path": None, "restart_transition": False}
    idx = 1
    if len(argv) > 1 and not argv[1].startswith("--"):
        out["checks"] = argv[1]
        idx = 2
    if len(argv) > 2 and not argv[2].startswith("--"):
        out["health"] = argv[2]
        idx = 3
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--heartbeat" and idx + 1 < len(argv):
            out["heartbeat_path"] = argv[idx + 1]
            idx += 2
            continue
        if arg == "--restart-transition":
            out["restart_transition"] = True
            idx += 1
            continue
        idx += 1
    return out


def _load_heartbeat(path: str | None) -> dict:
    if not path:
        return {}
    try:
        p = Path(path)
        if not p.exists():
            return {}
        text = p.read_text(encoding="utf-8", errors="replace")
        if text.startswith("\ufeff"):
            text = text.lstrip("\ufeff")
        return json.loads(text)
    except Exception:
        return {}


def main() -> int:
    try:
        from calyx.kernel.event_ledger import clear_system_phase, emit, set_system_phase
        parsed = _parse_args(sys.argv)
        checks = parsed.get("checks") or ""
        health = parsed.get("health") or ""
        hb = _load_heartbeat(parsed.get("heartbeat_path"))
        data = {"checks": checks[:100], "health": health[:20]}
        for key in (
            "heartbeat_emitted_ts",
            "station_boot_ts",
            "boot_session_id",
            "memory_pressure_tier",
            "heartbeat_payload_sha256",
            "restart_detected",
            "restart_count",
            "hidden_restart_suspected",
            "service_snapshot_sha256",
        ):
            if key in hb and hb[key] not in (None, "", []):
                data[key] = hb[key]
        if hb.get("restart_services"):
            data["restart_services"] = hb.get("restart_services")
        set_system_phase("runtime")
        try:
            emit(
                level="INFO",
                component="heartbeat",
                event="heartbeat.tick",
                msg="heartbeat tick",
                data=data,
            )
            if parsed.get("restart_transition"):
                emit(
                    level="WARN",
                    component="heartbeat",
                    event="restart.detected",
                    msg="Service restart detected",
                    data={
                        "restart_services": hb.get("restart_services", []),
                        "restart_count": hb.get("restart_count"),
                        "hidden_restart_suspected": hb.get("hidden_restart_suspected"),
                        "heartbeat_emitted_ts": hb.get("heartbeat_emitted_ts"),
                    },
                )
        finally:
            clear_system_phase()
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())
