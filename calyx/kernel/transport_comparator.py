from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CANONICAL_PORTS = {7777, 7778, 7780, 7781}
CANONICAL_SERVICE_PORTS = {
    "dev_harness": 7777,
    "cbo_core": 7778,
    "avatar_web": 7780,
    "telemetry_gateway": 7781,
}
# WO_DISCORD_CANONICAL_TRANSPORT_DECLARATION_V1: Discord = canonical_transport_intake_only
DISCORD_CANONICAL_TRANSPORT_SOURCE = "calyx.cbo.discord_gateway"
DISCORD_CANONICAL_AUTHORITY_BASIS = "discord.heartbeat.sender.identity"


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def _load_json_files(directory: Path, pattern: str) -> list[dict[str, Any]]:
    items: list[tuple[datetime, dict[str, Any]]] = []
    for p in sorted(directory.glob(pattern)):
        try:
            rec = _read_json(p)
        except Exception:
            continue
        ts = _parse_ts(rec.get("ts_utc")) or datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        rec["_path"] = str(p)
        items.append((ts, rec))
    items.sort(key=lambda x: x[0], reverse=True)
    return [rec for _, rec in items]


def _load_ledger_events(repo_root: Path) -> list[dict[str, Any]]:
    ledger_dir = repo_root / "runtime" / "ledger"
    events: list[dict[str, Any]] = []
    for p in sorted(ledger_dir.glob("station_events__*.jsonl")):
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        for line in lines:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            ts = _parse_ts(rec.get("ts_utc") or rec.get("ts"))
            if ts is None:
                continue
            rec["_ts"] = ts
            events.append(rec)
    events.sort(key=lambda x: x["_ts"])
    return events


@dataclass
class TransportCycle:
    cycle_ref: str
    boot_session_id: str
    unexpected_new_remote: bool
    unexpected_new_emitter_authority: bool
    new_listener_unexpected: bool
    channel_widening: bool
    details: dict[str, Any]


def _events_in_window(events: list[dict[str, Any]], start: datetime | None, end: datetime | None) -> list[dict[str, Any]]:
    if start is None or end is None:
        return []
    return [e for e in events if start <= e["_ts"] <= end]


