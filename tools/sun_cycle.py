#!/usr/bin/env python3
"""Emit Station Calyx sun-cycle records."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


UNKNOWN_HASH = "unknown"


def utc_stamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_filename_stamp(ts_utc: str) -> str:
    return ts_utc.replace(":", "-").replace("+00:00", "Z")


def sha256_path(path: Path) -> str:
    if not path.exists():
        return UNKNOWN_HASH
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.read_bytes())
        return digest.hexdigest()
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(str(child.relative_to(path)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(child.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def load_energy_policy(root: Path) -> dict[str, Any]:
    policy_path = root / "governance" / "policies" / "energy_viability_policy.json"
    if not policy_path.exists():
        return {"sunrise_min_battery_percent": 25, "ac_required": False}
    return json.loads(policy_path.read_text(encoding="utf-8"))


def read_energy_snapshot() -> dict[str, Any]:
    """Return conservative host energy telemetry when portable APIs are unavailable."""

    return {
        "power_line_status": os.environ.get("CALYX_POWER_LINE_STATUS", "unknown"),
        "battery_charge_status": os.environ.get("CALYX_BATTERY_CHARGE_STATUS", "unknown"),
        "battery_life_percent": float(os.environ.get("CALYX_BATTERY_LIFE_PERCENT", "100")),
        "battery_life_remaining": None,
    }


def build_station_state_snapshot(root: Path, node_id: str) -> dict[str, Any]:
    repo_roots = [str(root)] if (root / ".git").exists() else []
    return {
        "repo_roots_present": repo_roots,
        "node_id": node_id,
        "active_workspaces": [str(root)],
        "last_known_correlation_id": None,
        "last_known_agent_statuses": {},
    }


def build_integrity_snapshot(root: Path) -> dict[str, str]:
    approvals_dir = root / "governance" / "approvals"
    receipts_dir = root / "governance" / "receipts"
    return {
        "allowed_signers_hash": sha256_path(root / "governance" / "identities" / "allowed_signers"),
        "identity_json_hash": sha256_path(root / "governance" / "identities" / "architect_identity.json"),
        "most_recent_receipts_hash": sha256_path(receipts_dir if receipts_dir.exists() else approvals_dir),
    }


def build_sunrise_record(
    root: Path,
    *,
    node_id: str,
    reason: str,
    next_phase: str,
    energy: dict[str, Any] | None = None,
    parent_correlation_id: str | None = None,
    correlation_id: str | None = None,
    ts_utc: str | None = None,
) -> dict[str, Any]:
    ts = ts_utc or utc_stamp()
    correlation = correlation_id or f"sunrise-{uuid.uuid4().hex[:12]}"
    return {
        "ts_utc": ts,
        "correlation_id": correlation,
        "parent_correlation_id": parent_correlation_id,
        "reason": reason,
        "energy": energy or read_energy_snapshot(),
        "station_state_snapshot": build_station_state_snapshot(root, node_id),
        "integrity": build_integrity_snapshot(root),
        "next_intended_boot_phase": next_phase,
    }


def validate_sun_cycle_record(record: dict[str, Any]) -> list[str]:
    required = {
        "ts_utc",
        "correlation_id",
        "reason",
        "energy",
        "station_state_snapshot",
        "integrity",
        "next_intended_boot_phase",
    }
    errors: list[str] = []
    missing = sorted(required - set(record))
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")
    if record.get("reason") not in {"low_battery", "ac_unavailable", "operator_shutdown", "thermal_risk", "unknown"}:
        errors.append("reason is not permitted by governance/schemas/sun_cycle.schema.json")
    for field in ("power_line_status", "battery_charge_status", "battery_life_percent"):
        if field not in record.get("energy", {}):
            errors.append(f"energy.{field} missing")
    for field in ("repo_roots_present", "node_id", "active_workspaces"):
        if field not in record.get("station_state_snapshot", {}):
            errors.append(f"station_state_snapshot.{field} missing")
    for field in ("allowed_signers_hash", "identity_json_hash", "most_recent_receipts_hash"):
        if field not in record.get("integrity", {}):
            errors.append(f"integrity.{field} missing")
    return errors


def assess_boot_guard(record: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    energy = record.get("energy", {})
    battery_percent = float(energy.get("battery_life_percent", 0))
    power_line_status = str(energy.get("power_line_status", "unknown")).lower()
    min_battery = float(policy.get("sunrise_min_battery_percent", 25))
    ac_required = bool(policy.get("ac_required", False))
    checks: list[str] = []

    if battery_percent < min_battery:
        checks.append("battery_below_sunrise_min")
    if ac_required and power_line_status not in {"online", "ac", "charging"}:
        checks.append("ac_required_but_unavailable")

    return {
        "status": "blocked" if checks else "allowed",
        "checks": checks,
        "sunrise_min_battery_percent": min_battery,
        "ac_required": ac_required,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def emit_sunrise(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    out_dir_arg = Path(args.out_dir)
    out_dir = out_dir_arg if out_dir_arg.is_absolute() else root / out_dir_arg
    record = build_sunrise_record(
        root,
        node_id=args.node_id,
        reason=args.reason,
        next_phase=args.next_phase,
        parent_correlation_id=args.parent_correlation_id,
        correlation_id=args.correlation_id,
        ts_utc=args.ts_utc,
    )
    errors = validate_sun_cycle_record(record)
    guard = assess_boot_guard(record, load_energy_policy(root))
    ts = safe_filename_stamp(record["ts_utc"])
    sunrise_path = out_dir / "sunrises" / f"sunrise_{ts}_{record['correlation_id']}.json"
    report_path = out_dir / f"boot_guard_validation_{record['correlation_id']}.json"
    write_json(sunrise_path, record)
    try:
        record_path = str(sunrise_path.relative_to(root))
        report_rel_path = str(report_path.relative_to(root))
    except ValueError:
        record_path = str(sunrise_path)
        report_rel_path = str(report_path)
    report = {
        "ts_utc": utc_stamp(),
        "node_id": args.node_id,
        "host": socket.gethostname(),
        "record_path": record_path,
        "report_path": report_rel_path,
        "sunrise_sha256": sha256_path(sunrise_path),
        "correlation_id": record["correlation_id"],
        "schema": "governance/schemas/sun_cycle.schema.json",
        "valid": not errors,
        "errors": errors,
        "boot_guard": guard,
        "status": guard["status"],
        "verdict": (
            "sunrise accepted"
            if not errors and guard["status"] == "allowed"
            else "sunrise blocked"
        ),
    }
    write_json(report_path, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Station Calyx repository root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sunrise = subparsers.add_parser("sunrise", help="Write a sunrise record and validation report")
    sunrise.add_argument("--node-id", default="station-calyx")
    sunrise.add_argument("--reason", default="unknown")
    sunrise.add_argument("--next-phase", default="cbo_operational_watch")
    sunrise.add_argument("--parent-correlation-id")
    sunrise.add_argument("--correlation-id")
    sunrise.add_argument("--ts-utc")
    sunrise.add_argument("--out-dir", default="telemetry/sun_cycle")
    sunrise.set_defaults(func=emit_sunrise)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
