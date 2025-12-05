#!/usr/bin/env python3
"""
Calyx Bridge Overseer (CBO)
---------------------------------

Purpose:
- Preflight the local environment (Windows-first, WSL optional) and establish guardrails.
- Ensure essential supervisory loops are alive with auto-heal and conservative defaults.
- Minimize human involvement in activating Station Calyx and keeping agents productive.

What it does:
- Writes a lightweight CBO heartbeat at outgoing/cbo.lock with system telemetry.
- Ensures gates/locks directories exist; defaults to Network=OFF, Local LLM gate=ON (configurable).
- Starts and watches the adaptive supervisor (Windows/WSL) for essential loops.
- Starts long-period maintenance loops (metrics cron, log housekeeping) if missing.
- Exposes a --status mode for quick checks and a --dry-run for safe previews.

Conservative by design: no network calls; uses stdlib + psutil only.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

TRACE_LOG = Path(__file__).resolve().parents[1] / "logs" / "overseer_loop_trace.jsonl"
DEFAULT_RESPECT_FRAME = "neutral_observer"
DEFAULT_LAWS = [2, 4, 5, 9, 10]

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None  # lazy-fallback: status will skip system metrics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outgoing'
OUT_GATES = OUT / 'gates'
OUT_POLICIES = OUT / 'policies'
LOGS = ROOT / 'logs'
STATE = ROOT / 'state'

LOCK_CBO = OUT / 'cbo.lock'
LOCK_SVF = OUT / 'svf.lock'
LOCK_TRIAGE = OUT / 'triage.lock'
LOCK_SYSINT = OUT / 'sysint.lock'
LOCK_NAV = OUT / 'navigator.lock'
LOCK_SCHED = OUT / 'scheduler.lock'
LOCK_LLM_READY = OUT / 'llm_ready.lock'

GATE_NETWORK = OUT_GATES / 'network.ok'
GATE_LLM = OUT_GATES / 'llm.ok'
GATE_CBO = OUT_GATES / 'cbo.ok'

POLICY_CBO = OUT_POLICIES / 'cbo_permissions.json'
CAPACITY_FLAGS = OUT / 'capacity.flags.json'
GPU_ENV_PY = ROOT / 'venvs' / 'calyx-gpu' / 'Scripts' / 'python.exe'
AI4ALL_MONITOR_STATE = ROOT / 'Projects' / 'AI_for_All' / 'outgoing' / 'ai4all' / 'monitoring' / 'recent_metrics.json'


@dataclass
class CBOConfig:
    interval: float = 30.0  # seconds between heartbeats/ensures
    enable_scheduler: bool = False
    allow_daemons: bool = False  # Architect-controlled: allow long-running supervisor/optimizer/metrics loops
    network_default_on: bool = False
    llm_default_on: bool = True
    grant_authority: bool = True
    metrics_cron_interval: int = 900
    housekeeping_keep_days: int = 14
    supervisor_interval: float = 60.0
    navigator_control_on_windows: bool = False
    nav_pause_sec: int = 90
    nav_hot_interval: int = 90
    nav_cool_interval: int = 20
    enable_optimizer: bool = False
    optimizer_interval: float = 120.0
    optimizer_enable_teaching: bool = False
    optimizer_teach_interval_mins: int = 30


def _print(msg: str) -> None:
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"{ts} [CBO] {msg}", flush=True)


def _ensure_dirs() -> None:
    for p in (OUT, OUT_GATES, OUT_POLICIES, LOGS, STATE):
        p.mkdir(parents=True, exist_ok=True)
    TRACE_LOG.parent.mkdir(parents=True, exist_ok=True)


def _log_trace(
    loop: str,
    mode: str,
    decision: str,
    reason: str,
    *,
    effects: Optional[list[str]] = None,
    test_mode: bool = False,
    laws: Optional[list[int]] = None,
    respect_frame: str = DEFAULT_RESPECT_FRAME,
    duration_ms: Optional[float] = None,
    err: Optional[str] = None,
) -> None:
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "loop": loop,
        "mode": mode,
        "decision": decision,
        "reason": reason,
        "effects": effects or [],
        "test_mode": bool(test_mode),
        "respect_frame": respect_frame,
        "laws": laws or DEFAULT_LAWS,
    }
    if duration_ms is not None:
        entry["duration_ms"] = duration_ms
    if err:
        entry["err"] = err
    try:
        with TRACE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # Trace logging must never break overseer operation
        pass


def _set_gate_defaults(cfg: CBOConfig) -> None:
    # Network gate: default OFF unless explicitly requested
    if cfg.network_default_on:
        try:
            GATE_NETWORK.write_text('ok', encoding='utf-8')
        except Exception:
            pass
    else:
        try:
            if GATE_NETWORK.exists():
                GATE_NETWORK.unlink()
        except Exception:
            pass
    # LLM gate: default ON to favor local LLM usage when present
    try:
        if cfg.llm_default_on:
            GATE_LLM.write_text('ok', encoding='utf-8')
        else:
            if GATE_LLM.exists():
                GATE_LLM.unlink()
    except Exception:
        pass


def _ensure_permissions(cfg: CBOConfig) -> None:
    """Grant CBO authority and establish a default permissions policy.

    Authority gate (gates/cbo.ok) toggles whether CBO may take control decisions
    like enabling scheduler or navigator control on Windows. The policy file lists
    allowed actions and is conservative by default.
    """
    try:
        if cfg.grant_authority:
            GATE_CBO.write_text('ok', encoding='utf-8')
        else:
            if GATE_CBO.exists():
                GATE_CBO.unlink()
    except Exception:
        pass

    if not POLICY_CBO.exists():
        policy = {
            'version': 1,
            'granted': bool(cfg.grant_authority),
            'allowed_actions': [
                'supervise_core_loops',
                'toggle_llm_gate',
                'toggle_network_gate',
                'run_metrics_cron',
                'run_housekeeping',
                'enable_agent_scheduler',
                'navigator_control',
                'adjust_intervals'
            ],
            'constraints': {
                # Network stays OFF by default; CBO may not turn it ON without an explicit gate toggle
                'network_must_default_off': True,
                'require_local_llm_ready_for_gpu_probe': True,
                'windows_navigator_control_requires_authority_gate': True
            }
        }
        try:
            POLICY_CBO.write_text(json.dumps(policy, indent=2), encoding='utf-8')
        except Exception:
            pass


def _hb_fresh(path: Path, grace: float) -> bool:
    try:
        return path.exists() and (time.time() - path.stat().st_mtime) <= grace
    except Exception:
        return False


def _start_detached_win(py_rel: str, args: list[str], *, prefer_gpu: bool = False) -> None:
    """Start a Python process detached on Windows (no window)."""
    try:
        creationflags = 0x08000000  # CREATE_NO_WINDOW
        chosen = GPU_ENV_PY if prefer_gpu and GPU_ENV_PY.exists() else Path(sys.executable)
        subprocess.Popen([str(chosen), '-u', str(ROOT / py_rel), *args], cwd=str(ROOT),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
    except Exception:
        pass


def _start_detached_wsl(py_rel: str, args: list[str]) -> None:
    """Start a Python process inside WSL, detached via nohup/disown."""
    try:
        cmd = 'bash -lc "source ~/.calyx-venv/bin/activate || true && cd /mnt/c/Calyx_Terminal && nohup python -u ' \
              + py_rel + (' ' + ' '.join(args) if args else '') + ' > logs/cbo_' + Path(py_rel).name + '.log 2>&1 & disown"'
        subprocess.Popen(['wsl', cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _is_wsl_ready(timeout: float = 3.0) -> bool:
    try:
        rc = subprocess.run(['wsl', 'bash', '-lc', 'echo ok'], capture_output=True, text=True, timeout=timeout).returncode
        return rc == 0
    except Exception:
        return False


def _ensure_adaptive_supervisor(cfg: CBOConfig) -> tuple[str, str, list[str]]:
    # Use a soft heartbeat heuristic: if the adaptive supervisor is missing, (re)start it.
    grace = max(20.0, cfg.supervisor_interval * 2)
    # We consider the suite healthy if core locks are fresh.
    healthy = any([
        _hb_fresh(LOCK_SVF, grace),
        _hb_fresh(LOCK_TRIAGE, grace),
        _hb_fresh(LOCK_SYSINT, grace),
        _hb_fresh(LOCK_NAV, grace),
    ])
    if healthy:
        return "skip", "supervisor locks fresh", []
    args = [
        '--interval', str(cfg.supervisor_interval),
        '--navigator-interval', '3',
        '--nav-pause-sec', str(cfg.nav_pause_sec),
        '--hot-interval', str(cfg.nav_hot_interval),
        '--cool-interval', str(cfg.nav_cool_interval),
    ]
    # Only permit Windows control mode if authority gate exists
    if cfg.navigator_control_on_windows and GATE_CBO.exists():
        args.append('--navigator-control')
    if cfg.enable_scheduler:
        args += ['--include-scheduler', '--scheduler-interval', '180']
    if _is_wsl_ready():
        _start_detached_wsl('tools/svc_supervisor_adaptive.py', args)
        return "run", "supervisor stale; started svc_supervisor_adaptive (wsl)", ["started:svc_supervisor_adaptive"]
    else:
        _start_detached_win('tools/svc_supervisor_adaptive.py', args)
        return "run", "supervisor stale; started svc_supervisor_adaptive (win)", ["started:svc_supervisor_adaptive"]


def _ensure_metrics_cron(interval_sec: int) -> tuple[str, str, list[str]]:
    grace = max(60.0, interval_sec * 2)
    # metrics_cron writes logs/metrics_cron_state.json
    state_path = ROOT / 'logs' / 'metrics_cron_state.json'
    if _hb_fresh(state_path, grace):
        return "skip", "metrics_cron fresh", []
    if _is_wsl_ready():
        _start_detached_wsl('tools/metrics_cron.py', ['--interval', str(interval_sec)])
        return "run", "metrics_cron stale; started (wsl)", ["started:metrics_cron"]
    else:
        _start_detached_win('tools/metrics_cron.py', ['--interval', str(interval_sec)])
        return "run", "metrics_cron stale; started (win)", ["started:metrics_cron"]


def _ensure_optimizer(cfg: CBOConfig) -> tuple[str, str, list[str]]:
    """Ensure the cbo_optimizer loop is running when enabled.

    The optimizer writes dynamic overrides for the adaptive supervisor and may
    schedule teaching cycles if allowed by policy and config.
    We detect presence by the overrides file freshness; if stale, (re)start.
    """
    if not cfg.enable_optimizer:
        return "skip", "optimizer disabled", []
    # Consider optimizer healthy if overrides file was updated within 2x its interval
    tuning_dir = OUT / 'tuning'
    overrides = tuning_dir / 'supervisor_overrides.json'
    grace = max(60.0, cfg.optimizer_interval * 2)
    healthy = _hb_fresh(overrides, grace)
    if healthy:
        return "skip", "optimizer overrides fresh", []
    args = ['--interval', str(cfg.optimizer_interval)]
    if cfg.optimizer_enable_teaching:
        args += ['--enable-teaching', '--teach-interval-mins', str(int(cfg.optimizer_teach_interval_mins))]
    if _is_wsl_ready():
        _start_detached_wsl('tools/cbo_optimizer.py', args)
        return "run", "optimizer stale; started (wsl)", ["started:cbo_optimizer"]
    else:
        _start_detached_win('tools/cbo_optimizer.py', args)
        return "run", "optimizer stale; started (win)", ["started:cbo_optimizer"]


def _ensure_production_monitor() -> tuple[str, str, list[str]]:
    """Keep the AI4All production monitor running for alert coverage."""
    grace = 180.0  # monitor interval defaults to 60s; allow 3 cycles
    if _hb_fresh(AI4ALL_MONITOR_STATE, grace):
        return "skip", "production monitor fresh", []

    args = [
        '--interval', '60',
        '--alert-interval', '30',
        '--performance-decline-threshold', '-0.1',
        '--stability-threshold', '0.7'
    ]
    if _is_wsl_ready():
        _start_detached_wsl('Projects/AI_for_All/monitoring/production_monitor.py', args)
        return "run", "production monitor stale; started (wsl)", ["started:production_monitor"]
    else:
        _start_detached_win('Projects/AI_for_All/monitoring/production_monitor.py', args, prefer_gpu=True)
        return "run", "production monitor stale; started (win)", ["started:production_monitor"]


def _ensure_housekeeping(keep_days: int) -> tuple[str, str, list[str]]:
    # Run a lightweight one-shot if last archive run was > 24h ago
    marker = LOGS / 'last_housekeeping.txt'
    now = time.time()
    if marker.exists() and (now - marker.stat().st_mtime) < 24 * 3600:
        return "skip", "housekeeping recent", []
    args = ['run', '--keep-days', str(int(keep_days))]
    try:
        # Fire and forget, no spam
        subprocess.Popen([sys.executable, '-u', str(ROOT / 'tools' / 'log_housekeeper.py'), *args],
                         cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        marker.write_text(time.strftime('%F %T'), encoding='utf-8')
        return "run", "housekeeping fired", ["started:log_housekeeper"]
    except Exception as exc:
        return "error", f"housekeeping error: {exc}", []


LOOP_FUNCS = {
    "supervisor": lambda cfg: _ensure_adaptive_supervisor(cfg),
    "metrics": lambda cfg: _ensure_metrics_cron(cfg.metrics_cron_interval),
    "optimizer": lambda cfg: _ensure_optimizer(cfg),
    "production_monitor": lambda cfg: _ensure_production_monitor(),
    "housekeeping": lambda cfg: _ensure_housekeeping(cfg.housekeeping_keep_days),
}


def _run_named_loop(loop: str, cfg: CBOConfig, mode: str, *, test_mode: bool, allow_daemons: bool) -> str:
    start = time.time()
    err: Optional[str] = None
    effects: list[str] = []
    try:
        if loop == "heartbeat":
            ok = _write_heartbeat(cfg)
            decision = "run" if ok else "error"
            reason = "heartbeat write ok" if ok else "heartbeat write failed"
            if ok:
                effects = ["wrote_cbo_lock", "recomputed_capacity"]
        else:
            if not allow_daemons:
                decision = "skip"
                reason = "allow_daemons=false"
            else:
                fn = LOOP_FUNCS.get(loop)
                if fn is None:
                    decision = "skip"
                    reason = "unknown_loop"
                else:
                    decision, reason, effects = fn(cfg)
    except Exception as exc:
        decision = "error"
        reason = f"{loop} exception"
        err = str(exc)
    duration_ms = round((time.time() - start) * 1000.0, 2)
    _log_trace(loop, mode, decision, reason, effects=effects, test_mode=test_mode, duration_ms=duration_ms, err=err)
    return decision


def _sys_metrics() -> dict:
    d: dict[str, object] = {
        'psutil': bool(psutil is not None),
    }
    try:
        if psutil is None:
            return d
        vm = psutil.virtual_memory()
        d.update({
            'cpu_pct': psutil.cpu_percent(interval=None),
            'mem_used_pct': vm.percent,
            'disk_free_pct': None,
        })
        # Disk (project drive)
        try:
            usage = psutil.disk_usage(str(ROOT))
            d['disk_free_pct'] = round((usage.free / usage.total) * 100, 2)
        except Exception:
            pass
    except Exception:
        pass
    return d


def _gpu_metrics() -> Optional[dict]:
    """Optional GPU telemetry (NVIDIA).

    Priority:
    - nvidia-smi (no deps)
    - torch.cuda (if installed)
    Only run when LLM ready lock exists, to avoid probing unnecessarily.
    """
    if not LOCK_LLM_READY.exists():
        return None
    # Try nvidia-smi for a concise CSV
    try:
        res = subprocess.run([
            'nvidia-smi',
            '--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu',
            '--format=csv,noheader,nounits'
        ], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            gpus = []
            for line in res.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 5:
                    gpus.append({
                        'name': parts[0],
                        'mem_total_mb': float(parts[1]),
                        'mem_used_mb': float(parts[2]),
                        'util_pct': float(parts[3]),
                        'temp_c': float(parts[4]),
                    })
            return {'backend': 'nvidia-smi', 'gpus': gpus}
    except Exception:
        pass
    # Try torch.cuda
    try:
        import torch  # type: ignore
        if torch.cuda.is_available():
            count = torch.cuda.device_count()
            gpus = []
            for i in range(count):
                name = torch.cuda.get_device_name(i)
                util = None
                mem_total = torch.cuda.get_device_properties(i).total_memory / (1024 * 1024)
                mem_alloc = torch.cuda.memory_allocated(i) / (1024 * 1024)
                gpus.append({
                    'name': name,
                    'mem_total_mb': round(float(mem_total), 2),
                    'mem_used_mb': round(float(mem_alloc), 2),
                    'util_pct': util,
                    'temp_c': None,
                })
            return {'backend': 'torch.cuda', 'gpus': gpus}
    except Exception:
        pass
    return None


def _capacity_from_metrics(metrics: dict) -> dict:
    """Compute capacity/headroom flags from one snapshot of metrics.

    Definitions (conservative):
    - cpu_ok: CPU <= 50%
    - mem_ok: Mem used <= 80%
    - gpu_ok: if GPU seen then util <= 40%, else True (no GPU pressure)
    - super_cool: CPU <= 35%, Mem <= 70%, GPU util <= 30% or absent
    - verified: super_cool and llm_ready.lock exists (basic readiness gate)
    - score: simple headroom score in [0,1] (higher is more headroom)
    """
    cpu = float(metrics.get('cpu_pct') or 0)
    mem = float(metrics.get('mem_used_pct') or 0)
    gpu_util = None
    try:
        g0 = ((metrics.get('gpu') or {}).get('gpus') or [{}])[0]
        gpu_util = float(g0.get('util_pct')) if g0 and g0.get('util_pct') is not None else None
    except Exception:
        gpu_util = None
    # Guardrails align with bridge pulse + coordinator domain policies
    cpu_guard = 70.0
    mem_guard = 75.0
    gpu_guard = 85.0
    cpu_ok = cpu <= cpu_guard
    mem_ok = mem <= mem_guard
    gpu_ok = (gpu_util is None) or (gpu_util <= gpu_guard)
    # Super-cool means plenty of headroom for experiments/research-mode spikes
    super_cool = (
        (cpu <= 40.0)
        and (mem <= 65.0)
        and ((gpu_util is None) or (gpu_util <= 40.0))
    )
    # Headroom score: average of per-resource headroom (clipped)
    def clamp01(x: float) -> float:
        return 0.0 if x < 0 else (1.0 if x > 1 else x)
    cpu_head = clamp01((cpu_guard - cpu) / cpu_guard)  # 1.0 if cpu=0, 0.0 if cpu>=guard
    mem_head = clamp01((mem_guard - mem) / mem_guard)
    if gpu_util is None:
        gpu_head = 1.0
    else:
        gpu_head = clamp01((gpu_guard - gpu_util) / gpu_guard)
    score = round(float((cpu_head + mem_head + gpu_head) / 3.0), 3)
    verified = bool(super_cool and LOCK_LLM_READY.exists())
    return {
        'cpu_ok': cpu_ok,
        'mem_ok': mem_ok,
        'gpu_ok': gpu_ok,
        'super_cool': super_cool,
        'verified': verified,
        'score': score,
    }


def _write_heartbeat(cfg: CBOConfig) -> bool:
    hb = {
        'ts': time.time(),
        'iso': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'version': 1,
        'gates': {
            'network': GATE_NETWORK.exists(),
            'llm': GATE_LLM.exists(),
            'cbo_authority': GATE_CBO.exists(),
        },
        'locks': {
            'svf': LOCK_SVF.exists(),
            'triage': LOCK_TRIAGE.exists(),
            'sysint': LOCK_SYSINT.exists(),
            'navigator': LOCK_NAV.exists(),
            'scheduler': LOCK_SCHED.exists(),
            'llm_ready': LOCK_LLM_READY.exists(),
        },
        'directives': {
            'system_uptime_target_pct': 0.90,
            'description': 'Maintain system uptime > 90% over 24h'
        },
        'metrics': {
            **_sys_metrics(),
        },
        'config': {
            'interval': cfg.interval,
            'supervisor_interval': cfg.supervisor_interval,
            'enable_scheduler': cfg.enable_scheduler,
        }
    }
    gpu = _gpu_metrics()
    if gpu:
        hb['metrics']['gpu'] = gpu
    # Capacity flags from current metrics
    try:
        cap = _capacity_from_metrics(hb['metrics'])
        hb['capacity'] = cap
        CAPACITY_FLAGS.write_text(json.dumps(cap, ensure_ascii=False), encoding='utf-8')
    except Exception:
        pass
    try:
        LOCK_CBO.write_text(json.dumps(hb, ensure_ascii=False), encoding='utf-8')
        return True
    except Exception:
        return False


def run_loop(cfg: CBOConfig) -> None:
    _ensure_dirs()
    _ensure_permissions(cfg)
    _set_gate_defaults(cfg)
    mode = "daemon" if cfg.allow_daemons else "safe"
    daemon_loops = ["supervisor", "metrics", "optimizer", "production_monitor", "housekeeping"]
    # Main loop
    while True:
        for loop_name in daemon_loops:
            _run_named_loop(loop_name, cfg, mode, test_mode=False, allow_daemons=cfg.allow_daemons)
        _run_named_loop("heartbeat", cfg, mode, test_mode=False, allow_daemons=True)
        time.sleep(max(5.0, float(cfg.interval)))


def run_test_mode(cfg: CBOConfig, loop_names: list[str], iterations: int, max_seconds: float, sleep_seconds: Optional[float]) -> Path:
    """Bounded test mode for daemon loops; always runs with allow_daemons=True and exits after bounds."""
    mode = "daemon"
    counts: dict[str, dict[str, int]] = {}
    start_ts = time.time()
    sleep_val = sleep_seconds if sleep_seconds is not None else cfg.interval
    for i in range(max(1, iterations)):
        for loop_name in loop_names:
            counts.setdefault(loop_name, {"run": 0, "skip": 0, "error": 0})
            decision = _run_named_loop(loop_name, cfg, mode, test_mode=True, allow_daemons=True)
            counts[loop_name][decision] = counts[loop_name].get(decision, 0) + 1
        if (time.time() - start_ts) >= max_seconds:
            break
        time.sleep(max(0.1, float(sleep_val)))
    end_ts = time.time()
    report_path = ROOT / "reports" / "cbo_overseer_daemon_test_summary_v0.1.md"
    report_lines = [
        "# CBO Overseer Daemon Test Summary v0.1",
        f"Start (UTC): {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(start_ts))}",
        f"End (UTC):   {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(end_ts))}",
        f"Iterations requested: {iterations}",
        f"Loops: {', '.join(loop_names)}",
        "",
        "## Outcomes per loop",
    ]
    for loop_name in loop_names:
        c = counts.get(loop_name, {})
        report_lines.append(f"- {loop_name}: run={c.get('run',0)} skip={c.get('skip',0)} error={c.get('error',0)}")
    report_lines += [
        "",
        "Notes: test_mode=true traces written to logs/overseer_loop_trace.jsonl (Law 2/4/5/9/10 compliance).",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return report_path


def cmd_status() -> int:
    _ensure_dirs()
    # Opportunistically establish permissions in status mode too
    cfg = CBOConfig()
    _ensure_permissions(cfg)
    gates = {
        'network': GATE_NETWORK.exists(),
        'llm': GATE_LLM.exists(),
        'cbo_authority': GATE_CBO.exists(),
    }
    locks = {
        'svf': LOCK_SVF.exists(),
        'triage': LOCK_TRIAGE.exists(),
        'sysint': LOCK_SYSINT.exists(),
        'navigator': LOCK_NAV.exists(),
        'scheduler': LOCK_SCHED.exists(),
        'llm_ready': LOCK_LLM_READY.exists(),
    }
    status = {
        'root': str(ROOT),
        'gates': gates,
        'locks': locks,
        'wsl_ready': _is_wsl_ready(),
        'metrics': {**_sys_metrics(), 'gpu': _gpu_metrics()},
    }
    # Include capacity flags in status and mirror file for inspection
    try:
        cap = _capacity_from_metrics(status['metrics'])
        status['capacity'] = cap
        CAPACITY_FLAGS.write_text(json.dumps(cap, ensure_ascii=False), encoding='utf-8')
    except Exception:
        pass
    print(json.dumps(status, indent=2))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description='Calyx Bridge Overseer')
    ap.add_argument('--interval', type=float, default=30.0, help='Heartbeat/ensure interval (seconds)')
    ap.add_argument('--enable-scheduler', action='store_true', help='Also supervise agent_scheduler')
    ap.add_argument('--allow-daemons', action='store_true', help='Allow CBO to start long-running supervisor/optimizer/metrics loops')
    ap.add_argument('--network-on', action='store_true', help='Enable network gate by default (unsafe; default OFF)')
    ap.add_argument('--llm-off', action='store_true', help='Disable local LLM gate by default (default ON)')
    ap.add_argument('--navigator-control-on-windows', action='store_true', help='Allow control mode on Windows')
    ap.add_argument('--no-authority', action='store_true', help='Do not grant CBO authority (monitor-only)')
    ap.add_argument('--supervisor-interval', type=float, default=60.0, help='Adaptive supervisor check cadence')
    ap.add_argument('--metrics-interval', type=int, default=900, help='metrics_cron interval (seconds)')
    ap.add_argument('--housekeeping-keep-days', type=int, default=14, help='Days to keep unarchived *.md logs')
    ap.add_argument('--status', action='store_true', help='Print status and exit')
    ap.add_argument('--dry-run', action='store_true', help='Print planned actions (no starts), then exit')
    ap.add_argument('--enable-optimizer', action='store_true', help='Start cbo_optimizer loop to tune intervals at runtime')
    ap.add_argument('--optimizer-interval', type=float, default=120.0, help='cbo_optimizer cadence (seconds)')
    ap.add_argument('--enable-teaching', action='store_true', help='Allow optimizer to schedule CP6/CP7 cycles')
    ap.add_argument('--teach-interval-mins', type=int, default=30, help='Minimum minutes between teaching cycles')
    ap.add_argument('--test-loops', type=str, help='Comma-separated list of loops to exercise in bounded test mode (daemon)')
    ap.add_argument('--test-iterations', type=int, default=1, help='Iterations per loop in test mode (default: 1)')
    ap.add_argument('--test-max-seconds', type=float, default=300.0, help='Wall-clock cap for test mode (seconds)')
    ap.add_argument('--test-sleep', type=float, default=None, help='Sleep between test iterations (seconds); defaults to --interval')
    args = ap.parse_args(argv)

    if args.status:
        return cmd_status()

    cfg = CBOConfig(
        interval=float(args.interval),
        enable_scheduler=bool(args.enable_scheduler),
        allow_daemons=bool(args.allow_daemons),
        network_default_on=bool(args.network_on),
        llm_default_on=not bool(args.llm_off),
        metrics_cron_interval=int(args.metrics_interval),
        housekeeping_keep_days=int(args.housekeeping_keep_days),
        supervisor_interval=float(args.supervisor_interval),
        navigator_control_on_windows=bool(args.navigator_control_on_windows),
        grant_authority=not bool(args.no_authority),
        enable_optimizer=bool(args.enable_optimizer),
        optimizer_interval=float(args.optimizer_interval),
        optimizer_enable_teaching=bool(args.enable_teaching),
        optimizer_teach_interval_mins=int(args.teach_interval_mins),
    )

    # Policy-aware escalations: if policy grants full_access, promote capabilities
    try:
        if POLICY_CBO.exists():
            pol = json.loads(POLICY_CBO.read_text(encoding='utf-8'))
            if pol.get('granted') and pol.get('full_access'):
                cfg.enable_scheduler = True
                cfg.navigator_control_on_windows = True
                # Auto-enable optimizer; teaching gated by policy feature
                cfg.enable_optimizer = True if not args.enable_optimizer else cfg.enable_optimizer
            # Respect teaching_cycles policy when present
            feat = (pol.get('features') or {}).get('teaching_cycles') or {}
            if feat:
                if feat.get('enabled') is True and not args.enable_teaching:
                    cfg.optimizer_enable_teaching = True
                # Allow policy to suggest a default interval
                try:
                    mins = int(feat.get('interval_minutes_default'))
                    if mins > 0:
                        cfg.optimizer_teach_interval_mins = mins
                except Exception:
                    pass
    except Exception:
        pass

    # Bounded test mode (daemon, forced allow)
    if args.test_loops:
        loop_names = [ln.strip() for ln in (args.test_loops or "").split(",") if ln.strip()]
        if not loop_names:
            loop_names = ["heartbeat"]
        cfg.allow_daemons = True
        _ensure_dirs()
        _ensure_permissions(cfg)
        _set_gate_defaults(cfg)
        report_path = run_test_mode(
            cfg,
            loop_names=loop_names,
            iterations=max(1, int(args.test_iterations)),
            max_seconds=float(args.test_max_seconds),
            sleep_seconds=args.test_sleep,
        )
        print(f"[OK] Test mode complete: {report_path}")
        return 0

    if args.dry_run:
        plan = {
            'will_set_gates': {
                'network_on': cfg.network_default_on,
                'llm_on': cfg.llm_default_on,
            },
            'will_supervise': ['svf_probe', 'triage_probe', 'sys_integrator', 'traffic_navigator'] + (['agent_scheduler'] if cfg.enable_scheduler else []),
            'metrics_interval': cfg.metrics_cron_interval,
            'housekeeping_keep_days': cfg.housekeeping_keep_days,
            'supervisor_interval': cfg.supervisor_interval,
            'optimizer': {
                'enabled': cfg.enable_optimizer,
                'interval': cfg.optimizer_interval,
                'teaching_enabled': cfg.optimizer_enable_teaching,
                'teach_interval_mins': cfg.optimizer_teach_interval_mins,
            },
            'allow_daemons': cfg.allow_daemons,
        }
        print(json.dumps(plan, indent=2))
        return 0

    _print('Starting CBO loop')
    run_loop(cfg)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
