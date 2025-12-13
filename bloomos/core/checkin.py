"""
BloomOS Core Check-In Gateway v0 (Safe Mode, reflection-only).

Provides run_core_checkin(...) to return a structured snapshot without any
activation, dispatch, scheduling, or enforcement. Safe Mode is absolute.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from bloomos.identity.registry import get_identity
from bloomos.policy.binding import get_policy_snapshot
from bloomos.telemetry.collectors import collect as collect_telemetry
from bloomos.lifecycle.controller import get_state, VALID_STATES
from bloomos.safety.guard import check_action  # import safe; advisory-only


def _hash_snapshot(snapshot: Dict[str, Any]) -> str:
    data = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _readable_ts() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _canon_presence() -> Dict[str, Any]:
    canon_files = {
        "genesis": os.path.join("docs", "GENESIS_SPEC_v1.0.md"),
        "doctrine": os.path.join("docs", "CALYX_DOCTRINE_v1.0.md"),
        "heartwood": os.path.join("docs", "HEARTWOOD_CANON_v1.0.md"),
        "bloomos_canon": os.path.join("docs", "CALYX_CANON_HARMONIZED_v1.0.md"),
    }
    presence = {key: {"present": os.path.exists(path)} for key, path in canon_files.items()}
    hash_chain_tip: Optional[str] = None
    chain_path = os.path.join("docs", "HASH_CHAIN_LEDGER.jsonl")
    if os.path.exists(chain_path):
        try:
            with open(chain_path, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    last = json.loads(line)
            hash_chain_tip = last.get("sha256") if "last" in locals() else None
        except Exception:
            hash_chain_tip = None
    presence["hash_chain_tip"] = hash_chain_tip
    return presence


def _telemetry_summary(raw: Dict[str, Any]) -> Dict[str, Any]:
    tes_val = None
    tes_raw = raw.get("tes_last")
    if isinstance(tes_raw, dict):
        tes_val = tes_raw.get("tes") or tes_raw.get("tes_value") or list(tes_raw.values())[-1]
    return {
        "tes": {"present": bool(tes_raw), "latest": tes_raw, "value": tes_val},
        "agii": {"present": bool(raw.get("agii_text"))},
        "cas": {"present": bool(raw.get("cas_last")), "latest": raw.get("cas_last")},
        "foresight": {
            "present": bool(raw.get("forecast_last") or raw.get("early_warning_last")),
            "forecast_latest": raw.get("forecast_last"),
            "warning_latest": raw.get("early_warning_last"),
        },
    }


def _lifecycle_summary() -> Dict[str, Any]:
    state = get_state()
    return {
        "available_states": sorted(list(VALID_STATES)),
        "current_state": state if state in VALID_STATES else "UNKNOWN",
    }


def _checkin_log_path() -> str:
    path = os.path.join("logs", "bloomos", "core_checkins.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def _append_checkin_log(entry: Dict[str, Any]) -> None:
    path = _checkin_log_path()
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, separators=(",", ":")) + "\n")


def run_core_checkin(core_envelope: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Perform a Safe Mode core check-in and return a structured snapshot.
    This is read-only and has no side effects beyond append-only logging.
    """
    safe_mode_flag = True
    policy_snapshot = get_policy_snapshot()
    identity_snapshot = get_identity()
    telemetry_raw = collect_telemetry()
    telemetry_summary = _telemetry_summary(telemetry_raw)
    lifecycle_state = _lifecycle_summary()
    canon_integrity = _canon_presence()

    snapshot = {
        "bloomos_version": "phase_x_runtime_v1",
        "safe_mode": safe_mode_flag,
        "policy_snapshot": policy_snapshot,
        "identity_snapshot": identity_snapshot,
        "telemetry_summary": telemetry_summary,
        "lifecycle_state": lifecycle_state,
        "canon_integrity": canon_integrity,
        "core_envelope_echo": core_envelope or {},
        "timestamp": _readable_ts(),
    }
    checksum = _hash_snapshot(snapshot)
    log_entry = {
        "timestamp": snapshot["timestamp"],
        "core_envelope": core_envelope,
        "safe_mode": safe_mode_flag,
        "lifecycle_state": lifecycle_state.get("current_state"),
        "snapshot_hash": checksum,
    }
    _append_checkin_log(log_entry)
    return snapshot


__all__ = ["run_core_checkin"]
