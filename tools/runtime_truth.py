from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any


CONTRACTS: dict[str, dict[str, Any]] = {
    "station_health": {
        "freshness_window_sec": 15,
        "stale_label": "STALE_HEALTH",
        "timestamp_fields": ("emitted_ts_utc", "health_ts"),
    },
    "navigator": {
        "freshness_window_sec": 180,
        "stale_label": "STALE_ADVISORY",
        "timestamp_fields": ("emitted_ts_utc", "ts_utc", "ts"),
    },
    "triage": {
        "freshness_window_sec": 180,
        "stale_label": "STALE_ADVISORY",
        "timestamp_fields": ("emitted_ts_utc", "ts_utc", "ts"),
    },
    "cp6": {
        "freshness_window_sec": 900,
        "stale_label": "STALE_ADVISORY",
        "timestamp_fields": ("emitted_ts_utc", "ts_utc", "ts"),
    },
    "cp7": {
        "freshness_window_sec": 900,
        "stale_label": "STALE_ADVISORY",
        "timestamp_fields": ("emitted_ts_utc", "ts_utc", "ts"),
    },
    "cp9": {
        "freshness_window_sec": 600,
        "stale_label": "STALE_TUNING",
        "timestamp_fields": ("emitted_ts_utc", "ts_utc", "ts"),
    },
    "signal_digest": {
        "freshness_window_sec": 180,
        "stale_label": "STALE_SIGNAL_DIGEST",
        "timestamp_fields": ("emitted_ts_utc", "ts_utc", "ts"),
    },
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw).astimezone(timezone.utc)
    except ValueError:
        return None


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def artifact_freshness(path: Path, payload: dict[str, Any] | None, contract_name: str, now: datetime | None = None) -> dict[str, Any]:
    contract = CONTRACTS[contract_name]
    now = now or utc_now()
    emitted_at = None
    timestamp_source = ""
    explicit_expiry = None
    explicit_truth_state = ""
    if payload:
        explicit_expiry = parse_utc(payload.get("expires_ts_utc"))
        explicit_truth_state = str(payload.get("truth_state") or "").strip()
        for field in contract["timestamp_fields"]:
            emitted_at = parse_utc(payload.get(field))
            if emitted_at:
                timestamp_source = field
                break
    if emitted_at is None and path.exists():
        emitted_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        timestamp_source = "file_mtime_utc"
    if emitted_at is None:
        return {
            "emitted_ts_utc": "",
            "freshness_window_sec": int(contract["freshness_window_sec"]),
            "expires_ts_utc": explicit_expiry.isoformat().replace("+00:00", "Z") if explicit_expiry else "",
            "truth_state": explicit_truth_state or "unknown",
            "stale_label": contract["stale_label"],
            "authoritative_for_liveness": False,
            "is_fresh": False,
            "timestamp_source": timestamp_source,
        }
    expires_at = explicit_expiry or (emitted_at + timedelta(seconds=int(contract["freshness_window_sec"])))
    is_fresh = explicit_truth_state != "stale" and now <= expires_at
    return {
        "emitted_ts_utc": emitted_at.isoformat().replace("+00:00", "Z"),
        "freshness_window_sec": int(contract["freshness_window_sec"]),
        "expires_ts_utc": expires_at.isoformat().replace("+00:00", "Z"),
        "truth_state": "fresh" if is_fresh else (explicit_truth_state or "stale"),
        "stale_label": "" if is_fresh else contract["stale_label"],
        "authoritative_for_liveness": False,
        "is_fresh": is_fresh,
        "timestamp_source": timestamp_source,
    }


def load_json_if_fresh(path: Path, contract_name: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    payload = load_json(path)
    freshness = artifact_freshness(path, payload, contract_name)
    if freshness["is_fresh"]:
        return payload, freshness
    return None, freshness


def add_truth_metadata(
    payload: dict[str, Any],
    contract_name: str,
    emitted_at: datetime | None = None,
    *,
    force_stale: bool = False,
    stale_reason: str = "",
) -> dict[str, Any]:
    contract = CONTRACTS[contract_name]
    emitted_at = emitted_at or utc_now()
    expires_at = emitted_at if force_stale else emitted_at + timedelta(seconds=int(contract["freshness_window_sec"]))
    payload["emitted_ts_utc"] = emitted_at.isoformat().replace("+00:00", "Z")
    payload["freshness_window_sec"] = int(contract["freshness_window_sec"])
    payload["expires_ts_utc"] = expires_at.isoformat().replace("+00:00", "Z")
    payload["truth_state"] = "stale" if force_stale else "fresh"
    payload["stale_label"] = contract["stale_label"] if force_stale else ""
    payload["authoritative_for_liveness"] = False
    payload["stale_reason"] = stale_reason if force_stale else ""
    return payload
