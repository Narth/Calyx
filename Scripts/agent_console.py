r"""Agent1 Console — interact with the local Calyx Agent from Windows PowerShell.

This tool lets you send conversational goals to Agent1 (tools/agent_runner.py)
running under WSL. Each goal triggers a new agent run and writes artifacts under
outgoing/agent_run_<timestamp>/.

Usage (one-shot):
    python -u .\Scripts\agent_console.py --goal "Add a Try it section to README with the listener command"

Interactive mode:
    python -u .\Scripts\agent_console.py
  Agent1> <type a goal, Enter to run>
  Agent1> :help   # for console commands
  Agent1> :exit

Options:
  --apply           Apply proposed changes to allowed files (default: off)
  --run-tests       Run compile/tests after each run (default: on)
  --steps N         Max plan steps (default: 3)

Notes:
- Calls into WSL using the venv at ~/.calyx-venv as in tools/triage_orchestrator.py
- Uses --goal-file to avoid Windows shell quoting issues
- Agent heartbeats appear in outgoing/agent1.lock (visible via Scripts/agent_watcher.py)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
try:
    # Keep Shared Voice active for agentic comms
    from tools.svf_util import ensure_svf_running  # type: ignore
except Exception:
    def ensure_svf_running(*args, **kwargs):  # type: ignore
        return False
try:
    # Optional: ensure SVF comms are active for shared outputs
    from tools.svf_util import ensure_svf_running  # type: ignore
except Exception:
    def ensure_svf_running(*args, **kwargs):  # type: ignore
        return False

# CAS (Calyx Autonomy Score) integration
try:
    from tools.cas import CASCalculator, CASTaskEvent, CASTaskMetrics
    CAS_ENABLED = True
except Exception:
    CAS_ENABLED = False
    def CASCalculator(*args, **kwargs): pass
    def CASTaskEvent(*args, **kwargs): pass
    def CASTaskMetrics(*args, **kwargs): pass

# Simple console animations (friendly emoticons)
ANIM_FRAMES = [
    "ᗧ···ᗣ",  # pacman-ish
    "ᗧ· ·ᗣ",
    "ᗧ···ᗣ",
    "ᗧ· ·ᗣ",
]

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
CBO_DIR = OUT / "bridge"
CBO_GOALS_DIR = CBO_DIR / "user_goals"
CBO_DIALOG = CBO_DIR / "dialog.log"
CBO_DISPATCH_DIR = CBO_DIR / "dispatch"
_CBO_DIALOG_TAIL_LINES = 25


def _write_goal_file(text: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    path = OUT / f"goal_{ts}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def _cbo_goal_filename() -> str:
    return f"goal_{int(time.time() * 1000)}.txt"


def _write_cbo_goal(text: str) -> Path:
    msg = text.strip()
    if not msg:
        raise ValueError("Empty CBO goal text")
    CBO_GOALS_DIR.mkdir(parents=True, exist_ok=True)
    path = CBO_GOALS_DIR / _cbo_goal_filename()
    path.write_text(msg + "\n", encoding="utf-8")
    # Mirror Watcher convention for dialog lines
    try:
        CBO_DIALOG.parent.mkdir(parents=True, exist_ok=True)
        with CBO_DIALOG.open("a", encoding="utf-8") as fh:
            fh.write(f"USER> {msg}\n")
    except Exception:
        pass
    return path


def _tail_cbo_dialog(lines: int = _CBO_DIALOG_TAIL_LINES) -> str:
    try:
        data = CBO_DIALOG.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "(no dialog yet)"
    rows = data.splitlines()
    if not rows:
        return "(no dialog yet)"
    return "\n".join(rows[-max(1, lines):])


def _write_cbo_dispatch(goal_file: Path, targets: List[str], domain: str) -> Path:
    rel_goal = goal_file.relative_to(ROOT).as_posix()
    payload: Dict[str, Any] = {
        "id": f"agent_console_{int(time.time() * 1000)}_{uuid.uuid4().hex[:5]}",
        "targets": targets,
        "domain": domain,
        "action": "run",
        "goal_file": rel_goal,
    }
    CBO_DISPATCH_DIR.mkdir(parents=True, exist_ok=True)
    name = f"dispatch_{int(time.time() * 1000)}_{uuid.uuid4().hex[:5]}.json"
    path = CBO_DISPATCH_DIR / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _post_cmd(cmd: str, args: Dict[str, Any]) -> None:
    """Best-effort bridge to the Watcher control channel.

    If the watcher isn't running or the token is missing, this silently does nothing.
    """
    try:
        from tools.agent_control import post_command as _pc  # lazy import
        _pc(cmd, args, sender="agent1")
    except Exception:
        pass


def _write_hb(phase: str, status: str = "running", extra: Optional[Dict[str, Any]] = None, goal_preview: Optional[str] = None) -> None:
    """Write a watcher-compatible heartbeat to outgoing/agent1.lock.

    Mirrors the schema used by tools/agent_runner.py so the Tk watcher can display
    phase/status. We keep this lightweight and best-effort.
    """
    try:
        payload: Dict[str, Any] = {
            "name": "agent1",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": time.time(),
        }
        if goal_preview:
            payload["goal_preview"] = goal_preview
        if extra:
            payload.update(extra)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "agent1.lock").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _emit_cas_event(goal: str, preview: str, success: bool, run_dir: Optional[Path]) -> Optional[CASTaskEvent]:
    """Emit CAS event for completed task"""
    try:
        if not CAS_ENABLED or not run_dir:
            return None

        cas_calc = CASCalculator()

        # Extract metrics from run artifacts
        metrics = _extract_task_metrics(run_dir, success)

        # Create event data
        event_data = {
            "task_id": f"T-{datetime.now().strftime('%Y-%m-%d')}-{int(time.time())}",
            "agent_id": "agent1",
            "started_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ended_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "difficulty": "normal",  # Could be determined from task complexity
            "metrics": {
                "IFCR": 1 if success else 0,  # Intervention-Free Completion Rate
                "HTI": 0,  # Human-Touch Index (will be calculated centrally)
                "SRR": 1 if success else 0,  # Self-Recovery Rate
                "CTC": 0.0,  # Cost-Time-Compute (will be calculated from actual costs)
                "SFT": 1 if success else 0,  # Safe-Failure Threshold
                "RHR": 1  # Reward-Hacking Resistance (default to 1 for now)
            },
            "cost": {
                "tokens": 0,  # Would be extracted from actual LLM calls
                "usd": 0.0,
                "wall_time_sec": 0  # Would be calculated from actual execution time
            },
            "notes": f"Agent1 task: {preview}" + (" - Success" if success else " - Failed"),
            "audit": {
                "toolspec_sha256": "placeholder",  # Would hash actual tool specifications
                "raw_trace_uri": f"file://{run_dir}/"  # Reference to run artifacts
            }
        }

        # Emit the event
        event = cas_calc.ingest_event(event_data)

        # Save event to task-specific file
        event_file = run_dir / "cas_event.json"
        with open(event_file, 'w') as f:
            json.dump({
                "task_event": event_data,
                "cas_score": event.cas_score,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)

        return event

    except Exception as e:
        print(f"[C:CAS] — Error emitting CAS event: {e}")
        return None


def _extract_task_metrics(run_dir: Path, success: bool) -> Dict[str, float]:
    """Extract task metrics from run artifacts"""
    metrics = {
        "IFCR": 1.0 if success else 0.0,
        "HTI": 0.0,  # Will be calculated centrally
        "SRR": 1.0 if success else 0.0,
        "CTC": 0.0,  # Will be calculated from actual costs
        "SFT": 1.0 if success else 0.0,
        "RHR": 1.0
    }

    try:
        # Try to extract actual metrics from run artifacts
        audit_file = run_dir / "audit.json"
        if audit_file.exists():
            with open(audit_file, 'r') as f:
                audit_data = json.load(f)

            # Extract actual cost information
            if 'tokens_used' in audit_data:
                metrics["cost_tokens"] = audit_data['tokens_used']

            if 'execution_time' in audit_data:
                metrics["cost_time"] = audit_data['execution_time']

    except Exception:
        pass

    return metrics


def _run_agent_wsl(goal_file: Path, max_steps: int, apply: bool, run_tests: bool) -> subprocess.CompletedProcess:
    """Invoke tools/agent_runner.py inside WSL using the configured venv.

    Use argument vector form to avoid Windows shell quoting pitfalls.
    """
    goal_file_wsl = f"outgoing/{goal_file.name}"
    parts = [
        "source ~/.calyx-venv/bin/activate",
        "cd /mnt/c/Calyx_Terminal",
        "python -u tools/agent_runner.py",
        f"--goal-file {goal_file_wsl}",
        f"--max-steps {max_steps}",
        "--skip-patches",
    ]
    if apply:
        parts.append("--apply")
    if run_tests:
        parts.append("--run-tests")
    bash_cmd = " && ".join(parts)
    # Call WSL with explicit args (no shell=True)
    return subprocess.run(["wsl", "bash", "-lc", bash_cmd], text=True, capture_output=True)


def _print_tail(tag: str, text: str, limit: int = 4000) -> None:
    if not text:
        return
    tail = text[-limit:]
    if tail.strip():
        print(f"[{tag}]\n{tail}\n", flush=True)


def _summarize_last_run_dir() -> Optional[Path]:
    runs = [p for p in OUT.glob("agent_run_*") if p.is_dir()]
    if not runs:
        return None
    return sorted(runs, key=lambda p: p.name)[-1]


def _print_run_summary() -> None:
    rd = _summarize_last_run_dir()
    if not rd:
        return
    audit = rd / "audit.json"
    plan = rd / "plan.json"
    print(f"Artifacts: {rd.relative_to(ROOT)}")
    if plan.exists():
        try:
            data = plan.read_text(encoding="utf-8")
            # print only step descriptions to keep it short
            import json as _json
            obj = _json.loads(data)
            steps = obj.get("steps", [])
            if steps:
                print("Plan:")
                for i, s in enumerate(steps, 1):
                    desc = s.get("description") or "(no description)"
                    files = s.get("files") or []
                    files_s = ", ".join(files) if files else "n/a"
                    print(f"  {i}. {desc} -> {files_s}")
        except Exception:
            pass
    if audit.exists():
        try:
            import json as _json
            a = _json.loads(audit.read_text(encoding="utf-8"))
            changed = a.get("changed_files", [])
            applied = bool(a.get("applied"))
            print(f"Applied: {applied} | Changed files: {', '.join(changed) if changed else 'none'}")
        except Exception:
            pass


def one_shot(goal: str, steps: int, apply: bool, run_tests: bool, anim: bool = True) -> int:
    goal_file = _write_goal_file(goal)
    preview = (" ".join(goal.split()))[:140]
    print(f"[Agent1] Running goal via {goal_file.name} (steps={steps}, apply={apply}, tests={run_tests})")
    _write_hb("launch", status="running", goal_preview=preview)
    # Notify watcher (if unlocked)
    _post_cmd("set_banner", {"text": f"Running: {preview}", "color": "#1f6feb"})
    _post_cmd("append_log", {"text": f"Goal: {preview}"})

    # Launch process and optionally animate while waiting
    goal_file_wsl = goal_file  # for clarity
    parts = [
        "source ~/.calyx-venv/bin/activate",
        "cd /mnt/c/Calyx_Terminal",
        "python -u tools/agent_runner.py",
        f"--goal-file outgoing/{goal_file_wsl.name}",
        f"--max-steps {steps}",
        "--skip-patches",
    ]
    if apply:
        parts.append("--apply")
    if run_tests:
        parts.append("--run-tests")
    bash_cmd = " && ".join(parts)
    # Optionally launch a tiny indicator window (auto-close when finished)
    try:
        if getattr(one_shot, "_indicator_enabled", True):
            subprocess.Popen([sys.executable, "-u", "Scripts\\agent_indicator.py", "--auto-close", "--top"], cwd=str(ROOT))
    except Exception:
        pass

    proc = subprocess.Popen(["wsl", "bash", "-lc", bash_cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if anim:
        print(" ", end="", flush=True)
        i = 0
        while proc.poll() is None:
            print(f"\rWorking... ({i % 10})", end="", flush=True)
            time.sleep(0.12)
            i += 1
        print("\r", end="")

    stdout, stderr = proc.communicate()
    ok = proc.returncode == 0
    _print_tail("stdout", stdout)
    _print_tail("stderr", stderr)
    _print_run_summary()

    # CAS Event Emission (if enabled)
    if CAS_ENABLED:
        try:
            cas_calc = CASCalculator()
            task_event = _emit_cas_event(goal, preview, ok, rd)
            if task_event:
                print(f"[C:CAS] — Station Calyx: Task scored - CAS: {task_event.cas_score:.3f}")

                # Show agent status card if available
                agent_status = cas_calc.generate_agent_status_card("agent1")
                if agent_status and "No tasks completed yet" not in agent_status:
                    print(f"[C:AUTONOMY_PULSE] — Station Calyx:")
                    print(agent_status)
        except Exception as e:
            print(f"[C:CAS] — Warning: CAS system error: {e}")

    # Update heartbeat with latest run info
    rd = _summarize_last_run_dir()
    extra: Dict[str, Any] = {}
    if rd:
        try:
            extra["run_dir"] = str(rd.relative_to(ROOT))
        except Exception:
            extra["run_dir"] = str(rd)
    status = "done" if ok else "error"
    if not ok and stderr:
        extra["error_tail"] = stderr.strip()[-300:]
    _write_hb("done", status=status, extra=extra, goal_preview=preview)
    # Notify watcher final state
    if ok:
        _post_cmd("set_banner", {"text": f"Done: {preview}", "color": "#3fb950"})
        _post_cmd("append_log", {"text": "Run completed successfully."})
    else:
        _post_cmd("set_banner", {"text": f"Error: {preview}", "color": "#d1242f"})
        _post_cmd("append_log", {"text": "Run failed. See artifacts for details."})
        _post_cmd("show_toast", {"text": "Agent1 encountered an error. Check the latest run artifacts."})
    return 0 if ok else 1


def repl(steps: int, apply: bool, run_tests: bool, *, cbo_domain: str, cbo_dispatch_targets: Optional[List[str]]) -> int:
    print("Agent1 Console - type ':help' for commands; ':exit' to quit.")
    cur_steps = steps
    cur_apply = apply
    cur_tests = run_tests
    cur_anim = True
    # Indicator toggle stored on the function for reuse in one_shot launch path
    one_shot._indicator_enabled = True  # type: ignore[attr-defined]
    while True:
        try:
            line = input("Agent1> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.startswith(":"):
            raw = line[1:].strip()
            cmd = raw.lower()
            if cmd in ("exit", "quit", "q"):
                break
            if cmd == "help":
                print(":steps N     - set max steps (current:", cur_steps, ")")
                print(":apply on|off - toggle apply (current:", "on" if cur_apply else "off", ")")
                print(":tests on|off - toggle run-tests (current:", "on" if cur_tests else "off", ")")
                print(":open         - open last run directory in Explorer")
                print(":watch        - launch the watcher GUI in a separate window")
                print(":anim on|off  - toggle console animations (current:", "on" if cur_anim else "off", ")")
                print(":indicator on|off - toggle pop-up indicator window (current:", "on" if getattr(one_shot, "_indicator_enabled", True) else "off", ")")
                print(":cbo TEXT     - send TEXT to the CBO queue")
                print(":cbod TEXT    - send TEXT and emit CP12 dispatch (targets:", cbo_dispatch_targets or ["agent2"], ")")
                print(":cbo-log      - show recent CBO dialog lines")
                continue
            if cmd.startswith("steps"):
                parts = cmd.split()
                if len(parts) == 2 and parts[1].isdigit():
                    cur_steps = max(1, int(parts[1]))
                    print(f"[cfg] steps={cur_steps}")
                else:
                    print("Usage: :steps N")
                continue
            if cmd.startswith("apply"):
                parts = cmd.split()
                if len(parts) == 2 and parts[1] in ("on", "off"):
                    cur_apply = parts[1] == "on"
                    print(f"[cfg] apply={'on' if cur_apply else 'off'}")
                else:
                    print("Usage: :apply on|off")
                continue
            if cmd.startswith("tests"):
                parts = cmd.split()
                if len(parts) == 2 and parts[1] in ("on", "off"):
                    cur_tests = parts[1] == "on"
                    print(f"[cfg] tests={'on' if cur_tests else 'off'}")
                else:
                    print("Usage: :tests on|off")
                continue
            if cmd == "open":
                rd = _summarize_last_run_dir()
                if rd and os.name == "nt":
                    os.startfile(str(rd))  # type: ignore[attr-defined]
                else:
                    print("No run dir yet.")
                continue
            if cmd.startswith("anim"):
                parts = cmd.split()
                if len(parts) == 2 and parts[1] in ("on", "off"):
                    cur_anim = parts[1] == "on"
                    print(f"[cfg] anim={'on' if cur_anim else 'off'}")
                else:
                    print("Usage: :anim on|off")
                continue
            if cmd.startswith("indicator"):
                parts = cmd.split()
                if len(parts) == 2 and parts[1] in ("on", "off"):
                    one_shot._indicator_enabled = parts[1] == "on"  # type: ignore[attr-defined]
                    print(f"[cfg] indicator={'on' if getattr(one_shot, '_indicator_enabled', True) else 'off'}")
                else:
                    print("Usage: :indicator on|off")
                continue
            if cmd == "watch":
                try:
                    subprocess.Popen([sys.executable, "-u", "Scripts\\agent_watcher.py", "--quiet"], cwd=str(ROOT))
                    print("[Agent1] Watcher launched.")
                except Exception as e:
                    print(f"[Agent1] Failed to launch watcher: {e}")
                continue
            if cmd == "cbo-log":
                print(_tail_cbo_dialog())
                continue
            if cmd.startswith("cbod"):
                parts = raw.split(" ", 1)
                payload = parts[1].strip() if len(parts) == 2 else ""
                if not payload:
                    print("[CBO] Usage: :cbod your goal text")
                    continue
                goal_path = _write_cbo_goal(payload)
                targets = cbo_dispatch_targets or ["agent2"]
                dispatch_path = _write_cbo_dispatch(goal_path, targets, cbo_domain)
                print(f"[CBO] queued goal: {goal_path.relative_to(ROOT)} (dispatch: {dispatch_path.relative_to(ROOT)})")
                continue
            if cmd.startswith("cbo"):
                parts = raw.split(" ", 1)
                payload = parts[1].strip() if len(parts) == 2 else ""
                if not payload:
                    print("[CBO] Usage: :cbo your goal text")
                    continue
                goal_path = _write_cbo_goal(payload)
                print(f"[CBO] queued goal file: {goal_path.relative_to(ROOT)}")
                continue
            print("Unknown console command. Type :help")
            continue
        # Run a goal
        rc = one_shot(line, steps=cur_steps, apply=cur_apply, run_tests=cur_tests, anim=cur_anim)
        if rc != 0:
            print("[Agent1] Run failed (non-zero exit). See artifacts above.")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Interactive console for Agent1 (WSL)")
    ap.add_argument("--goal", help="One-shot goal to run (omit for interactive mode)")
    ap.add_argument("--cbo-goal", help="Send a goal to the CBO queue (skips Agent1 run)")
    ap.add_argument("--cbo-dispatch-target", action="append", dest="cbo_dispatch_targets", help="Add a CP12 dispatch target (default: agent2). Repeat for multiple targets.")
    ap.add_argument("--cbo-domain", choices=["any", "wsl", "win"], default="any", help="Domain hint for CP12 dispatches (default: any)")
    ap.add_argument("--no-cbo-dispatch", action="store_true", help="Skip CP12 dispatch files when sending CBO goals")
    ap.add_argument("--apply", action="store_true", help="Apply proposed changes (default: off)")
    ap.add_argument("--no-tests", dest="run_tests", action="store_false", help="Disable compile/tests (default: on)")
    ap.add_argument("--steps", type=int, default=3, help="Maximum plan steps (default: 3)")
    args = ap.parse_args(argv)
    # Keep Shared Voice active so console-triggered runs can produce SVF-compliant outputs
    try:
        ensure_svf_running(grace_sec=15.0, interval=5.0)
    except Exception:
        pass

    # Ensure SVF is active before running any one-shot/interactive sessions
    try:
        ensure_svf_running(grace_sec=15.0, interval=5.0)
    except Exception:
        pass

    cbo_targets: Optional[List[str]] = None
    if not args.no_cbo_dispatch:
        if args.cbo_dispatch_targets:
            cbo_targets = args.cbo_dispatch_targets
        elif args.cbo_goal:
            cbo_targets = ["agent2"]

    if args.cbo_goal:
        goal_path = _write_cbo_goal(args.cbo_goal)
        print(f"[CBO] queued goal file: {goal_path.relative_to(ROOT)}")
        if cbo_targets:
            dispatch_path = _write_cbo_dispatch(goal_path, cbo_targets, args.cbo_domain)
            print(f"[CBO] dispatch file: {dispatch_path.relative_to(ROOT)}")
        print(_tail_cbo_dialog())
        return 0

    if args.goal:
        return one_shot(args.goal, steps=max(1, args.steps), apply=bool(args.apply), run_tests=bool(args.run_tests))
    return repl(steps=max(1, args.steps), apply=bool(args.apply), run_tests=bool(args.run_tests), cbo_domain=args.cbo_domain, cbo_dispatch_targets=cbo_targets)


if __name__ == "__main__":
    raise SystemExit(main())
