#!/usr/bin/env python3
"""Stewardship liveness probe.

Prints two samples of key lockfiles (mtime + embedded JSON timestamps) separated by a sleep.
This is designed to be run via VS Code tasks to prove continuous loop stewardship.

Usage:
  python -u tools/stewardship_liveness_probe.py --sleep-sec 70
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_LOCK_PATHS = [
    "outgoing/cbo.lock",
    "outgoing/uptime_tracker.lock",
    "outgoing/enhanced_metrics.lock",
    "outgoing/telemetry_sentinel.lock",
    "outgoing/bridge_pulse_scheduler.lock",
    "outgoing/scheduler.lock",
    "outgoing/navigator.lock",
]


def _iso_utc_from_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class LockSample:
    path: str
    exists: bool
    mtime_iso: str | None = None
    size_bytes: int | None = None
    json_iso: str | None = None
    json_ts: float | None = None
    json_ok: bool | None = None
    json_keys: list[str] | None = None
    parse_error: str | None = None


def read_lock(path: Path) -> LockSample:
    if not path.exists():
        return LockSample(path=str(path).replace("\\", "/"), exists=False)

    stat = path.stat()
    mtime_iso = _iso_utc_from_ts(stat.st_mtime)
    size_bytes = stat.st_size

    raw = path.read_text(encoding="utf-8", errors="replace").strip()
    json_iso: str | None = None
    json_ts: float | None = None
    json_ok: bool | None = None
    json_keys: list[str] | None = None
    parse_error: str | None = None

    if raw:
        try:
            j: Any = json.loads(raw)
            if isinstance(j, dict):
                json_keys = sorted([str(k) for k in j.keys()])
                if "iso" in j and isinstance(j["iso"], str):
                    json_iso = j["iso"]
                if "ts" in j and isinstance(j["ts"], (int, float)):
                    json_ts = float(j["ts"])
                if "ok" in j and isinstance(j["ok"], bool):
                    json_ok = j["ok"]
        except Exception as e:  # noqa: BLE001
            parse_error = f"{type(e).__name__}: {e}"

    return LockSample(
        path=str(path).replace("\\", "/"),
        exists=True,
        mtime_iso=mtime_iso,
        size_bytes=size_bytes,
        json_iso=json_iso,
        json_ts=json_ts,
        json_ok=json_ok,
        json_keys=json_keys,
        parse_error=parse_error,
    )


def print_sample(tag: str, root: Path, paths: list[str]) -> None:
    now_iso = _iso_utc_from_ts(time.time())
    print(f"=== SAMPLE {tag} @ {now_iso} ===")
    for rel in paths:
        sample = read_lock(root / rel)
        if not sample.exists:
            print(f"{sample.path}\tMISSING")
            continue

        ok_str = "" if sample.json_ok is None else str(sample.json_ok)
        ts_str = "" if sample.json_ts is None else f"{sample.json_ts:.3f}"
        iso_str = "" if sample.json_iso is None else sample.json_iso
        err_str = "" if sample.parse_error is None else f" parse_error={sample.parse_error}"
        print(
            f"{sample.path}"
            f"\tmtime_utc={sample.mtime_iso}"
            f"\tjson_iso={iso_str}"
            f"\tjson_ts={ts_str}"
            f"\tok={ok_str}"
            f"\tbytes={sample.size_bytes}{err_str}"
        )


def run_probe(root: Path, paths: list[str], sleep_sec: float) -> list[str]:
    """Run probe and return all output lines (also printed to stdout)."""

    lines: list[str] = []

    def emit(line: str) -> None:
        lines.append(line)
        print(line)

    def emit_sample(tag: str) -> None:
        now_iso = _iso_utc_from_ts(time.time())
        emit(f"=== SAMPLE {tag} @ {now_iso} ===")
        for rel in paths:
            sample = read_lock(root / rel)
            if not sample.exists:
                emit(f"{sample.path}\tMISSING")
                continue

            ok_str = "" if sample.json_ok is None else str(sample.json_ok)
            ts_str = "" if sample.json_ts is None else f"{sample.json_ts:.3f}"
            iso_str = "" if sample.json_iso is None else sample.json_iso
            err_str = "" if sample.parse_error is None else f" parse_error={sample.parse_error}"
            emit(
                f"{sample.path}"
                f"\tmtime_utc={sample.mtime_iso}"
                f"\tjson_iso={iso_str}"
                f"\tjson_ts={ts_str}"
                f"\tok={ok_str}"
                f"\tbytes={sample.size_bytes}{err_str}"
            )

    emit_sample("A")
    emit(f"--- sleeping {sleep_sec:.0f}s ---")
    time.sleep(max(0.0, float(sleep_sec)))
    emit_sample("B")

    emit("")
    emit("=== PROCESSES (filtered) ===")
    ps_cmd = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match "
        "'tools\\\\cbo_overseer\\.py|tools\\\\svc_supervisor_adaptive\\.py|tools\\\\svc_supervisor\\.py|"
        "tools\\\\uptime_tracker\\.py|tools\\\\enhanced_metrics_collector\\.py|tools\\\\bridge_pulse_scheduler\\.py|"
        "tools\\\\telemetry_sentinel\\.py' } | "
        "Select-Object ProcessId,Name,CreationDate,CommandLine | "
        "Format-Table -AutoSize | Out-String -Width 260"
    )
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            text=True,
            capture_output=True,
            check=False,
        )
        out = (proc.stdout or "").rstrip()
        err = (proc.stderr or "").rstrip()

        if out:
            for line in out.splitlines():
                emit(line)
        else:
            emit("(no matching processes found, or no stdout)")

        if err:
            emit("")
            emit("--- stderr ---")
            for line in err.splitlines():
                emit(line)
    except Exception as e:  # noqa: BLE001
        emit(f"(process listing failed: {type(e).__name__}: {e})")

    return lines


def print_filtered_processes() -> None:
    print("\n=== PROCESSES (filtered) ===")
    ps_cmd = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match "
        "'tools\\\\cbo_overseer\\.py|tools\\\\svc_supervisor_adaptive\\.py|tools\\\\svc_supervisor\\.py|"
        "tools\\\\uptime_tracker\\.py|tools\\\\enhanced_metrics_collector\\.py|tools\\\\bridge_pulse_scheduler\\.py|"
        "tools\\\\telemetry_sentinel\\.py' } | "
        "Select-Object ProcessId,Name,CreationDate,CommandLine | "
        "Format-Table -AutoSize | Out-String -Width 260"
    )
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception as e:  # noqa: BLE001
        print(f"(process listing failed: {type(e).__name__}: {e})")
        return

    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()

    if out:
        print(out)
    else:
        print("(no matching processes found, or no stdout)")

    if err:
        print("\n--- stderr ---")
        print(err)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.getcwd(), help="Station root directory")
    parser.add_argument("--sleep-sec", type=float, default=70.0)
    parser.add_argument(
        "--output",
        default="",
        help="Optional path to write full probe output (relative to --root if not absolute)",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        default=DEFAULT_LOCK_PATHS,
        help="Relative lockfile paths to probe",
    )
    args = parser.parse_args()

    root = Path(args.root)
    paths = [p.replace("\\", "/") for p in args.paths]

    lines = run_probe(root=root, paths=paths, sleep_sec=float(args.sleep_sec))

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = root / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n(wrote {out_path})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
