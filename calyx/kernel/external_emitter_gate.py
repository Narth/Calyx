"""
WO_OPENCLAW_DECOMMISSION_GATING_V2 — Detect and fail-closed against external emitters.
Attribution rules: process/task/service/port containing "openclaw" → external.emitter.openclaw.
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

EXTERNAL_EMITTERS_DENYLIST = ["openclaw"]
OPENCLAW_PORTS = [18789]  # OpenClaw gateway default


def _resolve_repo_root() -> Path:
    env = os.environ.get("CALYX_REPO_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


def _is_openclaw_process(binary_path: str, task_name: str, service_name: str) -> bool:
    """Attribution: path or name contains openclaw → OpenClaw."""
    s = (binary_path or "").lower() + " " + (task_name or "").lower() + " " + (service_name or "").lower()
    return "openclaw" in s


def detect_openclaw_processes() -> list[dict[str, Any]]:
    """Detect running processes attributable to OpenClaw. Windows: wmic/Get-Process."""
    out: list[dict[str, Any]] = []
    if platform.system() != "Windows":
        return out
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process | Where-Object { $_.Path } | Select-Object Id, ProcessName, Path | ConvertTo-Json -Compress"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(_resolve_repo_root()),
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return out
        import json
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return out
        if data is None:
            return out
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return out
        for p in data:
            path = (p.get("Path") or "").replace("\\", "/").lower()
            name = (p.get("ProcessName") or "").lower()
            if "openclaw" in path or "openclaw" in name:
                out.append({
                    "evidence_type": "process",
                    "evidence_value": p.get("Path") or p.get("ProcessName", ""),
                    "pid": p.get("Id"),
                    "path": p.get("Path"),
                })
    except Exception:
        pass
    return out


def detect_openclaw_services() -> list[dict[str, Any]]:
    """Detect Windows services with openclaw in name."""
    out: list[dict[str, Any]] = []
    if platform.system() != "Windows":
        return out
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Service | Where-Object { $_.Name -like '*openclaw*' -or $_.DisplayName -like '*openclaw*' } | Select-Object Name, DisplayName, Status | ConvertTo-Json -Compress"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return out
        import json
        data = json.loads(proc.stdout)
        if isinstance(data, dict):
            data = [data]
        for s in data:
            out.append({
                "evidence_type": "service",
                "evidence_value": s.get("Name") or s.get("DisplayName", ""),
                "status": s.get("Status"),
            })
    except Exception:
        pass
    return out


def detect_openclaw_tasks() -> list[dict[str, Any]]:
    """Detect scheduled tasks with openclaw in name. Only flag Ready/Running (Disabled = inert)."""
    out: list[dict[str, Any]] = []
    if platform.system() != "Windows":
        return out
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-ScheduledTask | Where-Object { ($_.TaskName -like '*openclaw*' -or $_.TaskPath -like '*openclaw*') -and $_.State -ne 'Disabled' } | Select-Object TaskName, TaskPath, State | ConvertTo-Json -Compress"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return out
        import json
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return out
        if data is None:
            return out
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return out
        for t in data:
            out.append({
                "evidence_type": "task",
                "evidence_value": t.get("TaskName") or t.get("TaskPath", ""),
                "state": t.get("State"),
            })
    except Exception:
        pass
    return out


def detect_openclaw_ports() -> list[dict[str, Any]]:
    """Detect listeners on OpenClaw-known ports (e.g. 18789)."""
    out: list[dict[str, Any]] = []
    if platform.system() != "Windows":
        return out
    for port in OPENCLAW_PORTS:
        try:
            proc = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in (proc.stdout or "").splitlines():
                if f":{port}" in line or f".{port}" in line:
                    parts = line.split()
                    pid = parts[-1] if parts else ""
                    out.append({
                        "evidence_type": "port",
                        "evidence_value": f"port_{port}",
                        "port": port,
                        "pid": pid,
                    })
                    break
        except Exception:
            pass
    return out


def detect_openclaw_presence() -> tuple[bool, list[dict[str, Any]]]:
    """
    Detect any OpenClaw presence. Returns (detected, list of evidence dicts).
    Each evidence: {emitter, evidence_type, evidence_value, pid?, path?}
    """
    evidence: list[dict[str, Any]] = []
    for e in detect_openclaw_processes():
        e["emitter"] = "openclaw"
        evidence.append(e)
    for e in detect_openclaw_services():
        e["emitter"] = "openclaw"
        evidence.append(e)
    for e in detect_openclaw_tasks():
        e["emitter"] = "openclaw"
        evidence.append(e)
    for e in detect_openclaw_ports():
        e["emitter"] = "openclaw"
        evidence.append(e)
    return len(evidence) > 0, evidence


def check_external_emitter_gate(
    repo_root: Path | None = None,
    denylist: list[str] | None = None,
    allow_openclaw_migration: bool | None = None,
) -> tuple[bool, str, list[dict[str, Any]]]:
    """
    WO_OPENCLAW_DECOMMISSION_GATING_V2: Gate against external emitters.
    Returns (pass, reason, evidence_list).
    pass=False means OpenClaw (or denylist emitter) detected → fail-closed.
    """
    _root = repo_root or _resolve_repo_root()
    _deny = denylist or os.environ.get("EXTERNAL_EMITTERS_DENYLIST", "openclaw").split(",")
    _deny = [d.strip().lower() for d in _deny if d.strip()]
    if not _deny:
        _deny = EXTERNAL_EMITTERS_DENYLIST
    _allow_migration = allow_openclaw_migration
    if _allow_migration is None:
        _allow_migration = os.environ.get("ALLOW_OPENCLAW_FOR_MIGRATION", "").strip().lower() in ("true", "1", "yes")

    if _allow_migration and "openclaw" in _deny:
        return True, "ALLOW_OPENCLAW_FOR_MIGRATION=true", []

    detected, evidence = detect_openclaw_presence()
    if not detected:
        return True, "no_external_emitter_detected", []

    return False, "openclaw_detected", evidence


def main() -> int:
    """CLI: run gate, emit to ledger, exit 1 if detected."""
    detected, evidence = detect_openclaw_presence()
    if detected:
        print("OpenClaw detected:", file=sys.stderr)
        for e in evidence:
            print(f"  {e.get('evidence_type')}: {e.get('evidence_value')} (pid={e.get('pid')})", file=sys.stderr)
        try:
            from calyx.kernel.event_ledger import emit as _le
            for ev in evidence:
                _le("WARN", "external_emitter_gate", "audit.external.emitter.detected", "OpenClaw detected", data={
                    "emitter": "openclaw",
                    "evidence_type": ev.get("evidence_type", ""),
                    "evidence_value": str(ev.get("evidence_value", ""))[:200],
                    "pid": ev.get("pid"),
                    "path": str(ev.get("path", ""))[:200] if ev.get("path") else None,
                })
            _le("WARN", "external_emitter_gate", "audit.runtime.singularity.breach", "External emitter gate: OpenClaw detected", data={"evidence_count": len(evidence)})
            _le("WARN", "external_emitter_gate", "governance.assertion.failed", "OpenClaw detected; fail-closed", data={"reason": "external_emitter_detected"})
        except Exception:
            pass
        return 1
    print("No OpenClaw detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
