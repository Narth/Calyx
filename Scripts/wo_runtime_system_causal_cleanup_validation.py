#!/usr/bin/env python3
"""Validate runtime-system causal envelope cleanup without expanding system authority."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = REPO_ROOT / "runtime"
LEDGER_DIR = RUNTIME_DIR / "ledger"
RECEIPT_DIR = RUNTIME_DIR / "receipts" / "audit"

TARGETED_RUNTIME_EVENTS = {
    ("heartbeat", "heartbeat.tick"),
    ("heartbeat", "restart.detected"),
}
REQUIRED_RUNTIME_EVENTS = {
    ("heartbeat", "heartbeat.tick"),
}
TARGETED_BOOT_EVENTS = {
    ("avatar", "station.boot"),
    ("avatar", "station.service.identity"),
    ("dev_harness", "station.boot"),
    ("dev_harness", "station.service.identity"),
}
ALLOWED_RUNTIME_SYSTEM_EVENTS = set(TARGETED_RUNTIME_EVENTS)

TASK_EVENT_NAMES = {
    "system.task.triggered",
    "system.task.completed",
    "system.task.failed",
    "budget.task.recorded",
    "calyx_gateway.heartbeat",
    "calyx_gateway.heartbeat_failed",
    "discord.heartbeat.sent",
}
OUTBOUND_EVENT_NAMES = {
    "calyx_gateway.heartbeat",
    "calyx_gateway.heartbeat_failed",
    "discord.heartbeat.sent",
    "discord.heartbeat.sent.emit_failed",
}
TOOL_EVENT_NAMES = {
    "tool.used",
}
HUMAN_EVENT_HINTS = (
    "request",
    "inbound",
    "response.finalized",
    "station.smoke",
)


@dataclass
class Finding:
    category: str
    component: str
    event: str
    ts_utc: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "category": self.category,
            "component": self.component,
            "event": self.event,
            "ts_utc": self.ts_utc,
            "reason": self.reason,
        }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate runtime-system causal cleanup.")
    parser.add_argument("--since-minutes", type=int, default=30)
    return parser.parse_args()


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _load_window_records(since_minutes: int) -> tuple[list[dict[str, Any]], datetime, datetime]:
    end = datetime.now(UTC)
    start = end - timedelta(minutes=since_minutes)
    rows: list[dict[str, Any]] = []
    for path in sorted(LEDGER_DIR.glob("station_events__*.jsonl")):
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = _parse_ts(record.get("ts_utc") or record.get("ts"))
                    if ts is None or ts < start or ts > end:
                        continue
                    rows.append(record)
        except OSError:
            continue
    rows.sort(key=lambda rec: rec.get("ts_utc") or rec.get("ts") or "")
    return rows, start, end


def _event_key(record: dict[str, Any]) -> tuple[str, str]:
    return str(record.get("component") or ""), str(record.get("event") or "")


def _system_phase(record: dict[str, Any]) -> str:
    env = record.get("causal_envelope") or {}
    if not isinstance(env, dict):
        return ""
    return str(env.get("system_phase") or "")


def _causal_kind(record: dict[str, Any]) -> str:
    env = record.get("causal_envelope") or {}
    if not isinstance(env, dict):
        return ""
    return str(env.get("causal_kind") or "")


def _data_map(record: dict[str, Any]) -> dict[str, Any]:
    data = record.get("data")
    return data if isinstance(data, dict) else {}


def _is_human_misuse(record: dict[str, Any]) -> str | None:
    if _causal_kind(record) != "system":
        return None
    if record.get("corr_id"):
        return "system event carried corr_id"
    data = _data_map(record)
    if data.get("method") or data.get("path"):
        return "system event carried request boundary fields"
    event = str(record.get("event") or "")
    if any(hint in event for hint in HUMAN_EVENT_HINTS):
        return f"system event matched human hint: {event}"
    return None


def _is_task_misuse(record: dict[str, Any]) -> str | None:
    if _causal_kind(record) != "system":
        return None
    data = _data_map(record)
    if any(data.get(field) for field in ("task_corr_id", "task_name", "schedule_id", "trigger_reason")):
        return "system event carried task fields"
    if str(record.get("event") or "") in TASK_EVENT_NAMES:
        return "system event matched scheduled task event"
    return None


def _is_runtime_tool_or_outbound(record: dict[str, Any]) -> str | None:
    if _causal_kind(record) != "system" or _system_phase(record) != "runtime":
        return None
    event = str(record.get("event") or "")
    if event in TOOL_EVENT_NAMES:
        return "runtime system event performed tool execution"
    if event in OUTBOUND_EVENT_NAMES:
        return "runtime system event performed outbound send"
    return None


def _write_receipt(payload: dict[str, Any]) -> Path:
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    path = RECEIPT_DIR / f"wo_runtime_system_causal_cleanup_validation__{ts}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> int:
    args = _parse_args()
    records, start, end = _load_window_records(args.since_minutes)

    findings: list[Finding] = []
    targeted_runtime_hits: defaultdict[str, int] = defaultdict(int)
    targeted_boot_hits: defaultdict[str, int] = defaultdict(int)
    runtime_phase_breakdown: defaultdict[str, int] = defaultdict(int)
    system_phase_breakdown: defaultdict[str, int] = defaultdict(int)
    all_missing_context = 0

    for record in records:
        component, event = _event_key(record)
        key_text = f"{component}:{event}"
        causal_kind = _causal_kind(record)
        phase = _system_phase(record)
        ts_utc = str(record.get("ts_utc") or record.get("ts") or "")

        if record.get("event") == "audit.context.missing":
            all_missing_context += 1

        if causal_kind == "system":
            system_phase_breakdown[f"{component}:{phase or 'unset'}"] += 1
        if phase == "runtime":
            runtime_phase_breakdown[key_text] += 1

        if (component, event) in TARGETED_RUNTIME_EVENTS:
            targeted_runtime_hits[key_text] += 1
            if causal_kind != "system" or phase != "runtime":
                findings.append(Finding("targeted_runtime_wrong_context", component, event, ts_utc, f"expected system/runtime, got {causal_kind or 'unset'}/{phase or 'unset'}"))

        if (component, event) in TARGETED_BOOT_EVENTS:
            targeted_boot_hits[key_text] += 1
            if causal_kind != "system" or phase != "boot":
                findings.append(Finding("targeted_boot_wrong_context", component, event, ts_utc, f"expected system/boot, got {causal_kind or 'unset'}/{phase or 'unset'}"))

        if phase == "runtime" and (component, event) not in ALLOWED_RUNTIME_SYSTEM_EVENTS:
            findings.append(Finding("runtime_scope_expansion", component, event, ts_utc, "runtime system phase used outside explicit whitelist"))

        human_reason = _is_human_misuse(record)
        if human_reason:
            findings.append(Finding("human_labeled_system", component, event, ts_utc, human_reason))

        task_reason = _is_task_misuse(record)
        if task_reason:
            findings.append(Finding("task_labeled_system", component, event, ts_utc, task_reason))

        runtime_action_reason = _is_runtime_tool_or_outbound(record)
        if runtime_action_reason:
            findings.append(Finding("runtime_tool_or_outbound", component, event, ts_utc, runtime_action_reason))

    for component, event in sorted(REQUIRED_RUNTIME_EVENTS):
        key_text = f"{component}:{event}"
        if targeted_runtime_hits[key_text] == 0:
            findings.append(Finding("targeted_runtime_missing", component, event, "", "targeted runtime event not observed in validation window"))

    for component, event in sorted(TARGETED_BOOT_EVENTS):
        key_text = f"{component}:{event}"
        if targeted_boot_hits[key_text] == 0:
            findings.append(Finding("targeted_boot_missing", component, event, "", "targeted boot event not observed in validation window"))

    misuse_counts: dict[str, int] = defaultdict(int)
    per_component_breakdown: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for finding in findings:
        misuse_counts[finding.category] += 1
        per_component_breakdown[finding.component][finding.category] += 1

    validation_pass = not findings and all_missing_context == 0
    receipt = {
        "schema": "audit.runtime_system_causal_cleanup_validation.v1",
        "ts_utc": datetime.now(UTC).isoformat(),
        "since_minutes": args.since_minutes,
        "window_start_ts_utc": start.isoformat(),
        "window_end_ts_utc": end.isoformat(),
        "pass": validation_pass,
        "audit_context_missing_count": all_missing_context,
        "misuse_counts": dict(misuse_counts),
        "classification_drift_summary": {
            "runtime_phase_breakdown": dict(sorted(runtime_phase_breakdown.items())),
            "system_phase_breakdown": dict(sorted(system_phase_breakdown.items())),
            "targeted_runtime_hits": dict(sorted(targeted_runtime_hits.items())),
            "targeted_boot_hits": dict(sorted(targeted_boot_hits.items())),
        },
        "per_component_breakdown": {
            component: dict(sorted(counts.items()))
            for component, counts in sorted(per_component_breakdown.items())
        },
        "findings": [finding.to_dict() for finding in findings],
    }
    receipt_path = _write_receipt(receipt)
    print(json.dumps({"pass": validation_pass, "receipt_path": str(receipt_path), "audit_context_missing_count": all_missing_context, "misuse_counts": dict(misuse_counts)}, ensure_ascii=False))
    return 0 if validation_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
