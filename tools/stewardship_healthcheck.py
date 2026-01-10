#!/usr/bin/env python3
"""Stewardship health check (read-only collection + explicit export).

Stabilization rules:
- Default behavior is read-only (collect only).
- Export is explicit via CLI flag or launcher button.

Writes (only when --write):
- reports/stewardship/health/healthcheck_<timestamp>.json
- reports/stewardship/health/healthcheck_<timestamp>.md (optional summary)
- append one line to logs/stewardship/healthcheck_runs.jsonl

No other writes.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_LOCKS: Dict[str, Dict[str, Any]] = {
    "uptime_tracker": {"path": "outgoing/uptime_tracker.lock", "interval_sec": 60},
    "enhanced_metrics": {"path": "outgoing/enhanced_metrics.lock", "interval_sec": 60},
    "telemetry_sentinel": {"path": "outgoing/telemetry_sentinel.lock", "interval_sec": 60},
    "bridge_pulse_scheduler": {"path": "outgoing/bridge_pulse_scheduler.lock", "interval_sec": 60},
    "cbo": {"path": "outgoing/cbo.lock", "interval_sec": 30},
}

CBO_ACTIVITY_CANDIDATES = [
    "outgoing/bridge_actions.log",
    "outgoing/cbo/bridge_actions.log",
    "outgoing/cbo/bridge_actions.jsonl",
    "outgoing/cbo/activity.log",
    "logs/cbo_activity.log",
]


def _utc_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_read_text(path: Path, max_bytes: int = 256_000) -> str:
    try:
        if not path.exists():
            return ""
        data = path.read_bytes()
        if len(data) > max_bytes:
            data = data[-max_bytes:]
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _tail_lines(text: str, n: int) -> list[str]:
    lines = text.splitlines()
    if len(lines) <= n:
        return lines
    return lines[-n:]


def _parse_json_maybe(raw: str) -> Optional[dict[str, Any]]:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        v = json.loads(raw)
        return v if isinstance(v, dict) else None
    except Exception:
        return None


def _lock_info(now: float, *, name: str, rel_path: str, interval_sec: float) -> dict[str, Any]:
    path = (ROOT / rel_path).resolve()
    exists = path.exists()
    threshold = float(interval_sec) * 3.0

    if not exists:
        return {
            "name": name,
            "path": str(path),
            "status": "MISSING",
            "age_sec": None,
            "threshold_sec": threshold,
            "mtime_utc": None,
            "json": None,
        }

    try:
        mtime = path.stat().st_mtime
    except Exception:
        mtime = now

    age = max(0.0, now - mtime)
    raw = _safe_read_text(path, max_bytes=64_000)
    parsed = _parse_json_maybe(raw)

    status = "OK" if age <= threshold else "STALE"

    return {
        "name": name,
        "path": str(path),
        "status": status,
        "age_sec": round(age, 2),
        "threshold_sec": threshold,
        "mtime_utc": _utc_iso(mtime),
        "json": parsed,
    }


def _find_git_root() -> Optional[Path]:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=3,
        )
        if proc.returncode != 0:
            return None
        p = proc.stdout.strip()
        return Path(p) if p else None
    except Exception:
        return None


def _git(cmd: list[str], cwd: Path) -> Optional[str]:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=3)
        if proc.returncode != 0:
            return None
        return proc.stdout.strip()
    except Exception:
        return None


def collect_repo_sanity() -> dict[str, Any]:
    root = _find_git_root()
    if root is None:
        return {"git": False}

    branch = _git(["git", "rev-parse", "--abbrev-ref", "HEAD"], root)
    head = _git(["git", "rev-parse", "HEAD"], root)
    origin = _git(["git", "remote", "get-url", "origin"], root)

    status = _git(["git", "status", "--porcelain"], root)
    dirty = bool(status)

    return {
        "git": True,
        "root": str(root),
        "branch": branch,
        "head": head,
        "dirty": dirty,
        "origin": origin,
    }


def _windows_find_processes_cmd_contains(needle: str) -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    ps = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -and ($_.CommandLine -like '*" + needle + "*') -and ($_.CommandLine -notlike '*Get-CimInstance Win32_Process*') } | "
        "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    )
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if proc.returncode != 0:
            return []
        raw = (proc.stdout or "").strip()
        if not raw:
            return []
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return []
        matches: list[dict[str, Any]] = []
        for d in data:
            if not isinstance(d, dict):
                continue
            cmd = d.get("CommandLine")
            matches.append(
                {
                    "pid": int(d.get("ProcessId")) if d.get("ProcessId") is not None else None,
                    "name": d.get("Name"),
                    "cmdline": [cmd] if isinstance(cmd, str) else [],
                }
            )
        return [m for m in matches if m.get("pid") is not None]
    except Exception:
        return []


def collect_supervisor_status() -> dict[str, Any]:
    """Best-effort detection of the Windows adaptive supervisor."""
    matches: list[dict[str, Any]] = []
    detected = False
    running: Optional[bool] = None

    try:
        import psutil  # type: ignore

        detected = True
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline") or []
                joined = " ".join(cmdline)
                if "svc_supervisor_adaptive.py" in joined.replace("/", "\\"):
                    matches.append(
                        {
                            "pid": int(proc.info["pid"]),
                            "name": proc.info.get("name"),
                            "cmdline": cmdline,
                        }
                    )
            except Exception:
                continue
    except Exception:
        pass

    cim_matches = _windows_find_processes_cmd_contains("svc_supervisor_adaptive.py")
    if cim_matches:
        detected = True
        existing_pids = {m.get("pid") for m in matches}
        for m in cim_matches:
            if m.get("pid") not in existing_pids:
                matches.append(m)

    if detected:
        running = len(matches) > 0

    return {"detected": detected, "running": running, "processes": matches}


def collect_cbo_activity(max_lines: int = 12) -> dict[str, Any]:
    for rel in CBO_ACTIVITY_CANDIDATES:
        p = (ROOT / rel).resolve()
        if p.exists():
            txt = _safe_read_text(p, max_bytes=256_000)
            return {
                "found": True,
                "path": str(p),
                "tail": _tail_lines(txt, max_lines),
            }
    return {"found": False}


def compute_overall_station_status(locks: list[dict[str, Any]], supervisor: dict[str, Any]) -> str:
    ok = sum(1 for l in locks if l.get("status") == "OK")
    bad = len(locks) - ok

    supervisor_running = bool(supervisor.get("running")) if supervisor.get("running") is not None else False

    if ok == len(locks):
        return "OK"
    if ok == 0:
        return "DOWN"
    if bad >= (len(locks) // 2 + 1):
        return "DOWN"
    if (not supervisor_running) and ok <= 2:
        return "DOWN"
    return "DEGRADED"


def collect_health_snapshot() -> dict[str, Any]:
    now = time.time()
    locks = [
        _lock_info(now, name=name, rel_path=spec["path"], interval_sec=float(spec["interval_sec"]))
        for name, spec in REQUIRED_LOCKS.items()
    ]

    supervisor = collect_supervisor_status()
    repo = collect_repo_sanity()
    cbo_activity = collect_cbo_activity(max_lines=12)

    overall = compute_overall_station_status(locks, supervisor)

    sentinel_pid = None
    for l in locks:
        if l.get("name") == "telemetry_sentinel" and isinstance(l.get("json"), dict):
            sentinel_pid = (l["json"] or {}).get("pid")

    return {
        "ts": now,
        "iso": _utc_iso(now),
        "mode": "READ_ONLY",
        "phase": "Stabilization",
        "overall_status": overall,
        "locks": locks,
        "supervisor": supervisor,
        "sentinel_pid": sentinel_pid,
        "repo": repo,
        "cbo_activity": cbo_activity,
    }


def _render_md(snapshot: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Stewardship Health Check")
    lines.append("")
    lines.append(f"- Time (UTC): {snapshot.get('iso')}")
    lines.append(f"- Overall: {snapshot.get('overall_status')}")
    lines.append(f"- Mode: READ-ONLY (Stabilization)")
    lines.append("")

    lines.append("## Stewardship Loops")
    lines.append("")
    lines.append("| lock | status | age_sec | mtime_utc | path |")
    lines.append("|---|---|---:|---|---|")
    for l in snapshot.get("locks") or []:
        lines.append(
            "| {name} | {status} | {age} | {mtime} | {path} |".format(
                name=l.get("name"),
                status=l.get("status"),
                age=l.get("age_sec") if l.get("age_sec") is not None else "-",
                mtime=l.get("mtime_utc") or "-",
                path=l.get("path") or "-",
            )
        )

    lines.append("")
    lines.append("## Repo Hooks")
    repo = snapshot.get("repo") or {}
    if repo.get("git"):
        lines.append("")
        lines.append(f"- Root: {repo.get('root')}")
        lines.append(f"- Branch: {repo.get('branch')}")
        lines.append(f"- HEAD: {repo.get('head')}")
        lines.append(f"- Dirty: {repo.get('dirty')}")
        if repo.get("origin"):
            lines.append(f"- Origin: {repo.get('origin')}")
    else:
        lines.append("")
        lines.append("- Git: not detected")

    lines.append("")
    lines.append("## CBO Presence")
    cbo = next((l for l in (snapshot.get("locks") or []) if l.get("name") == "cbo"), None)
    if cbo:
        lines.append("")
        lines.append(f"- cbo.lock: {cbo.get('status')} (mtime_utc={cbo.get('mtime_utc')})")

    act = snapshot.get("cbo_activity") or {}
    if act.get("found"):
        lines.append("")
        lines.append(f"- Activity log: {act.get('path')}")
        lines.append("\n```text")
        for line in act.get("tail") or []:
            lines.append(str(line))
        lines.append("```")
    else:
        lines.append("")
        lines.append("- Activity log: not found")

    return "\n".join(lines) + "\n"


def write_healthcheck(snapshot: dict[str, Any], *, write_md: bool = True) -> dict[str, Any]:
    ts = snapshot.get("ts")
    now = float(ts) if isinstance(ts, (int, float)) else time.time()
    stamp = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    out_dir = (ROOT / "reports" / "stewardship" / "health").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"healthcheck_{stamp}.json"
    md_path = out_dir / f"healthcheck_{stamp}.md"

    json_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    if write_md:
        md_path.write_text(_render_md(snapshot), encoding="utf-8")

    runs_log = (ROOT / "logs" / "stewardship" / "healthcheck_runs.jsonl").resolve()
    runs_log.parent.mkdir(parents=True, exist_ok=True)

    run_event = {
        "ts": now,
        "iso": _utc_iso(now),
        "event": "healthcheck_run",
        "overall_status": snapshot.get("overall_status"),
        "artifacts": {
            "json": str(json_path),
            "md": str(md_path) if write_md else None,
        },
        "repo": snapshot.get("repo"),
    }
    with runs_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(run_event, ensure_ascii=False) + "\n")

    return {
        "ok": True,
        "json_path": str(json_path),
        "md_path": str(md_path) if write_md else None,
        "log_path": str(runs_log),
        "overall_status": snapshot.get("overall_status"),
    }


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Stewardship Health Check")
    ap.add_argument(
        "--write",
        action="store_true",
        help="Write timestamped artifacts + append healthcheck run log (explicit export)",
    )
    ap.add_argument("--no-md", action="store_true", help="Skip markdown summary output")
    args = ap.parse_args(argv)

    try:
        import sys

        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    snap = collect_health_snapshot()

    if not args.write:
        print(json.dumps(snap, indent=2, ensure_ascii=False))
        return 0

    result = write_healthcheck(snap, write_md=not args.no_md)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
