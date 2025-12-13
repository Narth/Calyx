#!/usr/bin/env python3
"""
CBO Optimizer
- Reads local telemetry and agent metrics
- Writes dynamic overrides for the adaptive supervisor
- Optionally schedules teaching/self-discipline cycles (CP6/CP7) when system is cool

Artifacts:
- Overrides: outgoing/tuning/supervisor_overrides.json
- State: state/cbo_optimizer_state.json (last overrides, last teaching ts)

Usage (Windows PowerShell):
    python -u tools/cbo_optimizer.py --interval 120 --enable-teaching --teach-interval-mins 30 --dry-run
    python -u tools/cbo_optimizer.py --interval 120 --enable-teaching --teach-interval-mins 30

Notes:
- Stdlib only (optional psutil not required). No network calls.
- Conservative bounds and gates; will not enable control/scheduler unless policy grants authority.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

# GPU utilities for capacity-aware decisions
try:
    from tools.gpu_utils import get_gpu_utilization, should_use_gpu_for_llm
except Exception:
    def get_gpu_utilization():
        return None
    def should_use_gpu_for_llm():
        return False

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outgoing'
LOGS = ROOT / 'logs'
STATE_DIR = ROOT / 'state'
POLICIES = OUT / 'policies'
GATES = OUT / 'gates'
TUNING = OUT / 'tuning'
TEACH_DIR = OUT / 'teaching'

HB_CBO = OUT / 'cbo.lock'
LOCK_LLM_READY = OUT / 'llm_ready.lock'
POLICY_CBO = POLICIES / 'cbo_permissions.json'
OVERRIDES = TUNING / 'supervisor_overrides.json'
STATE = STATE_DIR / 'cbo_optimizer_state.json'


def _print(msg: str) -> None:
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"{ts} [CBO-OPT] {msg}", flush=True)


def _policy() -> dict:
    try:
        if POLICY_CBO.exists():
            return json.loads(POLICY_CBO.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {}


def _is_wsl_ready(timeout: float = 3.0) -> bool:
    try:
        rc = subprocess.run(['wsl', 'bash', '-lc', 'echo ok'], capture_output=True, text=True, timeout=timeout).returncode
        return rc == 0
    except Exception:
        return False


def _spawn_detached_win(py_rel: str, args: list[str]) -> None:
    try:
        creationflags = 0x08000000  # CREATE_NO_WINDOW
        subprocess.Popen([sys.executable, '-u', str(ROOT / py_rel), *args], cwd=str(ROOT),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
    except Exception:
        pass


def _spawn_detached_wsl(py_rel: str, args: list[str]) -> None:
    try:
        cmd = 'bash -lc "source ~/.calyx-venv/bin/activate || true && cd /mnt/c/Calyx_Terminal && nohup python -u ' \
              + py_rel + (' ' + ' '.join(args) if args else '') + ' > logs/cbo_optimizer_teach.log 2>&1 & disown"'
        subprocess.Popen(['wsl', cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _read_cbo_telemetry() -> dict:
    d: dict = {}
    try:
        if HB_CBO.exists():
            d = json.loads(HB_CBO.read_text(encoding='utf-8'))
    except Exception:
        d = {}
    return d


def _recent_metrics() -> Tuple[Optional[float], Optional[float]]:
    """Return (tes_mean, velocity_proxy) from logs/agent_metrics.csv if available.
    Velocity proxy: difference between mean of last 10 and previous 10 entries.
    """
    path = LOGS / 'agent_metrics.csv'
    if not path.exists():
        return None, None
    try:
        rows = []
        with path.open('r', encoding='utf-8', newline='') as f:
            rdr = csv.DictReader(f)
            for r in rdr:
                rows.append(r)
        if not rows:
            return None, None
        # Normalize keys
        def fval(r, klist):
            for k in klist:
                if k in r and r[k] not in (None, ''):
                    try:
                        return float(r[k])
                    except Exception:
                        pass
            return None
        vals = [fval(r, ['TES', 'tes', 'tes_score']) for r in rows]
        vals = [v for v in vals if isinstance(v, (float, int))]
        if not vals:
            return None, None
        # Normalize if values look like percentages
        scale = 1.0
        try:
            if max(vals) > 2.0:
                scale = 0.01
        except Exception:
            scale = 1.0
        vals = [float(v) * scale for v in vals]
        last20 = vals[-20:]
        tes_mean = sum(last20) / len(last20)
        last10 = vals[-10:]
        prev10 = vals[-20:-10] if len(vals) >= 20 else []
        if prev10:
            vel = (sum(last10) / len(last10)) - (sum(prev10) / len(prev10))
        else:
            vel = 0.0
        return float(tes_mean), float(vel)
    except Exception:
        return None, None


def _decide_overrides(hb: dict, tes_mean: Optional[float], vel: Optional[float], include_sched_default: bool) -> dict:
    # Defaults
    nav_int = 3
    nav_hot = 90
    nav_cool = 20
    nav_pause = 90
    sched_int = 180
    include_sched = include_sched_default

    # System heuristics
    metrics = hb.get('metrics', {}) if isinstance(hb, dict) else {}
    cpu = float(metrics.get('cpu_pct', 0) or 0)
    mem = float(metrics.get('mem_used_pct', 0) or 0)
    gpu_util = None
    try:
        gpu = metrics.get('gpu') or {}
        g0 = (gpu.get('gpus') or [{}])[0]
        gpu_util = float(g0.get('util_pct')) if g0 and g0.get('util_pct') is not None else None
    except Exception:
        gpu_util = None

    system_hot = (cpu >= 85.0) or (mem >= 90.0) or (gpu_util is not None and gpu_util >= 80.0)
    system_cool = (cpu <= 50.0) and (mem <= 80.0) and (gpu_util is None or gpu_util <= 40.0)

    # TES-driven nudges
    good_tes = (tes_mean is not None and tes_mean >= 0.85)
    improving = (vel is not None and vel > 0)

    # Super-cool: aggressively speed up when the system is very free and TES still has room to grow
    super_cool = (cpu <= 35.0) and (mem <= 70.0) and (gpu_util is None or gpu_util <= 30.0)

    # GPU-aware workload adjustment
    # If GPU has headroom but CPU/Mem are stressed, suggest offloading LLM work to GPU
    gpu_headroom_pct = (100.0 - gpu_util) if gpu_util is not None else 100.0
    
    # Add note about GPU utilization for transparency
    gpu_note = ""
    if gpu_util is not None:
        if gpu_headroom_pct > 50.0 and cpu >= 75.0:
            gpu_note = "gpu_underutilized"
        elif gpu_util >= 70.0:
            gpu_note = "gpu_saturated"

    if system_hot:
        nav_int = 5
        nav_hot = 120
        nav_cool = 30
        nav_pause = 120
        sched_int = 240
    elif super_cool:
        nav_int = 2
        nav_hot = 80
        nav_cool = 12
        nav_pause = 80
        # If TES < 0.9, push the scheduler harder to increase training cadence
        sched_int = 90 if (tes_mean is not None and tes_mean < 0.9) else 120
    elif system_cool and (good_tes or improving):
        nav_int = 2
        nav_hot = 90
        nav_cool = 15
        nav_pause = 90
        sched_int = 120

    overrides = {
        'navigator': {
            'interval': nav_int,
            'control': False,  # control on Windows still gated by policy/supervisor
            'pause_sec': nav_pause,
            'hot_interval': nav_hot,
            'cool_interval': nav_cool,
        },
        'scheduler': {
            'interval': sched_int,
            'include': include_sched,
        }
    }
    return overrides


def _write_overrides(ovr: dict, dry_run: bool) -> bool:
    TUNING.mkdir(parents=True, exist_ok=True)
    if dry_run:
        _print(f"[dry-run] would write overrides: {json.dumps(ovr)}")
        return False
    try:
        # Avoid rewriting if unchanged
        old = {}
        if OVERRIDES.exists():
            try:
                old = json.loads(OVERRIDES.read_text(encoding='utf-8'))
            except Exception:
                old = {}
        if old != ovr:
            OVERRIDES.write_text(json.dumps(ovr, ensure_ascii=False, indent=2), encoding='utf-8')
            _print("overrides updated")
            return True
        return False
    except Exception:
        return False


def _active_teaching_count(ttl_sec: int = 3600) -> int:
    try:
        TEACH_DIR.mkdir(parents=True, exist_ok=True)
        now = time.time()
        cnt = 0
        for p in TEACH_DIR.glob('teach_*.lock'):
            try:
                if (now - p.stat().st_mtime) <= ttl_sec:
                    cnt += 1
            except Exception:
                pass
        return cnt
    except Exception:
        return 0


def _load_state() -> dict:
    try:
        if STATE.exists():
            return json.loads(STATE.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {}


def _save_state(d: dict) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


def _should_teach(now: float, st: dict, teach_interval_sec: int, hb: dict, tes_mean: Optional[float]) -> bool:
    last = float(st.get('last_teach_ts', 0) or 0)
    if (now - last) < teach_interval_sec:
        return False
    if not LOCK_LLM_READY.exists():
        return False
    metrics = hb.get('metrics', {}) if isinstance(hb, dict) else {}
    cpu = float(metrics.get('cpu_pct', 0) or 0)
    mem = float(metrics.get('mem_used_pct', 0) or 0)
    gpu_util = None
    try:
        gpu = metrics.get('gpu') or {}
        g0 = (gpu.get('gpus') or [{}])[0]
        gpu_util = float(g0.get('util_pct')) if g0 and g0.get('util_pct') is not None else None
    except Exception:
        gpu_util = None
    system_cool = (cpu <= 60.0) and (mem <= 85.0) and (gpu_util is None or gpu_util <= 50.0)
    tes_ok = (tes_mean is None) or (tes_mean >= 0.8)
    return system_cool and tes_ok


def _run_teaching_cycle() -> None:
    # Run CP6 then CP7 as detached one-shots (prefer WSL when ready)
    try:
        if _is_wsl_ready():
            _spawn_detached_wsl('tools/cp6_sociologist.py', ['--interval', '1', '--max-iters', '30'])
            _spawn_detached_wsl('tools/cp7_chronicler.py', ['--interval', '1', '--max-iters', '10', '--quiet'])
        else:
            _spawn_detached_win('tools/cp6_sociologist.py', ['--interval', '1', '--max-iters', '30'])
            _spawn_detached_win('tools/cp7_chronicler.py', ['--interval', '1', '--max-iters', '10', '--quiet'])
        _print('teaching cycle started (CP6 -> CP7)')
    except Exception:
        pass
    # Drop a short-lived lock to account for concurrency
    try:
        TEACH_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime('%Y%m%d_%H%M%S')
        (TEACH_DIR / f'teach_{ts}.lock').write_text('ok', encoding='utf-8')
    except Exception:
        pass


def run_loop(interval: float, dry_run: bool, enable_teaching: bool, teach_interval_mins: int, force_teach: bool = False) -> None:
    st = _load_state()
    pol = _policy()
    # include scheduler only when CBO policy grants authority
    include_sched_default = bool(pol.get('granted'))
    # Teaching policy gates cycles regardless of flags
    feat = (pol.get('features') or {}).get('teaching_cycles') or {}
    policy_teaching_enabled = bool(feat.get('enabled'))
    max_parallel = int(feat.get('max_parallel', 1) or 1)
    teach_interval_sec = int(teach_interval_mins * 60)
    while True:
        hb = _read_cbo_telemetry()
        tes_mean, vel = _recent_metrics()
        ovr = _decide_overrides(hb, tes_mean, vel, include_sched_default)
        changed = _write_overrides(ovr, dry_run)
        if dry_run:
            _print(f"[dry-run] tes_mean={tes_mean} vel={vel} overrides={ovr}")
        else:
            if changed:
                _print(f"applied overrides: tes_mean={tes_mean} vel={vel}")
        # Forced teaching for test: ignore policy and cool/TES conditions, but still require LLM ready and respect max_parallel
        if force_teach and not dry_run:
            if not LOCK_LLM_READY.exists():
                _print('teaching test skipped (LLM not ready)')
            elif _active_teaching_count() >= max_parallel:
                _print('teaching test skipped (max_parallel reached)')
            else:
                _run_teaching_cycle()
                st['last_teach_ts'] = time.time()
                _save_state(st)
                _print('teaching test cycle launched')
                force_teach = False  # one-shot
        # Adaptive teach interval: shorten when super cool and TES below target; lengthen when hot
        cpu = float((hb.get('metrics') or {}).get('cpu_pct', 0) or 0)
        mem = float((hb.get('metrics') or {}).get('mem_used_pct', 0) or 0)
        gpu_util = None
        try:
            g0 = (((hb.get('metrics') or {}).get('gpu') or {}).get('gpus') or [{}])[0]
            gpu_util = float(g0.get('util_pct')) if g0 and g0.get('util_pct') is not None else None
        except Exception:
            gpu_util = None
        super_cool = (cpu <= 35.0) and (mem <= 70.0) and (gpu_util is None or gpu_util <= 30.0)
        system_hot = (cpu >= 85.0) or (mem >= 90.0) or (gpu_util is not None and gpu_util >= 80.0)
        teach_interval_eff = teach_interval_sec
        if super_cool and (tes_mean is not None and tes_mean < 0.9):
            teach_interval_eff = min(teach_interval_eff, 10 * 60)  # 10 minutes when very free and needs improvement
        elif system_hot:
            teach_interval_eff = max(teach_interval_eff, 40 * 60)  # defer when hot

        if (enable_teaching or policy_teaching_enabled) and _should_teach(time.time(), st, teach_interval_eff, hb, tes_mean):
            # Concurrency guard from policy
            if _active_teaching_count() >= max_parallel:
                if dry_run:
                    _print('[dry-run] teaching skipped (max_parallel reached)')
                else:
                    _print('teaching skipped (max_parallel reached)')
                time.sleep(max(30.0, float(interval)))
                continue
            if not dry_run:
                _run_teaching_cycle()
                st['last_teach_ts'] = time.time()
                _save_state(st)
            else:
                _print('[dry-run] would start teaching cycle (CP6 -> CP7)')
        # Burst: if super cool and TES below target, attempt to utilize remaining capacity (start one extra cycle this iteration)
        if (enable_teaching or policy_teaching_enabled) and not dry_run and super_cool and (tes_mean is not None and tes_mean < 0.9):
            cur = _active_teaching_count()
            if cur < max_parallel and LOCK_LLM_READY.exists():
                _run_teaching_cycle()
                st['last_teach_ts'] = time.time()
                _save_state(st)
                _print('teaching burst: launched additional cycle to utilize free capacity')
        time.sleep(max(30.0, float(interval)))


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description='CBO Optimizer')
    ap.add_argument('--interval', type=float, default=120.0, help='Seconds between optimizer iterations (default 120)')
    ap.add_argument('--dry-run', action='store_true', help='Print decisions; do not write overrides or start cycles')
    ap.add_argument('--once', action='store_true', help='Run one iteration and exit (honors dry-run)')
    ap.add_argument('--enable-teaching', action='store_true', help='Enable teaching/self-discipline cycles (CP6/CP7)')
    ap.add_argument('--teach-interval-mins', type=int, default=30, help='Minimum minutes between teaching cycles (default 30)')
    ap.add_argument('--force-teach', action='store_true', help='TEST: trigger a teaching cycle immediately (ignores policy/cool/TES, requires LLM ready; respects max_parallel)')
    args = ap.parse_args(argv)

    if args.once:
        hb = _read_cbo_telemetry()
        tes_mean, vel = _recent_metrics()
        pol = _policy()
        include_sched_default = bool(pol.get('granted'))
        feat = (pol.get('features') or {}).get('teaching_cycles') or {}
        policy_teaching_enabled = bool(feat.get('enabled'))
        max_parallel = int(feat.get('max_parallel', 1) or 1)
        ovr = _decide_overrides(hb, tes_mean, vel, include_sched_default)
        _write_overrides(ovr, args.dry_run)
        # Forced teaching for test
        if args.force_teach and not args.dry_run:
            if not LOCK_LLM_READY.exists():
                _print('teaching test skipped (LLM not ready)')
            elif _active_teaching_count() >= max_parallel:
                _print('teaching test skipped (max_parallel reached)')
            else:
                _run_teaching_cycle()
                st = _load_state()
                st['last_teach_ts'] = time.time()
                _save_state(st)
                _print('teaching test cycle launched')
        if (args.enable_teaching or policy_teaching_enabled) and not args.dry_run:
            if _active_teaching_count() < max_parallel and _should_teach(time.time(), _load_state(), int(args.teach_interval_mins*60), hb, tes_mean):
                _run_teaching_cycle()
                st = _load_state()
                st['last_teach_ts'] = time.time()
                _save_state(st)
            else:
                _print('teaching skipped (policy disabled, max_parallel reached, or conditions not met)')
        if args.dry_run:
            _print(f"[dry-run] once: tes_mean={tes_mean} vel={vel} overrides={ovr}")
        return 0

    _print('starting optimizer loop')
    run_loop(interval=float(args.interval), dry_run=bool(args.dry_run), enable_teaching=bool(args.enable_teaching), teach_interval_mins=int(args.teach_interval_mins), force_teach=bool(args.force_teach))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
