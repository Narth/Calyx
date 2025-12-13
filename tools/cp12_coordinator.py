"""CP12 — Systems Coordinator

Receives instructions from the Calyx Bridge Overseer (CBO) and delivers them
to multiple agents across bridges/domains in Station Calyx.

Contract (v0.1):
- Instruction mailbox: outgoing/bridge/dispatch/*.json
  Each file is a JSON object with optional fields:
    {
      "id": "optional-id",
      "targets": ["agent2", "agent3", "triage", "navigator", ...],
      "domain": "wsl" | "win" | "any",
      "action": "run" | "start" | "stop",
      "run": "task_label_or_hint",
      "args": "string of extra args",
      "goal": "free-text goal for agent_runner (optional)",
      "goal_file": "path to text file goal (optional)"
    }

- Processing folders:
  - incoming:  outgoing/bridge/dispatch/
  - processing: outgoing/bridge/dispatch/processing/
  - completed:  outgoing/bridge/dispatch/completed/

- Heartbeat: outgoing/cp12.lock (name=cp12, role=Systems Coordinator)
- Audit:     appends short lines to outgoing/bridge/dialog.log as CP12>

Notes:
- First implementation focuses on a safe, minimal subset:
  - For agent targets (agent2/3/4), run tools/agent_runner.py in tests-mode
    with llm-optional and no apply. Uses Windows Python by default; if
    domain=="wsl", dispatch via WSL bash with venv activation.
  - For triage/navigator/manifest/sysint, supports one-shot or short loops
    using --max-iters when action is "start" with optional args.
- If a dispatch file is malformed, it is moved to completed/ with error=true.

This script is purposely defensive and config-first; future versions can add
gates, richer plan following, and direct integration with Watcher tokens.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
DISPATCH_IN = OUT / "bridge" / "dispatch"
DISPATCH_PROC = DISPATCH_IN / "processing"
DISPATCH_DONE = DISPATCH_IN / "completed"
BRIDGE_DIALOG = OUT / "bridge" / "dialog.log"
HB = OUT / "cp12.lock"
VERSION = "0.1.0"
GATES_DIR = OUT / "gates"
GATE_LLM = GATES_DIR / "llm.ok"

try:
    # Keep Shared Voice communications active so dispatches are visible system-wide
    from tools.svf_util import ensure_svf_running  # type: ignore
except Exception:  # pragma: no cover - optional import
    def ensure_svf_running(*args, **kwargs):  # type: ignore
        return False


def _write_hb(phase: str, status: str = "running", extra: Optional[Dict[str, Any]] = None) -> None:
    try:
        payload: Dict[str, Any] = {
            "name": "cp12",
            "role": "Systems Coordinator",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": time.time(),
            "version": VERSION,
        }
        if extra:
            payload.update(extra)
        HB.parent.mkdir(parents=True, exist_ok=True)
        HB.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _append_dialog(line: str) -> None:
    try:
        BRIDGE_DIALOG.parent.mkdir(parents=True, exist_ok=True)
        with BRIDGE_DIALOG.open("a", encoding="utf-8") as fh:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            fh.write(f"{ts} CP12> {line}\n")
    except Exception:
        pass


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _move(src: Path, dst: Path) -> None:
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    except Exception:
        try:
            # Best-effort fallback: copy then unlink
            data = src.read_bytes()
            dst.write_bytes(data)
            src.unlink(missing_ok=True)
        except Exception:
            pass


def _ensure_dirs() -> None:
    for p in (DISPATCH_IN, DISPATCH_PROC, DISPATCH_DONE):
        p.mkdir(parents=True, exist_ok=True)


def _run_win(cmd: List[str], *, cwd: Optional[Path] = None, timeout: Optional[int] = None) -> Tuple[int, str]:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout)
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out
    except Exception as e:
        return 1, f"exception: {e}"


def _run_wsl(command: str, *, timeout: Optional[int] = None) -> Tuple[int, str]:
    # Activate ~/.calyx-venv if present, cd into repo, then run
    wrapped = f"source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && {command}"
    return _run_win(["wsl", "bash", "-lc", wrapped], timeout=timeout)


def _prefer_wsl() -> bool:
    """Best-effort check whether WSL is available and primed for Calyx.

    Signals: presence of outgoing/_wsl_touch.txt or a usable ~/.calyx-venv.
    """
    try:
        if (OUT / "_wsl_touch.txt").exists():
            return True
    except Exception:
        pass
    try:
        rc, _ = _run_win(["wsl", "bash", "-lc", "test -d ~/.calyx-venv && echo ok || echo no"], timeout=4)
        return rc == 0
    except Exception:
        return False


def _dispatch_agent(target: str, goal: Optional[str], goal_file: Optional[str], args: str, domain: str, dry_run: bool) -> Dict[str, Any]:
    agent_id = 1
    try:
        # Extract numeric id from target like "agent2"
        if target.lower().startswith("agent"):
            agent_id = int(target.lower().replace("agent", "").strip() or "1")
    except Exception:
        agent_id = 1

    # Respect LLM gate: drop --llm-optional when gate present
    llm_allowed = GATE_LLM.exists()
    extras = ["--skip-patches", "--run-tests"]
    if not llm_allowed:
        extras.append("--llm-optional")
    # Serialize LLM usage across agents for efficiency
    extras += ["--llm-token", "llm", "--llm-wait-sec", "60"]
    extras += ["--agent-id", str(agent_id)]
    # Normalize args: allow str or dict → CLI flags
    if args:
        if isinstance(args, str):
            extras += args.split()
        elif isinstance(args, dict):
            for k, v in args.items():
                key = f"--{str(k).replace('_','-')}"
                if isinstance(v, bool):
                    if v:
                        extras.append(key)
                elif v is None:
                    continue
                else:
                    extras += [key, str(v)]

    cmd_py = [sys.executable, "tools/agent_runner.py"]
    if goal_file:
        cmd_py += ["--goal-file", goal_file]
    elif goal:
        cmd_py += ["--goal", goal]
    else:
        cmd_py += ["--goal", "Coordination: small safe improvement"]
    cmd_py += extras

    result: Dict[str, Any] = {"target": target, "agent_id": agent_id, "domain": domain, "dry_run": dry_run}

    if dry_run:
        result.update({"rc": 0, "stdout": "(dry-run) would run: " + " ".join(cmd_py)})
        return result

    # Prefer WSL when domain is any and WSL is primed
    if domain == "any" and _prefer_wsl():
        domain = "wsl"
    if domain == "wsl":
        rc, out = _run_wsl("python tools/agent_runner.py " + " ".join(map(_shlex, cmd_py[2:])))
    else:
        rc, out = _run_win(cmd_py, cwd=ROOT)
    result.update({"rc": rc, "stdout": out})
    return result


def _dispatch_service(name: str, action: str, args: str, domain: str, dry_run: bool) -> Dict[str, Any]:
    # Map service name to python entry and default args
    service_map = {
        "triage": ("tools/triage_probe.py", "--interval 2 --probe-every 15"),
        "navigator": ("tools/traffic_navigator.py", "--interval 3"),
        "manifest": ("tools/manifest_probe.py", "--interval 5"),
        "sysint": ("tools/sys_integrator.py", "--interval 10"),
        "tes": ("tools/tes_monitor.py", "--interval 10 --tail 5"),
    }
    entry = service_map.get(name.lower())
    if not entry:
        return {"service": name, "rc": 2, "stdout": f"unknown service: {name}"}

    script, default = entry
    # Normalize args for services: allow str or dict
    if isinstance(args, dict):
        parts = []
        for k, v in args.items():
            key = f"--{str(k).replace('_','-')}"
            if isinstance(v, bool):
                if v:
                    parts.append(key)
            elif v is None:
                continue
            else:
                parts += [key, str(v)]
        arg_str = (" ".join(parts) or default).strip()
    else:
        arg_str = (args or default).strip()
    py_cmd = f"python -u {script} {arg_str}"

    result: Dict[str, Any] = {"service": name, "action": action, "domain": domain, "dry_run": dry_run}
    if dry_run:
        result.update({"rc": 0, "stdout": f"(dry-run) would {action}: {py_cmd}"})
        return result

    if domain == "wsl":
        rc, out = _run_wsl(py_cmd)
    else:
        # For long-running services, a real supervisor would background them; here we run once or short loops.
        rc, out = _run_win([sys.executable, "-u", script] + arg_str.split(), cwd=ROOT)
    result.update({"rc": rc, "stdout": out})
    return result


def _shlex(arg: str) -> str:
    # Minimal shell escaping for WSL wrapper: wrap if spaces
    if not arg:
        return arg
    if any(ch.isspace() for ch in arg):
        return f'"{arg}"'
    return arg


def process_one(path: Path, *, dry_run: bool = False) -> Dict[str, Any]:
    data = _read_json(path) or {}
    targets: List[str] = data.get("targets") or []
    action: str = (data.get("action") or "run").lower()
    domain: str = (data.get("domain") or "any").lower()
    args_common = data.get("args") or ""
    args_agent = data.get("args_agent", args_common)
    args_service = data.get("args_service", args_common)
    goal: Optional[str] = data.get("goal")
    goal_file: Optional[str] = data.get("goal_file")

    results: List[Dict[str, Any]] = []

    if not targets:
        return {"error": "no targets", "path": str(path)}

    for t in targets:
        t_l = t.lower()
        if t_l.startswith("agent"):
            results.append(_dispatch_agent(t_l, goal, goal_file, args_agent, "wsl" if domain == "wsl" else "win", dry_run))
        else:
            # Allow generic 'service' target to specify a concrete name via 'service' field
            svc_name = data.get("service") if t_l in ("service", "svc") else t_l
            results.append(_dispatch_service(str(svc_name or ""), action, args_service, "wsl" if domain == "wsl" else "win", dry_run))

    return {"path": str(path), "results": results}


def loop(interval: float, max_iters: int, dry_run: bool) -> int:
    _ensure_dirs()
    i = 0
    _append_dialog("CP12 online; watching bridge/dispatch for instructions…")
    _write_hb("watch", status="observing", extra={"status_message": "watching dispatch", "queue": 0})
    # Ensure SVF probe is running so shared-voice messages remain visible
    try:
        ensure_svf_running(grace_sec=10.0, interval=5.0)
    except Exception:
        pass
    try:
        while True:
            i += 1
            # Oldest first to preserve intent ordering
            files = sorted(DISPATCH_IN.glob("*.json"), key=lambda p: p.stat().st_mtime)
            for p in files:
                try:
                    proc_path = DISPATCH_PROC / p.name
                    _move(p, proc_path)
                    res = process_one(proc_path, dry_run=dry_run)
                    status_txt = "; ".join(
                        [
                            (f"{r.get('target') or r.get('service')}: rc={r.get('rc')}"
                             + (" (dry)" if dry_run else ""))
                            for r in res.get("results", [])
                        ]
                    )
                    _append_dialog(f"Dispatched {proc_path.name}: {status_txt}")
                    done_path = DISPATCH_DONE / proc_path.name
                    # Attach result JSON sidecar for audit
                    done_path_json = done_path.with_suffix(".result.json")
                    done_path_json.parent.mkdir(parents=True, exist_ok=True)
                    done_path_json.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
                    _move(proc_path, done_path)
                except Exception as e:
                    _append_dialog(f"Error processing {p.name}: {e}")
            _write_hb("watch", status="observing", extra={"status_message": "watching dispatch", "queue": len(files)})
            time.sleep(max(0.25, float(interval)))
            if max_iters and i >= int(max_iters):
                break
    except KeyboardInterrupt:
        pass
    time.sleep(0.25)
    _write_hb("done", status="done")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="CP12 Systems Coordinator — dispatch CBO instructions to agents/services")
    ap.add_argument("--interval", type=float, default=1.0, help="Poll interval seconds (default 1.0)")
    ap.add_argument("--max-iters", type=int, default=0, help="Stop after N iterations (0 = run forever)")
    ap.add_argument("--dry-run", action="store_true", help="Do not execute commands; log intended actions")
    args = ap.parse_args(argv)
    return loop(interval=args.interval, max_iters=args.max_iters, dry_run=bool(args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
