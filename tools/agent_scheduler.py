#!/usr/bin/env python3
"""
Agent1 lightweight scheduler: triggers a tiny Agent1 task every N seconds (default: 180 seconds).
- Skips if Agent1 appears to be running (based on outgoing/agent1.lock phase/status)
- Goal is designed to be light and fast to encourage frequent, consistent progress
- Can be run inside WSL or from Windows; when on Windows, it will call into WSL

Usage examples:
  # Run loop (3 minutes) in WSL
  python tools/agent_scheduler.py --interval 180

  # One-shot dry-run to verify without invoking the agent
  python tools/agent_scheduler.py --run-once --dry-run

Notes:
- By default, passes --skip-patches to avoid making changes automatically; adjust with --agent-args
- Writes a small log at logs/agent_scheduler.log for visibility
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

import yaml

try:
    from calyx_core.intercept import (
        ActionType,
        InterceptContext,
        ResourceSnapshot,
        StationInterceptor,
    )
except Exception:  # pragma: no cover
    ActionType = None  # type: ignore
    InterceptContext = None  # type: ignore
    ResourceSnapshot = None  # type: ignore
    StationInterceptor = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
# These paths are parameterized by --agent-id at runtime in main()
LOCK_PATH = ROOT / "outgoing" / "agent1.lock"
LOG_PATH = ROOT / "logs" / "agent_scheduler.log"
STATE_PATH = ROOT / "logs" / "agent_scheduler_state.json"
SCH_LOCK = ROOT / "outgoing" / "scheduler.lock"
AUTONOMY_LOG = ROOT / "logs" / "autonomy_decisions.jsonl"
LOAD_MODE_FILE = ROOT / "state" / "load_mode.json"

CRITICAL_LOCKS = {
    "autonomy_monitor.lock",
    "autonomy_runner.lock",
    "cbo.lock",
    "cp19.lock",
    "cp20.lock",
    "llm_ready.lock",
    "navigator.lock",
    "scheduler.lock",
    "svf.lock",
    "sysint.lock",
    "triage.lock",
}
LOCK_CLEANUP_INTERVAL_S = 1800  # Run stale-lock cleanup at most every 30 minutes

GOAL_SUFFIX = (
    "Complete within 8 minutes and <=3 lines changed. Report the change and hint at the "
    "next atomic step. Do NOT apply patches. Keep it fast."
)

DEFAULT_GOAL = (
    "Tiny improvement mode: Find ONE line or atomic change that improves clarity, "
    "fixes minor inconsistency, or adds helpful comment. "
    + GOAL_SUFFIX
)

# Optimized goal templates for different scenarios
GOAL_TEMPLATES = {
    "stability": (
        "Focus on stability: Identify and fix ONE error-prone pattern or missing error handling. "
        "Target: Error rate reduction. "
        + GOAL_SUFFIX
    ),
    "velocity": (
        "Focus on velocity: Identify ONE optimization that speeds up execution. "
        "Target: Performance improvement. "
        + GOAL_SUFFIX
    ),
    "footprint": (
        "Focus on footprint: Identify ONE unnecessary file access or redundant operation. "
        "Target: Reduce unnecessary operations. "
        + GOAL_SUFFIX
    ),
    "default": DEFAULT_GOAL
}

INTERCEPT_PHASE_TAG = os.environ.get("CALYX_PHASE_TAG", "phaseA")
INTERCEPT_SURFACE = "scheduler_launch"
_INTERCEPTOR = StationInterceptor() if StationInterceptor else None
_AGII_CACHE: dict[str, float | None] = {"mtime": 0.0, "value": None}
_AGENT_ROLE_CACHE: dict[str, str] = {}
_AGENT_ROLE_MTIME = 0.0


def _latest_agii_score() -> Optional[float]:
    """Return cached AGII score from reports/agii_report_latest.md."""
    global _AGII_CACHE
    path = ROOT / "reports" / "agii_report_latest.md"
    if not path.exists():
        return None
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return _AGII_CACHE.get("value")  # type: ignore[arg-type]
    if mtime != _AGII_CACHE.get("mtime"):
        value: Optional[float] = None
        try:
            text = path.read_text(encoding="utf-8")
            match = re.search(r"\*\*Overall AGII:\*\*\s*([0-9.]+)", text)
            if match:
                value = float(match.group(1))
        except Exception:
            value = None
        _AGII_CACHE["mtime"] = mtime
        _AGII_CACHE["value"] = value
    return _AGII_CACHE.get("value")  # type: ignore[return-value]


def _agent_role(agent_name: str) -> str:
    """Lookup agent role from outgoing/agents/registry.json (cached)."""
    global _AGENT_ROLE_CACHE, _AGENT_ROLE_MTIME
    registry_path = ROOT / "outgoing" / "agents" / "registry.json"
    try:
        mtime = registry_path.stat().st_mtime
    except FileNotFoundError:
        return ""
    if mtime != _AGENT_ROLE_MTIME:
        try:
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            agents = data.get("agents", {})
            if isinstance(agents, dict):
                _AGENT_ROLE_CACHE = {
                    name: str(info.get("role") or "")
                    for name, info in agents.items()
                    if isinstance(info, dict)
                }
            else:
                _AGENT_ROLE_CACHE = {}
        except Exception:
            _AGENT_ROLE_CACHE = {}
        _AGENT_ROLE_MTIME = mtime
    return _AGENT_ROLE_CACHE.get(agent_name, "")


def _intercept_guard(
    *,
    goal: str,
    mode: str,
    hb_name: str,
    interval_s: float,
    tes_snapshot: Optional[float],
    cpu_pct: float,
    mem_pct: float,
    warn_streak: int,
    intercept_mode: str,
) -> Tuple[bool, Optional[str]]:
    """Send the launch request through StationInterceptor."""
    if not _INTERCEPTOR or not InterceptContext or intercept_mode == "off":
        return True, None

    payload_meta = {
        "phase": INTERCEPT_PHASE_TAG,
        "surface": INTERCEPT_SURFACE,
        "agent_role": _agent_role(hb_name) or ("builder" if hb_name.startswith("agent") else hb_name),
        "autonomy_tier": mode,
        "goal_excerpt": goal[:180],
        "scheduler_interval_s": interval_s,
        "warn_streak": warn_streak,
        "correlation_id": f"{hb_name}-tick-{int(time.time() * 1000)}",
    }
    ctx = InterceptContext(
        agent_name=hb_name,
        action_type=ActionType.SCHEDULER_LAUNCH if ActionType else None,
        description=f"Scheduler launch request (mode={mode})",
        payload_meta=payload_meta,
        tes=tes_snapshot,
        agii=_latest_agii_score(),
        resources=ResourceSnapshot(cpu_percent=float(cpu_pct), ram_percent=float(mem_pct)),
        dry_run=(intercept_mode == "dry_run"),
    )
    decision = _INTERCEPTOR.check(ctx)
    log_parts = [
        f"allow={decision.allow}",
        f"severity={decision.severity.value}",
    ]
    if decision.cas_directive:
        log_parts.append(f"cas={decision.cas_directive.value}")
    if decision.log_path:
        log_parts.append(f"log={decision.log_path.name}")
    _log("Interceptor (%s) %s" % (intercept_mode, " ".join(log_parts)))
    if decision.adjust_autonomy:
        _log(f"Interceptor suggests autonomy adjustment: {decision.adjust_autonomy}")
    if decision.require_human_review:
        _log("Interceptor flagged for human review.")

    allowed = decision.allow or intercept_mode != "enforce"
    reason = None if decision.allow else "; ".join(decision.reasons)
    return allowed, reason


def _generate_targeted_goal(
    mode: str,
    tes_history: List[float],
    recent_rows: List[dict],
) -> str:
    """Generate focused agent goal based on system state."""
    recent_rows = [r for r in recent_rows if isinstance(r, dict)]
    failure_rows = [
        r for r in recent_rows
        if (r.get("status") or "").lower() not in ("", "done")
    ]
    durations: List[float] = []
    changed_counts: List[int] = []
    for r in recent_rows:
        try:
            durations.append(float(r.get("duration_s") or 0.0))
        except Exception:
            continue
        try:
            changed_counts.append(int(r.get("changed_files") or 0))
        except Exception:
            pass

    tes_decline = False
    if len(tes_history) >= 4:
        recent_avg = sum(tes_history[-3:]) / 3.0
        prev_slice = tes_history[:-3]
        if prev_slice:
            prev_avg = sum(prev_slice[-3:]) / min(3.0, float(len(prev_slice)))
            tes_decline = recent_avg < (prev_avg - 1.5)

    avg_duration = (sum(durations) / len(durations)) if durations else 0.0
    avg_changed = (sum(changed_counts) / len(changed_counts)) if changed_counts else 0.0
    slow_run = max(durations) if durations else 0.0

    focus = "default"
    context_bits: List[str] = []
    if failure_rows:
        focus = "stability"
        last_fail_dir = failure_rows[-1].get("run_dir") or ""
        if last_fail_dir:
            context_bits.append(f"Inspect artifacts in {last_fail_dir} before retrying.")
        context_bits.append(f"{len(failure_rows)} failure(s) in last {len(recent_rows)} runs.")
    elif avg_changed > 3.0 or (mode == "apply_tests" and avg_changed > 2.0):
        focus = "footprint"
        context_bits.append(f"Average touched files {avg_changed:.1f}; keep footprint minimal.")
    elif avg_duration > 210.0 or slow_run > 240.0:
        focus = "velocity"
        context_bits.append(f"Recent runs averaging {avg_duration:.0f}s (max {slow_run:.0f}s); tighten execution time.")
    elif tes_decline:
        focus = "stability"
        context_bits.append("TES trending downward; reinforce stable completions.")
    elif mode == "apply_tests":
        focus = "footprint"

    prompt = GOAL_TEMPLATES.get(focus, GOAL_TEMPLATES["default"])
    if context_bits:
        prompt = f"{prompt} Context: {' '.join(context_bits)}"
    return prompt


def _load_tes_history(limit: int = 12, rows: Optional[List[dict]] = None) -> List[float]:
    """Return recent TES history values (oldest to newest)."""
    if rows is None:
        rows = _read_metrics_csv(ROOT / "logs" / "agent_metrics.csv")
    if not rows:
        return []
    values: List[float] = []
    for row in rows[-limit:]:
        try:
            tes_val = float(row.get("tes", "") or 0.0)
        except Exception:
            continue
        if tes_val <= 0:
            continue
        values.append(tes_val)
    return values


def _cleanup_stale_locks(max_age_hours: int = 6) -> list[str]:
    """Remove stale lock files older than max_age_hours (excluding critical locks)."""
    cutoff = time.time() - (max_age_hours * 3600)
    removed: list[str] = []
    base = ROOT / "outgoing"
    if not base.exists():
        return removed
    for lock in base.rglob("*.lock"):
        try:
            if lock.name in CRITICAL_LOCKS or "gates" in lock.parts:
                continue
            if lock.stat().st_mtime >= cutoff:
                continue
        except FileNotFoundError:
            continue
        try:
            lock.unlink()
            removed.append(str(lock.relative_to(ROOT)))
        except Exception as exc:
            _log(f"Failed to remove stale lock {lock}: {exc}")
    if removed:
        _log(f"Pruned {len(removed)} stale lock(s): {', '.join(removed)}")
    return removed

_CONFIG_CACHE: Optional[dict[str, Any]] = None


def _config_path() -> Path:
    return ROOT / "config.yaml"


def _load_config() -> dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        cfg_path = _config_path()
        try:
            with cfg_path.open("r", encoding="utf-8") as fh:
                _CONFIG_CACHE = yaml.safe_load(fh) or {}
        except Exception:
            _CONFIG_CACHE = {}
    return dict(_CONFIG_CACHE)


def _default_model_id() -> Optional[str]:
    cfg = _load_config()
    try:
        settings = cfg.get("settings", {})
        scheduler_cfg = settings.get("scheduler", {})
        model_id = scheduler_cfg.get("model_id")
        if isinstance(model_id, str) and model_id.strip():
            return model_id.strip()
    except Exception:
        pass
    return None


def _is_wsl() -> bool:
    return "WSL_DISTRO_NAME" in os.environ or "microsoft-standard" in open("/proc/version", "r", errors="ignore").read().lower() if os.name == "posix" and Path("/proc/version").exists() else False


def _read_lock_phase() -> str | None:
    try:
        if LOCK_PATH.exists():
            data = json.loads(LOCK_PATH.read_text(encoding="utf-8", errors="ignore"))
            # defensive access: allow either dict keys or attributes
            phase = data.get("phase") if isinstance(data, dict) else None
            status = data.get("status") if isinstance(data, dict) else None
            # Consider running if phase indicates launch/running
            if phase:
                return f"{phase}:{status}" if status else phase
    except Exception:
        # If lock parsing fails, be conservative and assume not running
        return None
    return None


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def _append_decision(payload: dict) -> None:
    try:
        AUTONOMY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUTONOMY_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _hb(payload: dict) -> None:
    """Best-effort heartbeat for the watcher under outgoing/scheduler.lock"""
    try:
        d = dict(payload)
        d["ts"] = time.time()
        SCH_LOCK.parent.mkdir(parents=True, exist_ok=True)
        SCH_LOCK.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# -------------------- Autonomy mode & promotion helpers --------------------

AUTONOMY_SEQUENCE = ["safe", "tests", "apply_tests"]

# ------------------------- Hardening configuration -------------------------

def _json_read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def _cbo_policy() -> dict:
    return _json_read(ROOT / "outgoing" / "policies" / "cbo_permissions.json")


def _cbo_lock() -> dict:
    return _json_read(ROOT / "outgoing" / "cbo.lock")


def _llm_ready() -> dict:
    return _json_read(ROOT / "outgoing" / "llm_ready.lock")


def _gpu_gate_on() -> bool:
    return (ROOT / "outgoing" / "gates" / "gpu.ok").exists()


def _gpu_present_via_cbo() -> bool:
    try:
        lock = _cbo_lock()
        m = lock.get("metrics", {}) if isinstance(lock, dict) else {}
        return bool(m.get("gpu"))
    except Exception:
        return False


def _llm_ready_ok() -> bool:
    try:
        l = _llm_ready()
        ok = bool(l)
        # treat probe_ok true OR status running with path_ok true as acceptable
        return ok and (bool(l.get("probe_ok")) or (l.get("status") in ("running", "ok") and bool(l.get("path_ok", False))))
    except Exception:
        return False


def _hardening_cfg() -> dict:
    cfg = _load_config()
    try:
        s = cfg.get("settings", {})
        sch = s.get("scheduler", {})
        hard = sch.get("hardening", {})
        if not isinstance(hard, dict):
            hard = {}
    except Exception:
        hard = {}
    # Defaults: if GPU gate + policy full_access: enable hardened thresholds
    pol = _cbo_policy()
    enabled_default = _gpu_gate_on() and pol.get("granted") and pol.get("full_access")
    return {
        "enable": bool(hard.get("enable", enabled_default)),
        "tes_min": float(hard.get("tes_min", 90.0)),
        "velocity_min": float(hard.get("velocity_min", 0.65)),
        "max_duration_s": float(hard.get("max_duration_s", 240.0)),
        "max_llm_time_s": float(hard.get("max_llm_time_s", 15.0)),
        "consecutive": int(hard.get("consecutive", 7)),
        "require_gpu": bool(hard.get("require_gpu", True)),
        "require_llm_ready": bool(hard.get("require_llm_ready", True)),
    }


def _mode_to_args(mode: str) -> str:
    # Map autonomy mode to agent_runner args
    if mode == "safe":
        return "--skip-patches"
    if mode == "tests":
        return "--skip-patches --run-tests"
    if mode == "apply_tests":
        return "--apply --run-tests"
    return "--skip-patches"


def _system_mem_percent() -> float:
    try:
        import psutil
        return float(psutil.virtual_memory().percent)
    except Exception:
        # Fallback for Windows via wmic
        try:
            if sys.platform.startswith("win"):
                out = subprocess.check_output(["wmic", "OS", "get", "FreePhysicalMemory,TotalVisibleMemorySize", "/Value"], stderr=subprocess.DEVNULL)
                text = out.decode("utf-8", errors="ignore")
                parts = {}
                for line in text.splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        parts[k.strip()] = v.strip()
                free_kb = int(parts.get("FreePhysicalMemory", "0"))
                total_kb = int(parts.get("TotalVisibleMemorySize", "1"))
                used = total_kb - free_kb
                return round((used / total_kb) * 100.0, 2)
        except Exception:
            pass
    return 0.0


def _system_cpu_percent() -> float:
    try:
        import psutil
        return float(psutil.cpu_percent(interval=None))
    except Exception:
        return 0.0


def _load_mode() -> str:
    try:
        data = json.loads(LOAD_MODE_FILE.read_text(encoding="utf-8"))
        mode = str(data.get("mode", "normal")).strip().lower()
        return mode if mode in {"normal", "high_load"} else "normal"
    except Exception:
        return "normal"


def _demote_mode(mode: str) -> str:
    try:
        idx = AUTONOMY_SEQUENCE.index(mode)
        if idx > 0:
            return AUTONOMY_SEQUENCE[idx - 1]
    except ValueError:
        pass
    return mode


def _read_metrics_csv(csv_path: Path) -> list[dict]:
    rows: list[dict] = []
    try:
        import csv
        if not csv_path.exists():
            return rows
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
    except Exception:
        return []
    return rows


def _last_metrics(csv_path: Path) -> dict:
    rows = _read_metrics_csv(csv_path)
    return rows[-1] if rows else {}


def _audit_llm_stats(run_dir_rel: str) -> tuple[float, int]:
    try:
        audit = json.loads((ROOT / run_dir_rel / "audit.json").read_text(encoding="utf-8"))
    except Exception:
        return (0.0, 0)
    calls = audit.get("llm_calls", []) if isinstance(audit, dict) else []
    total = 0.0
    for c in calls:
        try:
            total += float(c.get("duration_s", 0.0))
        except Exception:
            pass
    return (total, len(calls))


def _recent_ok_runs(rows: list[dict], mode: str, limit: int,
                    tes_min: float = 85.0, vel_min: float = 0.5,
                    max_duration_s: Optional[float] = None,
                    max_llm_time_s: Optional[float] = None) -> int:
    ok = 0
    for r in reversed(rows):  # most recent first
        if r.get("autonomy_mode") != mode:
            continue
        try:
            stable = float(r.get("stability", "0")) >= 1.0
            tes = float(r.get("tes", "0"))
            vel = float(r.get("velocity", "0"))
            status = r.get("status") == "done"
            dur = float(r.get("duration_s", 0) or 0)
            run_dir = str(r.get("run_dir", ""))
            llm_time, llm_calls = _audit_llm_stats(run_dir) if run_dir else (0.0, 0)
        except Exception:
            continue
        within_time = (max_duration_s is None or dur <= float(max_duration_s))
        within_llm = (max_llm_time_s is None or llm_time <= float(max_llm_time_s))
        if status and stable and tes >= tes_min and vel >= vel_min and within_time and within_llm:
            ok += 1
            if ok >= limit:
                break
        else:
            break
    return ok


def _load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else {}
    except Exception:
        return {}


def _save_state(d: dict) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")
    except Exception:
        pass


def _decide_mode(auto_promote: bool, promote_after: int, cooldown_mins: int) -> str:
    # Determine current mode from state or default to safe
    st = _load_state()
    mode = st.get("mode", "safe")
    if not auto_promote:
        return mode
    # Cooldown guard
    now = time.time()
    last_promote = float(st.get("last_promote_ts", 0))
    if (now - last_promote) < (cooldown_mins * 60):
        return mode
    # Evaluate recent runs in current mode with optional hardened thresholds
    rows = _read_metrics_csv(ROOT / "logs" / "agent_metrics.csv")
    hard = _hardening_cfg()
    if hard.get("enable"):
        # Precondition gating: require GPU + llm_ready when configured
        if hard.get("require_gpu") and not (_gpu_gate_on() and _gpu_present_via_cbo()):
            return mode
        if hard.get("require_llm_ready") and not _llm_ready_ok():
            return mode
        need = int(hard.get("consecutive", promote_after))
        tes_min = float(hard.get("tes_min", 90.0))
        vel_min = float(hard.get("velocity_min", 0.65))
        max_d = hard.get("max_duration_s")
        max_llm = hard.get("max_llm_time_s")
        ok_streak = _recent_ok_runs(rows, mode, need, tes_min, vel_min, max_d, max_llm)
        if ok_streak < need:
            return mode
    else:
        if _recent_ok_runs(rows, mode, promote_after) < promote_after:
            return mode
    # Promote one level if possible
    try:
        idx = AUTONOMY_SEQUENCE.index(mode)
        if idx < len(AUTONOMY_SEQUENCE) - 1:
            new_mode = AUTONOMY_SEQUENCE[idx + 1]
            st["mode"] = new_mode
            st["last_promote_ts"] = now
            _save_state(st)
            _log(f"Auto-promote: {mode} -> {new_mode}")
            return new_mode
    except ValueError:
        pass
    return mode


def _build_agent_command(goal: str, agent_args: str | None, agent_id: int) -> list[str] | str:
    """Return a command suitable for the current host (WSL or Windows).
    - If running inside WSL: return argv list to call python tools/agent_runner.py directly.
    - If on Windows: return a shell command invoking wsl bash -lc with env AGENT_GOAL.
    """
    agent_args = agent_args or "--skip-patches"
    default_model_id = _default_model_id()
    if "--model-id" not in agent_args and default_model_id:
        agent_args = f"{agent_args} --model-id {default_model_id}"

    agent_args = (agent_args or "--skip-patches").strip()
    default_model_id = _default_model_id()
    if "--model-id" not in agent_args and default_model_id:
        agent_args = f"{agent_args} --model-id {default_model_id}".strip()

    if _is_wsl():
        # Direct WSL call
        return [
            "bash", "-lc",
            (
                "source ~/.calyx-venv/bin/activate && "
                "cd /mnt/c/Calyx_Terminal && "
                f"python tools/agent_runner.py --goal {shlex.quote(goal)} --agent-id {int(agent_id)} {agent_args}"
            ),
        ]
    else:
        # Windows host: call into WSL
        goal_quoted = shlex.quote(goal)
        cmd = (
            "wsl bash -lc "
            "\"source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && "
            f"python tools/agent_runner.py --goal {goal_quoted} --agent-id {int(agent_id)} {agent_args}\""
        )
        return cmd


def _run_agent(goal: str, agent_args: str | None, dry_run: bool, agent_id: int) -> int:
    cmd = _build_agent_command(goal, agent_args, agent_id)
    if dry_run:
        _log(f"DRY-RUN: would run: {cmd}")
        print(f"[dry-run] {cmd}")
        return 0

    _log(f"Launching agent with goal: {goal[:120]}{'...' if len(goal) > 120 else ''}")

    if isinstance(cmd, list):
        # We're in WSL context; call bash -lc
        proc = subprocess.run(cmd, cwd=str(ROOT))
        return proc.returncode
    else:
        # Windows command string that calls into WSL
        proc = subprocess.run(cmd, shell=True, cwd=str(ROOT))
        return proc.returncode


def main():
    parser = argparse.ArgumentParser(description="Agent lightweight scheduler (multi-agent)")
    parser.add_argument("--interval", type=int, default=180, help="Baseline interval seconds between attempts (default 180)")
    parser.add_argument("--goal", type=str, default=DEFAULT_GOAL, help="Goal string for Agent1")
    parser.add_argument("--agent-args", type=str, default=None, help="Extra args for agent_runner (overrides mode)")
    parser.add_argument("--agent-args-env", type=str, default=None, help="Env var name containing agent_runner args (safer than shell quoting)")
    parser.add_argument("--mode", type=str, default=None, choices=["safe","tests","apply_tests"], help="Autonomy mode")
    parser.add_argument("--agent-id", type=int, default=1, help="Target agent id (1..N); affects heartbeats and runner")
    parser.add_argument("--heartbeat-name", type=str, default=None, help="Override heartbeat file name (e.g., agent1a)")
    parser.add_argument("--auto-promote", action="store_true", help="Automatically promote mode when metrics are stable")
    parser.add_argument("--promote-after", type=int, default=5, help="Require N consecutive OK runs before promotion")
    parser.add_argument("--cooldown-mins", type=int, default=30, help="Cooldown minutes between promotions")
    # Adaptive guardrails (no hard caps):
    parser.add_argument("--adaptive-backoff", action="store_true", help="Adapt interval up/down based on recent warnings")
    parser.add_argument("--warn-backoff-factor", type=float, default=1.5, help="Multiply interval on warning (default 1.5x)")
    parser.add_argument("--ok-recover-factor", type=float, default=0.9, help="Multiply interval on OK to recover toward baseline (default 0.9x)")
    parser.add_argument("--min-interval", type=int, default=120, help="Minimum interval when recovering (default 120)")
    parser.add_argument("--max-interval", type=int, default=900, help="Maximum interval when backing off (default 900)")
    parser.add_argument("--demote-after-warns", type=int, default=3, help="Demote mode after N consecutive warnings (default 3)")
    parser.add_argument("--preflight-compile", action="store_true", help="Before apply_tests, run a quick compile check to avoid heavy runs when broken")
    parser.add_argument("--run-once", action="store_true", help="Run a single attempt and exit")
    parser.add_argument("--dry-run", action="store_true", help="Print command and exit without invoking agent")
    parser.add_argument("--beta-log", action="store_true", help="Emit beta feedback entries to logs/beta_feedback.jsonl")
    parser.add_argument(
        "--intercept-mode",
        choices=["off", "dry_run", "enforce"],
        default="dry_run",
        help="How to apply StationInterceptor to scheduler launches (default dry_run)",
    )

    args = parser.parse_args()

    # Resolve agent args from env if provided and direct arg missing
    if args.agent_args_env and not args.agent_args:
        try:
            env_val = os.environ.get(str(args.agent_args_env))
            if env_val:
                args.agent_args = env_val
        except Exception:
            pass

    # Parameterize per-agent paths/state
    global LOCK_PATH, SCH_LOCK, STATE_PATH, LOG_PATH
    aid = max(1, int(args.agent_id))
    hb_name = args.heartbeat_name or f"agent{aid}"
    LOCK_PATH = ROOT / "outgoing" / f"{hb_name}.lock"
    SCH_LOCK = ROOT / "outgoing" / (f"scheduler_{hb_name}.lock" if hb_name != "agent1" else "scheduler.lock")
    STATE_PATH = ROOT / "logs" / (f"agent_scheduler_state_{hb_name}.json" if hb_name != "agent1" else "agent_scheduler_state.json")
    LOG_PATH = ROOT / "logs" / (f"agent_scheduler_{hb_name}.log" if hb_name != "agent1" else "agent_scheduler.log")

    _log("Scheduler start")
    print("Agent1 scheduler started. Press Ctrl+C to stop.")

    try:
        while True:
            # Dynamic interval state
            st = _load_state()
            load_mode = _load_mode()
            target_baseline = int(args.interval if load_mode != "high_load" else args.interval * 2)
            baseline = int(st.get("baseline_interval", target_baseline))
            if baseline != target_baseline:
                baseline = target_baseline
                st["baseline_interval"] = baseline
                st["interval"] = baseline
            eff_interval = float(st.get("interval", baseline))
            warn_streak = int(st.get("warn_streak", 0))
            memory_skip_streak = int(st.get("memory_skip_streak", 0))
            phase = _read_lock_phase()
            if phase and any(x in phase for x in ("launch", "running")):
                next_ts = time.time() + max(5, eff_interval)
                msg = f"Agent active (phase={phase}); next in {int(max(5,eff_interval))}s"
                _log(msg)
                _hb({
                    "name": ("scheduler" if hb_name == "agent1" else f"scheduler_{hb_name}"),
                    "phase": "waiting",
                    "status": "running",
                    "status_message": msg,
                    "next_run_ts": next_ts,
                })
            else:
                cpu_limit = 65.0 if load_mode != "high_load" else 75.0
                ram_limit = 72.0 if load_mode != "high_load" else 78.0
                cpu_pct = _system_cpu_percent()
                mem_pct = _system_mem_percent()
                if cpu_pct >= cpu_limit or mem_pct >= ram_limit:
                    msg = (
                        f"High-load pause: CPU {cpu_pct:.1f}% RAM {mem_pct:.1f}% "
                        f"(limit {cpu_limit:.1f}%/{ram_limit:.1f}%)"
                    )
                    _log(msg)
                    _hb({
                        "name": ("scheduler" if hb_name == "agent1" else f"scheduler_{hb_name}"),
                        "phase": "paused",
                        "status": "waiting",
                        "status_message": msg,
                        "next_run_ts": time.time() + max(5, eff_interval),
                    })
                    time.sleep(max(5, eff_interval))
                    continue

                # Decide autonomy mode and agent args
                mode = args.mode or st.get("mode", "safe")
                mode = _decide_mode(args.auto_promote, args.promote_after, args.cooldown_mins) if args.auto_promote else mode
                eff_args = args.agent_args if args.agent_args else _mode_to_args(mode)
                metrics_rows = _read_metrics_csv(ROOT / "logs" / "agent_metrics.csv")
                tes_history = _load_tes_history(rows=metrics_rows)
                goal_prompt = args.goal
                if goal_prompt == DEFAULT_GOAL:
                    recent_rows = metrics_rows[-5:] if metrics_rows else []
                    goal_prompt = _generate_targeted_goal(mode, tes_history, recent_rows)
                removed_locks: list[str] = []
                now_ts = time.time()
                last_cleanup = float(st.get("last_lock_cleanup_ts", 0.0))
                if now_ts - last_cleanup >= LOCK_CLEANUP_INTERVAL_S:
                    removed_locks = _cleanup_stale_locks()
                    st["last_lock_cleanup_ts"] = now_ts
                    if removed_locks:
                        st["last_removed_locks"] = removed_locks[-5:]
                decision_record = {
                    "ts": time.time(),
                    "event": "tick",
                    "mode": mode,
                    "args": eff_args,
                    "goal": goal_prompt,
                    "tes_avg": tes_history[-1] if tes_history else None,
                    "warn_streak": warn_streak,
                    "auto_promote": bool(args.auto_promote),
                    "dry_run": bool(args.dry_run),
                    "memory_skip_streak": memory_skip_streak,
                }
                _append_decision(decision_record)
                _log(f"Tick: mode={mode} args='{eff_args}' auto_promote={bool(args.auto_promote)}")
                _hb({
                    "name": ("scheduler" if hb_name == "agent1" else f"scheduler_{hb_name}"),
                    "phase": "launch",
                    "status": "running",
                    "status_message": f"Launching micro-task (mode={mode})",
                    "mode": mode,
                    "goal": goal_prompt,
                    "lock_cleanup_removed": len(removed_locks),
                })
                # Optional preflight to avoid heavy apply when broken
                # Pre-launch memory guard: consult config.resource_management.adaptive_thresholds.memory_soft_limit
                cfg = _load_config()
                soft_lim = 76.0  # Base soft limit tuned for sustained apply_tests cadence without premature skips
                try:
                    rm = cfg.get("resource_management", {}) or {}
                    thr = (rm.get("adaptive_thresholds", {}) or {}).get("memory_soft_limit", soft_lim)
                    if isinstance(thr, str) and thr.endswith("%"):
                        thr = thr.rstrip("%")
                    soft_lim = float(thr)
                except Exception:
                    soft_lim = 75.0
                adaptive_soft = soft_lim
                tes_window = tes_history[-5:] if tes_history else []
                tes_avg = sum(tes_window) / len(tes_window) if tes_window else None
                if tes_avg is not None:
                    if tes_avg < 60:
                        adaptive_soft = max(soft_lim, 82.0)
                    elif tes_avg <= 80:
                        adaptive_soft = max(soft_lim, 80.0)
                    else:
                        adaptive_soft = max(soft_lim, 78.0)
                    if adaptive_soft != soft_lim:
                        _log(f"Adaptive memory soft limit now {adaptive_soft:.1f}% (TES avg {tes_avg:.1f})")
                    soft_lim = adaptive_soft
                st["last_goal"] = goal_prompt
                if tes_avg is not None:
                    st["last_tes_avg"] = tes_avg

                warn = False
                current_mem = _system_mem_percent()
                launch_blocked = False
                intercept_reason: Optional[str] = None
                rc = -1
                # Allow emergency override by gate file
                gate_override = (ROOT / "outgoing" / "gates" / "scheduler.allow").exists()
                if memory_skip_streak >= 1 and soft_lim < 72.0:
                    _log(f"Memory skip streak {memory_skip_streak}, relaxing soft limit to 72.0%")
                    soft_lim = 72.0
                if current_mem >= float(soft_lim) and (not args.dry_run) and (not gate_override):
                    # Retry logic for memory-limited launches
                    rc = -1
                    max_retries = 3
                    retry_delay = 60  # Start with 60 seconds
                    
                    for attempt in range(max_retries):
                        if attempt == 0:
                            _log(f"Skipping launch: system memory {current_mem:.1f}% >= soft_limit {soft_lim}%")
                        else:
                            wait_time = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                            _log(f"Retry {attempt}/{max_retries}: Waiting {wait_time}s before retry (memory: {current_mem:.1f}%)")
                            time.sleep(wait_time)
                            current_mem = _system_mem_percent()
                        
                        if current_mem < float(soft_lim):
                            _log(f"Memory cleared to {current_mem:.1f}%, retrying launch")
                            rc = _run_agent(goal_prompt, eff_args, args.dry_run, aid)
                            warn = False
                            memory_skip_streak = 0
                            break

                    if rc == -1:
                        # All retries exhausted
                        _log(f"Retry exhausted: Memory still {current_mem:.1f}% >= {soft_lim}% after {max_retries} attempts")
                        _hb({
                            "name": ("scheduler" if hb_name == "agent1" else f"scheduler_{hb_name}"),
                            "phase": "skipped",
                            "status": "warn",
                            "status_message": f"Skipped launch due to system memory {current_mem:.1f}% >= {soft_lim}% (retried {max_retries}x)",
                            "mode": mode,
                        })
                        warn = True
                        memory_skip_streak += 1
                else:
                    allow_launch, intercept_reason = _intercept_guard(
                        goal=goal_prompt,
                        mode=mode,
                        hb_name=hb_name,
                        interval_s=float(eff_interval),
                        tes_snapshot=tes_history[-1] if tes_history else None,
                        cpu_pct=cpu_pct,
                        mem_pct=current_mem,
                        warn_streak=warn_streak,
                        intercept_mode=args.intercept_mode,
                    )
                    if not allow_launch:
                        launch_blocked = True
                        warn = True
                        rc = -2
                    else:
                        if (not args.dry_run) and args.preflight_compile and mode == "apply_tests":
                            pre: subprocess.CompletedProcess | None = None
                            try:
                                cmd = [
                                    "bash", "-lc",
                                    "cd /mnt/c/Calyx_Terminal && python -m compileall -q ."
                                ]
                                pre = subprocess.run(["wsl"] + cmd, cwd=str(ROOT))
                                if pre.returncode != 0:
                                    _log("WSL preflight compile returned non-zero; attempting Windows fallback")
                            except FileNotFoundError:
                                _log("WSL unavailable for preflight compile; falling back to Windows compileall")
                            except Exception as exc:
                                _log(f"WSL preflight compile raised {exc!r}; falling back to Windows compileall")

                            if pre is None or pre.returncode != 0:
                                try:
                                    pre = subprocess.run(
                                        [sys.executable, "-m", "compileall", "-q", "."],
                                        cwd=str(ROOT),
                                    )
                                except Exception as exc:
                                    _log(f"Windows compileall fallback failed: {exc!r}")
                                    pre = None

                            if pre is None or pre.returncode != 0:
                                _log("Preflight compile failed; skipping run and backing off")
                                warn = True
                                rc = pre.returncode if pre is not None else 1
                            else:
                                rc = _run_agent(goal_prompt, eff_args, args.dry_run, aid)
                                warn = False
                        else:
                            rc = _run_agent(goal_prompt, eff_args, args.dry_run, aid)
                            warn = False
                    if rc != -1 and not launch_blocked:
                        memory_skip_streak = 0
                if launch_blocked:
                    _log(f"Launch blocked by interceptor: {intercept_reason or 'policy decision'}")
                else:
                    _log(f"Run completed with exit code {rc}")

                # Reflect latest metrics and simple warning in heartbeat
                if launch_blocked:
                    dur = 0.0
                    tes = float(tes_history[-1]) if tes_history else 0.0
                    last_run_dir = ""
                    llm_time, llm_calls = (0.0, 0)
                else:
                    last = _last_metrics(ROOT / "logs" / "agent_metrics.csv")
                    dur = float(last.get("duration_s", 0) or 0)
                    tes = float(last.get("tes", 0) or 0)
                    last_run_dir = str(last.get("run_dir", ""))
                    llm_time, llm_calls = _audit_llm_stats(last_run_dir) if last_run_dir else (0.0, 0)
                warn = warn or (dur > 420.0) or (llm_time > 90.0) or (llm_calls > 8)
                decision_summary = {
                    "ts": time.time(),
                    "event": "launch_blocked" if launch_blocked else "run_complete",
                    "mode": mode,
                    "goal": goal_prompt,
                    "rc": rc,
                    "warn": bool(warn),
                    "dry_run": bool(args.dry_run),
                    "duration_s": dur,
                    "tes": tes,
                    "llm_time_s": llm_time,
                    "llm_calls": llm_calls,
                    "current_mem": current_mem,
                    "soft_limit": float(soft_lim),
                    "skipped_due_to_memory": (rc == -1 and not args.dry_run),
                    "memory_skip_streak": memory_skip_streak,
                }
                if launch_blocked:
                    decision_summary["blocked_by_interceptor"] = True
                    decision_summary["intercept_reason"] = intercept_reason
                    decision_summary["intercept_mode"] = args.intercept_mode
                _append_decision(decision_summary)
                if args.beta_log and rc is not None and rc not in (-1, -2):
                    beta_record = {
                        "ts": decision_summary["ts"],
                        "mode": mode,
                        "goal": goal_prompt,
                        "rc": rc,
                        "warn": bool(warn),
                        "tes": tes,
                        "duration_s": dur,
                        "llm_time_s": llm_time,
                        "llm_calls": llm_calls,
                    }
                    beta_path = ROOT / "logs" / "beta_feedback.jsonl"
                    try:
                        with beta_path.open("a", encoding="utf-8") as beta_fp:
                            beta_fp.write(json.dumps(beta_record, ensure_ascii=False) + "\n")
                    except Exception:
                        _log(f"Failed to append beta feedback to {beta_path}")

                # Adaptive backoff & optional demotion
                note = ""
                if args.adaptive_backoff:
                    if warn:
                        warn_streak += 1
                        eff_interval = min(float(args.max_interval), max(5.0, eff_interval * float(args.warn_backoff_factor)))
                        note = f"backoff→{int(eff_interval)}s"
                        if args.auto_promote and warn_streak >= int(args.demote_after_warns):
                            new_mode = _demote_mode(mode)
                            if new_mode != mode:
                                st["mode"] = new_mode
                                st["last_promote_ts"] = time.time()
                                note += f"; demote {mode}->{new_mode}"
                                mode = new_mode
                            warn_streak = 0
                    else:
                        warn_streak = 0
                        # recover toward baseline but not below it
                        eff_interval = max(float(baseline), eff_interval * float(args.ok_recover_factor))
                # persist state
                st["interval"] = int(eff_interval)
                st["warn_streak"] = warn_streak
                st.setdefault("mode", mode)
                st.setdefault("baseline_interval", baseline)
                st["memory_skip_streak"] = memory_skip_streak
                _save_state(st)

                next_ts = time.time() + max(5, eff_interval)
                hb_payload = {
                    "name": ("scheduler" if hb_name == "agent1" else f"scheduler_{hb_name}"),
                    "mode": mode,
                    "next_run_ts": next_ts,
                }
                if launch_blocked:
                    hb_payload.update({
                        "phase": "blocked",
                        "status": "warn",
                        "status_message": f"Interceptor block: {intercept_reason or 'see reports/intercepts'}",
                        "last_tes": tes,
                    })
                else:
                    hb_payload.update({
                        "phase": "done",
                        "status": "warn" if warn else "done",
                        "status_message": f"TES={tes:.1f} dur={dur:.1f}s llm={llm_time:.1f}s/{llm_calls} next in {int(max(5,eff_interval))}s {note}",
                        "last_tes": tes,
                        "last_duration_s": dur,
                        "last_llm_time_s": llm_time,
                        "last_llm_calls": llm_calls,
                        "last_run_dir": last_run_dir,
                    })
                _hb(hb_payload)

            if args.run_once:
                break
            time.sleep(max(5, eff_interval))
    except KeyboardInterrupt:
        _log("Scheduler interrupted by user")
    finally:
        _log("Scheduler stop")


if __name__ == "__main__":
    main()
