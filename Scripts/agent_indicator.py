r"""Agent1 Indicator — a tiny animated window that mirrors agent1.lock.

Shows a playful ascii/emoticon animation while status is running and brief
summary text (goal preview + time since update). Auto-closes a few seconds
after done/error when --auto-close is provided.

Usage:
  python -u .\Scripts\agent_indicator.py [--interval 120] [--auto-close] [--top] [--scale 1.0]

Notes:
- Reads outgoing/agent1.lock (JSON heartbeat written by agent_console / agent_runner)
- Minimal, dependency-free; falls back to console animation if Tk is unavailable
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOCK = OUT / "agent1.lock"

# Theme presets (simple)
THEMES = {
    "calm": {"bg": "#f6f8fa", "fg": "#24292f", "running": "#1f6feb", "done": "#238636", "error": "#d1242f", "idle": "#6e7681"},
    "neon": {"bg": "#0d1117", "fg": "#c9d1d9", "running": "#58a6ff", "done": "#3fb950", "error": "#ff7b72", "idle": "#8b949e"},
    "retro": {"bg": "#fff8dc", "fg": "#2c241b", "running": "#1e90ff", "done": "#2e8b57", "error": "#b22222", "idle": "#8b8878"},
}
DEFAULT_THEME = "calm"

# Emoticon frames (simple but friendly)
FRAMES = [
    "ᗧ···ᗣ",
    "ᗧ· ·ᗣ",
    "ᗧ···ᗣ",
    "ᗧ· ·ᗣ",
]


def _ago(ts: Optional[float]) -> str:
    if not ts:
        return "—"
    d = max(0.0, time.time() - float(ts))
    if d < 1:
        return f"{int(d*1000)} ms"
    if d < 60:
        return f"{int(d)} s"
    m = int(d // 60)
    s = int(d % 60)
    return f"{m}m {s}s"


def _read_hb() -> Optional[Dict[str, Any]]:
    try:
        return json.loads(LOCK.read_text(encoding="utf-8"))
    except Exception:
        return None


# --- Console fallback ---

def _run_console(interval: int = 120, auto_close: bool = False) -> int:
    i = 0
    quiet_cycles_after_done = 0
    while True:
        hb = _read_hb()
        status = (hb or {}).get("status", "idle")
        run_dir = (hb or {}).get("run_dir")
        frame = FRAMES[i % len(FRAMES)] if status == "running" else ("✔" if status == "done" else ("!" if status == "error" else "·"))
        gp = (hb or {}).get("goal_preview") or ""
        ago = _ago((hb or {}).get("ts"))
        line = f"\r{frame}  {status:<7}  {ago:<8}  {gp[:48]:<48}"
        print(line, end="", flush=True)
        if auto_close and status in ("done", "error"):
            quiet_cycles_after_done += 1
            if quiet_cycles_after_done >= max(1, 150 // max(1, interval)):
                print("\n", end="")
                return 0
        i += 1
        time.sleep(max(0.02, interval / 1000.0))


# --- Tk GUI ---

def _run_tk(interval: int = 120, auto_close: bool = False, top: bool = False, scale: float = 1.0, theme: str = DEFAULT_THEME, sound: bool = False) -> int:
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        return _run_console(interval=interval, auto_close=auto_close)

    win = tk.Tk()
    win.title("Agent1 Indicator")
    if top:
        win.attributes("-topmost", True)
    palette = THEMES.get(theme, THEMES[DEFAULT_THEME])
    try:
        win.configure(bg=palette["bg"])
    except Exception:
        pass

    font_base = int(18 * max(0.6, min(2.0, scale)))

    frame_lbl = tk.Label(win, text="", font=("Consolas", font_base, "bold"))
    frame_lbl.pack(padx=12, pady=(10, 2))

    status_lbl = tk.Label(win, text="", font=("Segoe UI", int(font_base * 0.6)))
    status_lbl.pack(padx=12, pady=2)

    details_lbl = tk.Label(win, text="", font=("Segoe UI", int(font_base * 0.5)))
    details_lbl.pack(padx=12, pady=2)

    btn = ttk.Button(win, text="Open artifacts", state=tk.DISABLED)
    btn.pack(padx=12, pady=(2, 10))

    # Progress bar (phase-based approximation)
    pbar = ttk.Progressbar(win, orient="horizontal", mode="determinate", length=260)
    pbar.pack(padx=12, pady=(0, 10))

    i = 0
    done_ticks = 0
    last_status: Optional[str] = None

    def _tick():
        nonlocal i, done_ticks
        hb = _read_hb()
        status = (hb or {}).get("status", "idle")
        phase = (hb or {}).get("phase", "—")
        ts = (hb or {}).get("ts")
        gp = (hb or {}).get("goal_preview") or ""
        run_dir = (hb or {}).get("run_dir")
        ago = _ago(ts)
        # progress approximation and optional plan length
        progress_map = {"planning": 10, "planning_done": 25, "apply": 60, "testing": 85, "done": 100, "error": 100}
        pbar["value"] = progress_map.get(str(phase), 0)
        steps_info = ""
        try:
            if run_dir:
                p = Path(run_dir)
                if not p.is_absolute():
                    p = ROOT / p
                plan_file = p / "plan.json"
                if plan_file.exists():
                    obj = json.loads(plan_file.read_text(encoding="utf-8", errors="ignore"))
                    steps = obj.get("steps", [])
                    if isinstance(steps, list):
                        steps_info = f" • steps: {len(steps)}"
        except Exception:
            pass
        # animation while running
        if status == "running":
            frame_lbl.config(text=FRAMES[i % len(FRAMES)])
            i += 1
        elif status == "done":
            frame_lbl.config(text="✔")
            done_ticks += 1
        elif status == "error":
            frame_lbl.config(text="!")
            done_ticks += 1
        else:
            frame_lbl.config(text="·")
            done_ticks = 0
        status_lbl.config(text=f"{phase} — {status} — {ago} ago{steps_info}")
        details_lbl.config(text=gp[:80])
        if run_dir:
            p = Path(run_dir)
            if not p.is_absolute():
                p = ROOT / p
            btn.state(["!disabled"])  # type: ignore[attr-defined]
            btn.configure(command=lambda pp=p: os.startfile(str(pp)))  # type: ignore[attr-defined]
        else:
            btn.state(["disabled"])  # type: ignore[attr-defined]
        # Optional sound cue on status change
        nonlocal last_status
        if sound and last_status != status and status in ("done", "error"):
            try:
                if os.name == "nt":
                    import winsound
                    freq = 880 if status == "done" else 440
                    winsound.Beep(freq, 200)
                else:
                    print("\a", end="")
            except Exception:
                pass
        last_status = status
        # auto-close a few seconds after done/error
        if auto_close and status in ("done", "error") and done_ticks >= max(1, int(2500 / max(1, interval))):
            win.destroy()
            return
        win.after(interval, _tick)

    _tick()
    win.resizable(False, False)
    win.mainloop()
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Animated indicator for Agent1 heartbeats")
    ap.add_argument("--interval", type=int, default=120, help="Frame/update interval in ms (default 120)")
    ap.add_argument("--auto-close", action="store_true", help="Close a few seconds after done/error")
    ap.add_argument("--top", action="store_true", help="Always keep on top")
    ap.add_argument("--scale", type=float, default=1.0, help="UI scale multiplier (0.6-2.0)")
    ap.add_argument("--theme", choices=list(THEMES.keys()), default=DEFAULT_THEME, help="Theme preset")
    ap.add_argument("--sound", action="store_true", help="Play a short tone on done/error")
    args = ap.parse_args(argv)

    return _run_tk(interval=args.interval, auto_close=args.auto_close, top=args.top, scale=args.scale, theme=args.theme, sound=args.sound)


if __name__ == "__main__":
    raise SystemExit(main())
