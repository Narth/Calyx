#!/usr/bin/env python3
"""
Teaching Dashboard — CBO training/teaching telemetry at a glance.

Shows:
- Policy: teaching_cycles.enabled, max_parallel, interval default
- Teaching activity: active count, last teach time
- TES trend (mean of last 20; velocity = last10 - prev10)
- Current overrides: navigator/scheduler knobs from outgoing/tuning/supervisor_overrides.json

Usage:
  python -u Scripts/teaching_dashboard.py --once    # one-shot console
  python -u Scripts/teaching_dashboard.py --top     # small Tk window if available

Stdlib only. Falls back to console when Tk is unavailable.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outgoing'
LOGS = ROOT / 'logs'
STATE = ROOT / 'state'
POLICIES = OUT / 'policies'
TUNING = OUT / 'tuning'
TEACH_DIR = OUT / 'teaching'
CAPACITY = OUT / 'capacity.flags.json'

POLICY_PATH = POLICIES / 'cbo_permissions.json'
STATE_OPT = STATE / 'cbo_optimizer_state.json'
OVERRIDES = TUNING / 'supervisor_overrides.json'

THEMES = {
    'calm': {'bg': '#f6f8fa', 'fg': '#24292f', 'dim': '#6e7681', 'ok': '#238636', 'warn': '#9a6700'},
    'neon': {'bg': '#0d1117', 'fg': '#c9d1d9', 'dim': '#8b949e', 'ok': '#3fb950', 'warn': '#d29922'},
}


def _read_json(p: Path) -> Dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _policy() -> Dict[str, Any]:
    return _read_json(POLICY_PATH)


def _optimizer_state() -> Dict[str, Any]:
    return _read_json(STATE_OPT)


def _overrides() -> Dict[str, Any]:
    return _read_json(OVERRIDES)


def _active_teaching_count(ttl_sec: int = 3600) -> int:
    try:
        now = time.time()
        TEACH_DIR.mkdir(parents=True, exist_ok=True)
        return sum(1 for p in TEACH_DIR.glob('teach_*.lock') if (now - p.stat().st_mtime) <= ttl_sec)
    except Exception:
        return 0


def _last_teach_ago(st: Dict[str, Any]) -> str:
    ts = float(st.get('last_teach_ts', 0) or 0)
    if not ts:
        return '—'
    d = time.time() - ts
    if d < 60:
        return f"{int(d)}s"
    m = int(d // 60)
    s = int(d % 60)
    return f"{m}m {s}s"


def _tes_stats() -> Tuple[Optional[float], Optional[float]]:
    path = LOGS / 'agent_metrics.csv'
    if not path.exists():
        return None, None
    try:
        rows = []
        with path.open('r', encoding='utf-8', newline='') as f:
            rdr = csv.DictReader(f)
            for r in rdr:
                rows.append(r)
        def fval(r, keys):
            for k in keys:
                if k in r and r[k] not in (None, ''):
                    try:
                        return float(r[k])
                    except Exception:
                        pass
            return None
        vals = [fval(r, ['TES','tes','tes_score']) for r in rows]
        vals = [v for v in vals if isinstance(v, (float,int))]
        if not vals:
            return None, None
        scale = 1.0
        try:
            if max(vals) > 2.0:
                scale = 0.01
        except Exception:
            scale = 1.0
        vals = [float(v)*scale for v in vals]
        last20 = vals[-20:]
        mean20 = sum(last20)/len(last20)
        last10 = vals[-10:]
        prev10 = vals[-20:-10] if len(vals)>=20 else []
        vel = (sum(last10)/len(last10) - sum(prev10)/len(prev10)) if prev10 else 0.0
        return float(mean20), float(vel)
    except Exception:
        return None, None


def _compose_status() -> Dict[str, Any]:
    pol = _policy()
    feat = (pol.get('features') or {}).get('teaching_cycles') or {}
    enabled = bool(feat.get('enabled'))
    max_parallel = int(feat.get('max_parallel', 1) or 1)
    default_mins = int(feat.get('interval_minutes_default', 30) or 30)
    st = _optimizer_state()
    count = _active_teaching_count()
    ago = _last_teach_ago(st)
    ovr = _overrides()
    tes_mean, vel = _tes_stats()
    cap = _read_json(CAPACITY)
    return {
        'teaching_enabled': enabled,
        'max_parallel': max_parallel,
        'default_interval_mins': default_mins,
        'active_teaching': count,
        'last_teach_ago': ago,
        'tes_mean': tes_mean,
        'tes_velocity': vel,
        'overrides': ovr,
        'capacity': cap,
    }


def _console_once() -> int:
    s = _compose_status()
    ovr = s.get('overrides') or {}
    nav = (ovr.get('navigator') or {})
    sch = (ovr.get('scheduler') or {})
    print(json.dumps({k: v for k, v in s.items() if k != 'overrides'}, indent=2))
    print("overrides:")
    print(json.dumps({'navigator': nav, 'scheduler': sch}, indent=2))
    return 0


def _run_tk(interval_ms: int, top: bool, scale: float, theme: str) -> int:
    try:
        import tkinter as tk
    except Exception:
        return _console_once()
    palette = THEMES.get(theme, THEMES['calm'])
    win = tk.Tk()
    win.title('Teaching Dashboard')
    if top:
        try:
            win.attributes('-topmost', True)
        except Exception:
            pass
    try:
        win.configure(bg=palette['bg'])
    except Exception:
        pass
    font_base = int(18 * max(0.6, min(2.0, scale)))
    lbl_title = tk.Label(win, text='Teaching Dashboard', font=('Segoe UI', font_base, 'bold'), fg=palette['fg'], bg=palette['bg'])
    lbl_title.pack(padx=12, pady=(10, 6))
    lbl_policy = tk.Label(win, text='', font=('Consolas', int(font_base*0.6)), fg=palette['fg'], bg=palette['bg'], justify='left')
    lbl_policy.pack(padx=12, pady=4, anchor='w')
    lbl_teach = tk.Label(win, text='', font=('Consolas', int(font_base*0.6)), fg=palette['fg'], bg=palette['bg'], justify='left')
    lbl_teach.pack(padx=12, pady=4, anchor='w')
    lbl_tes = tk.Label(win, text='', font=('Consolas', int(font_base*0.6)), fg=palette['fg'], bg=palette['bg'], justify='left')
    lbl_tes.pack(padx=12, pady=4, anchor='w')
    lbl_ovr = tk.Label(win, text='', font=('Consolas', int(font_base*0.55)), fg=palette['dim'], bg=palette['bg'], justify='left')
    lbl_ovr.pack(padx=12, pady=(4, 10), anchor='w')
    lbl_cap = tk.Label(win, text='', font=('Consolas', int(font_base*0.55)), fg=palette['dim'], bg=palette['bg'], justify='left')
    lbl_cap.pack(padx=12, pady=(0, 10), anchor='w')

    def tick():
        s = _compose_status()
        lbl_policy.config(text=f"Policy: enabled={s['teaching_enabled']} max_parallel={s['max_parallel']} default_interval={s['default_interval_mins']}m")
        lbl_teach.config(text=f"Teaching: active={s['active_teaching']} last={s['last_teach_ago']}")
        tm = s.get('tes_mean')
        tv = s.get('tes_velocity')
        tm_s = '—' if tm is None else f"{tm:.2f}"
        tv_s = '—' if tv is None else f"{tv:+.3f}"
        lbl_tes.config(text=f"TES: mean20={tm_s} velocity={tv_s}")
        ovr = s.get('overrides') or {}
        nav = (ovr.get('navigator') or {})
        sch = (ovr.get('scheduler') or {})
        lbl_ovr.config(text=f"Overrides → nav: interval={nav.get('interval','?')} hot={nav.get('hot_interval','?')} cool={nav.get('cool_interval','?')} pause={nav.get('pause_sec','?')}  |  scheduler: include={sch.get('include','?')} interval={sch.get('interval','?')}")
        cap = s.get('capacity') or {}
        lbl_cap.config(text=f"Capacity → score={cap.get('score','?')} cpu_ok={cap.get('cpu_ok','?')} mem_ok={cap.get('mem_ok','?')} gpu_ok={cap.get('gpu_ok','?')} super_cool={cap.get('super_cool','?')} verified={cap.get('verified','?')}")
        win.after(max(250, interval_ms), tick)

    tick()
    win.resizable(False, False)
    win.mainloop()
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description='Teaching Dashboard')
    ap.add_argument('--once', action='store_true', help='Print one-shot summary and exit')
    ap.add_argument('--interval', type=int, default=1000, help='GUI update interval in ms (default 1000)')
    ap.add_argument('--top', action='store_true', help='Keep window on top')
    ap.add_argument('--scale', type=float, default=1.0, help='UI scale (0.6-2.0)')
    ap.add_argument('--theme', choices=list(THEMES.keys()), default='calm', help='Theme preset')
    args = ap.parse_args(argv)
    if args.once:
        return _console_once()
    return _run_tk(interval_ms=args.interval, top=args.top, scale=args.scale, theme=args.theme)


if __name__ == '__main__':
    raise SystemExit(main())
