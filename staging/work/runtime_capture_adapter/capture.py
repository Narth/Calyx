"""Read-only local runtime capture helpers for staging."""

from __future__ import annotations

import csv
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from staging.work.runtime_capture_adapter.models import (
    CapturedBridgePulse,
    CapturedPort,
    CapturedProcessRow,
    CapturedStationHealth,
    RuntimeCaptureInput,
)


def capture_live_runtime_state(*, repo_root: Path, capture_id: str, corr_id: str) -> RuntimeCaptureInput:
    processes = _capture_process_rows()
    ports_by_pid = _capture_ports_by_pid()
    enriched_processes = [
        CapturedProcessRow.model_validate({**proc.model_dump(mode="json"), "ports": [port.model_dump(mode="json") for port in ports_by_pid.get(proc.pid, [])]})
        for proc in processes
    ]
    station_health = _read_station_health(repo_root / "runtime" / "station_health.json")
    bridge_pulse = _read_bridge_pulse(repo_root / "metrics" / "bridge_pulse.csv")
    return RuntimeCaptureInput(
        schema_name="runtime.capture.input",
        schema_version="1.0.0",
        capture_id=capture_id,
        corr_id=corr_id,
        captured_at_utc=datetime.now(UTC),
        capture_mode="live_read_only",
        process_rows=enriched_processes,
        station_health=station_health,
        bridge_pulse=bridge_pulse,
        capture_notes="Read-only local runtime capture for staging observer ingestion.",
    )


def load_capture_input(path: Path) -> RuntimeCaptureInput:
    return RuntimeCaptureInput.model_validate_json(path.read_text(encoding="utf-8"))


def _capture_process_rows() -> list[CapturedProcessRow]:
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Depth 4",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    payload = json.loads(proc.stdout or "[]")
    rows = payload if isinstance(payload, list) else [payload]
    captured: list[CapturedProcessRow] = []
    for row in rows:
        pid = int(row.get("ProcessId") or 0)
        if pid <= 0:
            continue
        created = row.get("CreationDate")
        created_dt = None
        if isinstance(created, dict) and created.get("DateTime"):
            created_dt = _parse_loose_datetime(created["DateTime"])
        captured.append(
            CapturedProcessRow(
                pid=pid,
                parent_pid=int(row["ParentProcessId"]) if row.get("ParentProcessId") else None,
                process_name=str(row.get("Name") or "unknown"),
                executable_path=row.get("ExecutablePath"),
                command_line=row.get("CommandLine"),
                started_at_utc=created_dt,
            )
        )
    return captured


def _capture_ports_by_pid() -> dict[int, list[CapturedPort]]:
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Get-NetTCPConnection -ErrorAction SilentlyContinue | Select-Object OwningProcess,LocalAddress,LocalPort,RemoteAddress,RemotePort,State | ConvertTo-Json -Depth 4",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    stdout = proc.stdout.strip()
    if not stdout:
        return {}
    payload = json.loads(stdout)
    rows = payload if isinstance(payload, list) else [payload]
    by_pid: dict[int, list[CapturedPort]] = {}
    for row in rows:
        pid = int(row.get("OwningProcess") or 0)
        if pid <= 0:
            continue
        by_pid.setdefault(pid, []).append(
            CapturedPort(
                local_address=row.get("LocalAddress"),
                local_port=int(row["LocalPort"]) if row.get("LocalPort") else None,
                remote_address=row.get("RemoteAddress"),
                remote_port=int(row["RemotePort"]) if row.get("RemotePort") else None,
                state=str(row.get("State")) if row.get("State") is not None else None,
            )
        )
    return by_pid


def _read_station_health(path: Path) -> CapturedStationHealth | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    captured_at = _parse_iso(payload.get("emitted_ts_utc") or payload.get("health_ts"))
    top_processes = [f"{item.get('name')}#{item.get('pid')}" for item in payload.get("top", []) if item.get("name") and item.get("pid")]
    entropy_sources = [f"{item.get('name')}" for item in payload.get("entropy", {}).get("entropy_sources", []) if item.get("name")]
    return CapturedStationHealth(
        source_path=str(path),
        captured_at_utc=captured_at,
        health=payload.get("health", "unknown"),
        cpu_pct=payload.get("cpu_pct"),
        ram_pct=payload.get("ram_pct"),
        interval_s=payload.get("interval_s"),
        memory_pressure_tier=payload.get("memory_pressure_tier"),
        truth_state=payload.get("truth_state"),
        stale_reason=payload.get("stale_reason"),
        top_processes=top_processes,
        entropy_sources=entropy_sources,
        gpu_metrics_present=payload.get("gpu") is not None,
        expiry_sweep_invoked=None,
    )


def _read_bridge_pulse(path: Path) -> CapturedBridgePulse | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return None
    last = rows[-1]
    return CapturedBridgePulse(
        source_path=str(path),
        captured_at_utc=_parse_iso(last["timestamp"]),
        phase=last["phase"],
        status=last.get("status"),
        details=last["details"],
    )


def _parse_iso(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _parse_loose_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace(" ", "T")).astimezone(UTC)
