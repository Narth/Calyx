"""Systems Integrator Probe: assess non-agent data and surface upgrade/change suggestions.

- Writes outgoing/sysint.lock every --interval seconds with status="running" and phase="probe".
- Evaluates project hygiene and integration points without external network calls:
  - Optional deps present (e.g., psutil, metaphone) for richer features.
  - Stale/heavy logs worth rotating.
  - Helpful tasks and control modes available but not active.
  - Presence and shape of config files and samples.
- When actionable suggestions exist, sets status to "warn" and exposes a concise suggestion plus an open_path for quick review.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOCK = OUT / "sysint.lock"
VERSION = "0.1.0"


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_hb(phase: str, status: str = "running", extra: Optional[Dict[str, Any]] = None) -> None:
    try:
        payload: Dict[str, Any] = {
            "name": "sysint",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": time.time(),
            "version": VERSION,
        }
        if extra:
            payload.update(extra)
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _exists(p: Path) -> bool:
    try:
        return p.exists()
    except Exception:
        return False


def _file_size_mb(p: Path) -> int:
    try:
        return int(p.stat().st_size / (1024 * 1024))
    except Exception:
        return -1


def _has_module(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def _is_acknowledged(suggestion_id: str) -> bool:
    """Check if a suggestion has been acknowledged"""
    from calyx.cbo.runtime_paths import get_sysint_acknowledged_path
    ack_file = get_sysint_acknowledged_path(ROOT)
    if not ack_file.exists():
        return False
    
    try:
        with ack_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        if record.get("suggestion_id") == suggestion_id:
                            return True
                    except Exception:
                        pass
    except Exception:
        pass
    return False

def evaluate() -> Dict[str, Any]:
    suggestions: List[Dict[str, Any]] = []

    # --- WSL health probe (Windows-first environments) ---
    def _running_in_wsl() -> bool:
        try:
            # Heuristic: /proc/version contains 'Microsoft' on WSL
            with open('/proc/version', 'r') as f:
                v = f.read().lower()
            return 'microsoft' in v or 'wsl' in v
        except Exception:
            return False
    def _wsl_cmd(args: List[str], timeout: int = 4) -> Tuple[int, str]:
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
            out = (proc.stdout or "") + (proc.stderr or "")
            return proc.returncode, out
        except Exception as e:
            return 1, f"exception: {e}"

    def _wsl_health() -> Dict[str, Any]:
        info: Dict[str, Any] = {"wsl_ok": False, "venv_ok": False, "python_ok": False}
        # Is WSL callable?
        rc, _ = _wsl_cmd(["wsl", "bash", "-lc", "echo ok"], timeout=3)
        info["wsl_ok"] = (rc == 0)
        if not info["wsl_ok"]:
            return info
        # Is venv present?
        rc, out = _wsl_cmd(["wsl", "bash", "-lc", "test -d ~/.calyx-venv && echo ok || echo no"], timeout=3)
        info["venv_ok"] = (rc == 0)
        # Is python in venv executable?
        rc, out = _wsl_cmd(["wsl", "bash", "-lc", "source ~/.calyx-venv/bin/activate && python -V"], timeout=5)
        info["python_ok"] = (rc == 0)
        info["python_ver"] = out.strip() if isinstance(out, str) else None
        return info

    if _running_in_wsl():
        # When running inside WSL, we consider WSL present by definition and skip "wsl_not_available".
        # We also skip the venv/python checks here to avoid false warnings when invoked from Linux.
        pass
    else:
        wsl = _wsl_health()
        if not wsl.get("wsl_ok") and not _is_acknowledged("wsl_not_available"):
            suggestions.append({
                "id": "wsl_not_available",
                "title": "WSL not accessible",
                "summary": "Windows Subsystem for Linux is not responding to basic commands.",
                "open_path": str(ROOT / "OPERATIONS.md"),
                "hint": "Ensure WSL is installed and enabled, then reboot. In PowerShell (Admin): wsl --status",
            })
        else:
            if not wsl.get("venv_ok") and not _is_acknowledged("wsl_venv_missing"):
                suggestions.append({
                    "id": "wsl_venv_missing",
                    "title": "WSL venv not found (~/.calyx-venv)",
                    "summary": "Supervisor relies on ~/.calyx-venv. Create and install requirements there.",
                    "open_path": str(ROOT / "requirements.txt"),
                    "hint": "wsl bash -lc 'python3 -m venv ~/.calyx-venv && source ~/.calyx-venv/bin/activate && pip install -r /mnt/c/Calyx_Terminal/requirements.txt'",
                })
            if wsl.get("venv_ok") and not wsl.get("python_ok") and not _is_acknowledged("wsl_python_unavailable"):
                suggestions.append({
                    "id": "wsl_python_unavailable",
                    "title": "WSL Python not available in venv",
                    "summary": "Activating ~/.calyx-venv did not yield a working Python (python -V failed).",
                    "open_path": str(ROOT / "OPERATIONS.md"),
                    "hint": "wsl bash -lc 'source ~/.calyx-venv/bin/activate && python -V || which python'",
                })

    # Optional packages that improve functionality
    if not _has_module("psutil"):
        suggestions.append({
            "id": "install_psutil",
            "title": "Install psutil for richer resource snapshots",
            "summary": "Navigator can report CPU/RAM precisely when psutil is installed.",
            "open_path": str(ROOT / "requirements.txt"),
            "hint": "Add 'psutil>=5.9' to requirements.txt and install in your venv.",
        })
    if not _has_module("metaphone"):
        suggestions.append({
            "id": "install_metaphone",
            "title": "Install metaphone for better phonetic KWS",
            "summary": "KWS can use Double Metaphone for stronger phonetic matching.",
            "open_path": str(ROOT / "requirements.txt"),
            "hint": "Add 'Metaphone>=0.6' to requirements.txt and install.",
        })

    # Logs health
    wake_audit = ROOT / "logs" / "wake_word_audit.csv"
    if _exists(wake_audit) and _file_size_mb(wake_audit) > 50:
        suggestions.append({
            "id": "rotate_wake_audit",
            "title": "Rotate wake_word_audit.csv (large log)",
            "summary": "Audit log exceeds 50MB; consider rotating to keep operations snappy.",
            "open_path": str(wake_audit),
            "hint": "Archive older lines to logs/archive/ and reset the file.",
        })

    # Samples present for wake word eval
    samples_pos = ROOT / "samples" / "wake_word" / "positive"
    samples_neg = ROOT / "samples" / "wake_word" / "negative"
    if not (_exists(samples_pos) and _exists(samples_neg)):
        suggestions.append({
            "id": "add_wake_samples",
            "title": "Add wake-word sample audio for eval",
            "summary": "Populate samples/wake_word/{positive,negative} to enable offline evaluation.",
            "open_path": str(ROOT / "samples" / "wake_word" / "README.md"),
            "hint": "Place small WAV files to exercise tools/eval_wake_word.py.",
        })

    # Control mode availability hint
    nav_task_ws = ROOT / ".vscode" / "tasks.json"
    if _exists(nav_task_ws):
        # Encourage running navigator control if not already writing control lock
        if not _exists(OUT / "navigator_control.lock"):
            suggestions.append({
                "id": "enable_nav_control",
                "title": "Enable Traffic Navigator control mode",
                "summary": "Let navigator auto-pause triage on contention and tune probe cadence.",
                "open_path": str(nav_task_ws),
                "hint": "Use VS Code task 'Run Traffic Navigator (WSL, control)'.",
            })

    healthy = len(suggestions) == 0
    if healthy:
        msg = "Systems nominal"
    else:
        msg = f"Upgrade available: {len(suggestions)} suggestion(s)"

    # Pick a top suggestion for the UI
    top = suggestions[0] if suggestions else None
    open_path = top.get("open_path") if isinstance(top, dict) else None

    return {
        "status_message": msg,
        "upgrade_ready": not healthy,
        "suggestions": suggestions,
        # Provide an open_path so the watcher can light a button for review
        "open_path": open_path,
        # Minimal summary for the row's compact ok: line
        "summary": {"upgrade_ready": not healthy},
    }


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Systems Integrator — non-agent audit and upgrade suggestions")
    ap.add_argument("--interval", type=float, default=10.0, help="Heartbeat interval seconds (default 10)")
    ap.add_argument("--max-iters", type=int, default=0, help="Optional: stop after N iterations (0 = run forever)")
    args = ap.parse_args(argv)

    i = 0
    ev = evaluate()
    _write_hb("probe", status=("warn" if ev.get("upgrade_ready") else "monitoring"), extra=ev)
    try:
        while True:
            i += 1
            ev = evaluate()
            _write_hb("probe", status=("warn" if ev.get("upgrade_ready") else "monitoring"), extra=ev)
            time.sleep(max(0.5, float(args.interval)))
            if args.max_iters and i >= int(args.max_iters):
                break
    except KeyboardInterrupt:
        pass

    time.sleep(0.25)
    _write_hb("done", status="done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