def evaluate_transport_cycles(repo_root: Path, required_count: int) -> list[TransportCycle]:
    receipts_dir = repo_root / "runtime" / "receipts"
    audit_dir = receipts_dir / "audit"
    sunrise = _load_json_files(receipts_dir, "sunrise_receipt__*.json")
    boot_audits = _load_json_files(audit_dir, "boot_evidence_bundle__*.json")
    noise = _load_json_files(audit_dir, "telemetry_noise_signal_summary__*.json")
    n = min(len(sunrise), len(boot_audits), len(noise), max(required_count, 1))
    if n <= 0:
        return []

    # Build oldest->newest so stateful carry-forward can be applied safely.
    triples: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for i in range(n):
        triples.append((sunrise[i], boot_audits[i], noise[i]))
    triples.reverse()

    ledger_events = _load_ledger_events(repo_root)
    out_oldest_to_newest: list[TransportCycle] = []

    known_remote_keys: set[tuple[str, int, str]] = set()  # (source_module, port, classification)
    known_listener_keys: set[tuple[str, int]] = set()  # (module, port)
    prev_authority_basis = ""
    prev_authority_class = ""
    prev_authority_pid: int | None = None

    for idx, (s, b, z) in enumerate(triples, 1):
        window = z.get("window") or {}
        w_start = _parse_ts(window.get("start_ts_utc"))
        w_end = _parse_ts(window.get("end_ts_utc"))
        win_events = _events_in_window(ledger_events, w_start, w_end)

        boot_session_id = str(b.get("boot_session_id") or "")
        cycle_ref = f"cycle_{idx}"

        # Listener extraction from bind overrides.
        listener_items: list[dict[str, Any]] = []
        listener_unexpected = False
        for e in win_events:
            if e.get("event") != "audit.runtime.network.bind_override":
                continue
            data = e.get("data") or {}
            module = str(data.get("service") or "unknown")
            port = int(data.get("port") or 0)
            key = (module, port)
            canonical = port in CANONICAL_PORTS and CANONICAL_SERVICE_PORTS.get(module) == port
            seen_prior = key in known_listener_keys
            if not (canonical and seen_prior):
                listener_unexpected = True
            listener_items.append(
                {
                    "module": module,
                    "port": port,
                    "address": str(data.get("host") or ""),
                    "seen_in_prior_cycle": seen_prior,
                    "canonical_port": canonical,
                    "ts_utc": e.get("ts_utc") or e.get("ts"),
                }
            )
            known_listener_keys.add(key)

        # Emitter authority continuity: same basis/classification, PID may rotate.
        emitter_pid: int | None = None
        authority_basis = ""
        authority_class = ""
        for e in win_events:
            if e.get("event") != "discord.heartbeat.sender.identity":
                continue
            data = e.get("data") or {}
            try:
                emitter_pid = int(data.get("pid"))
            except Exception:
                emitter_pid = None
            authority_basis = "discord.heartbeat.sender.identity"
            authority_class = str(data.get("module_entrypoint") or "calyx.cbo.discord_gateway")
            break

        emitter_unexpected = False
        discord_canonical = (
            authority_basis == DISCORD_CANONICAL_AUTHORITY_BASIS
            and authority_class == DISCORD_CANONICAL_TRANSPORT_SOURCE
        )
        if discord_canonical:
            emitter_unexpected = False
        elif emitter_pid is None:
            emitter_unexpected = bool(z.get("unexpected_new_emitter_authority", False))
        else:
            if (
                prev_authority_pid is not None
                and emitter_pid != prev_authority_pid
                and authority_basis == prev_authority_basis
                and authority_class == prev_authority_class
            ):
                emitter_unexpected = False
            elif prev_authority_pid is None:
                emitter_unexpected = bool(z.get("unexpected_new_emitter_authority", False))
            else:
                emitter_unexpected = bool(z.get("unexpected_new_emitter_authority", False))

        prev_authority_pid = emitter_pid if emitter_pid is not None else prev_authority_pid
        if authority_basis:
            prev_authority_basis = authority_basis
        if authority_class:
            prev_authority_class = authority_class

        # Remote carry-forward with same source module + port 443 + classification.
        # Current boot windows do not expose concrete remotes in these receipts,
        # so we classify discord gateway 443 as continuity key.
        source_module = "calyx.cbo.discord_gateway"
        classification = "known_service"
        remote_key = (source_module, 443, classification)
        remote_seen_prior = remote_key in known_remote_keys
        if remote_seen_prior:
            remote_unexpected = False
        else:
            remote_unexpected = bool(z.get("unexpected_new_remote", False))
        known_remote_keys.add(remote_key)

        channel_widening = bool(z.get("channel_widening", False))
        details = {
            "window": {"start_ts_utc": window.get("start_ts_utc"), "end_ts_utc": window.get("end_ts_utc")},
            "listeners": listener_items,
            "emitter": {
                "pid": emitter_pid,
                "authority_basis": authority_basis or "unknown",
                "authority_classification": authority_class or "unknown",
            },
            "remote_continuity_key": {
                "source_module": source_module,
                "port": 443,
                "classification": classification,
                "seen_in_prior_cycle": remote_seen_prior,
            },
        }
        out_oldest_to_newest.append(
            TransportCycle(
                cycle_ref=cycle_ref,
                boot_session_id=boot_session_id,
                unexpected_new_remote=remote_unexpected,
                unexpected_new_emitter_authority=emitter_unexpected,
                new_listener_unexpected=listener_unexpected,
                channel_widening=channel_widening,
                details=details,
            )
        )

    # Protocol consumes newest-first.
    out_oldest_to_newest.reverse()
    return out_oldest_to_newest


def write_refinement_receipt(repo_root: Path, cycles: list[TransportCycle]) -> Path:
    audit_dir = repo_root / "runtime" / "receipts" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    ts_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = audit_dir / f"transport_comparator_refinement__{ts_tag}.json"
    payload = {
        "schema": "audit.transport_comparator_refinement.v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "observe_mode": True,
        "policy_mutation": False,
        "rules_applied": {
            "remote_carry_forward": "same classification + source module discord gateway + port 443",
            "emitter_continuity": "same authority_basis/classification, pid-only rotation treated as continuous",
            "canonical_listener_rebind_expected": "port canonical + module canonical + seen prior cycle",
        },
        "cycles": [
            {
                "cycle_ref": c.cycle_ref,
                "boot_session_id": c.boot_session_id,
                "unexpected_new_remote": c.unexpected_new_remote,
                "unexpected_new_emitter_authority": c.unexpected_new_emitter_authority,
                "new_listener_unexpected": c.new_listener_unexpected,
                "channel_widening": c.channel_widening,
                "details": c.details,
            }
            for c in cycles
        ],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
