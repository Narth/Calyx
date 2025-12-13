r"""CBO Indicator — a tiny window that mirrors bridge.lock (Calyx Bridge Overseer).

Shows an animated glyph while CBO is busy and a compact status line with:
- bridge phase/status and age
- queue size and current item (if any)
- last 1-2 lines from CBO dialog

Usage:
  python -u .\Scripts\cbo_indicator.py [--interval 120] [--top] [--scale 1.0] [--theme calm] [--sound]
  python -u .\Scripts\cbo_indicator.py --once   # one-shot console read (for tests/CI)

Notes:
- Reads outgoing/bridge.lock for status. Queue under outgoing/bridge/user_goals/*.txt
- Shows tail of outgoing/bridge/dialog.log when present.
- Minimal, dependency-free; falls back to console animation if Tk is unavailable.
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
BRIDGE_LOCK = OUT / "bridge.lock"
CBO_DIR = OUT / "bridge"
CBO_DIALOG = CBO_DIR / "dialog.log"
CBO_GOALS = CBO_DIR / "user_goals"

THEMES = {
    "calm": {"bg": "#f6f8fa", "fg": "#24292f", "running": "#1f6feb", "done": "#238636", "error": "#d1242f", "idle": "#6e7681"},
    "neon": {"bg": "#0d1117", "fg": "#c9d1d9", "running": "#58a6ff", "done": "#3fb950", "error": "#ff7b72", "idle": "#8b949e"},
    "retro": {"bg": "#fff8dc", "fg": "#2c241b", "running": "#1e90ff", "done": "#2e8b57", "error": "#b22222", "idle": "#8b8878"},
}
DEFAULT_THEME = "calm"

FRAMES = [
    "🌉⋯", "🌉·", "🌉⋯", "🌉·",
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


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _hb() -> Dict[str, Any]:
    d = _read_json(BRIDGE_LOCK) or {}
    if not isinstance(d, dict):
        d = {}
    return d


def _queue_size() -> int:
    try:
        return len(list(CBO_GOALS.glob("goal_*.txt")))
    except Exception:
        return 0


def _dialog_tail(nchars: int = 160) -> str:
    try:
        if not CBO_DIALOG.exists():
            return ""
        data = CBO_DIALOG.read_text(encoding="utf-8", errors="ignore")
        data = data.replace("\r\n", "\n")
        tail = data[-nchars:]
        # last line(s)
        return tail.splitlines()[-2:].join(" ") if tail else ""
    except Exception:
        return ""


# --- Console mode (one-shot or looping if Tk not available) ---

def _run_console(interval: int = 120, once: bool = False) -> int:
    i = 0
    while True:
        d = _hb()
        status = str(d.get("status", "idle"))
        phase = str(d.get("phase", "tests"))
        ts = d.get("ts")
        q = _queue_size()
        # consider busy if status running or queue pending
        busy = status == "running" or q > 0
        frame = FRAMES[i % len(FRAMES)] if busy else ("✔" if status == "done" else ("!" if status == "error" else "·"))
        ago = _ago(ts)
        cur = str(d.get("status_message") or "")[:60]
        line = f"\r{frame}  {phase}/{status:<7}  {ago:<8}  q={q}  {cur:<60}"
        print(line, end="", flush=True)
        if once:
            print("\n", end="")
            return 0
        i += 1
        time.sleep(max(0.02, interval / 1000.0))


# --- Tk GUI ---

def _run_tk(interval: int = 120, top: bool = False, scale: float = 1.0, theme: str = DEFAULT_THEME, sound: bool = False) -> int:
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        return _run_console(interval=interval, once=False)

    win = tk.Tk()
    win.title("CBO Indicator")
    if top:
        try:
            win.attributes("-topmost", True)
        except Exception:
            pass
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

    btn = ttk.Button(win, text="Open CBO folder", state=tk.DISABLED)
    btn.pack(padx=12, pady=(2, 10))

    pbar = ttk.Progressbar(win, orient="horizontal", mode="determinate", length=260)
    pbar.pack(padx=12, pady=(0, 10))

    i = 0
    last_state: Optional[str] = None

    def _tick():
        nonlocal i, last_state
        d = _hb()
        status = str(d.get("status", "idle"))
        phase = str(d.get("phase", "tests"))
        ts = d.get("ts")
        msg = str(d.get("status_message") or "")
        q = _queue_size()
        busy = status == "running" or q > 0
        # progress hint: if busy and q>0, show mid-progress; done/error=100
        progress_map = {"tests": 30, "apply": 60, "done": 100, "error": 100}
        pbar["value"] = 70 if (busy and q > 0 and status != "done" and status != "error") else progress_map.get(phase, 0)
        # animate or static glyph
        if busy:
            frame_lbl.config(text=FRAMES[i % len(FRAMES)])
            i += 1
        else:
            frame_lbl.config(text="✔" if status == "done" else ("!" if status == "error" else "·"))
        # text lines
        ago = _ago(ts)
        status_lbl.config(text=f"{phase} — {status} — {ago} ago — q={q}")
        tail = _dialog_tail(160)
        details_lbl.config(text=(msg or tail)[:140])
        # open button
        try:
            CBO_DIR.mkdir(parents=True, exist_ok=True)
            btn.state(["!disabled"])  # type: ignore[attr-defined]
            if os.name == "nt":
                btn.configure(command=lambda: os.startfile(str(CBO_DIR)))  # type: ignore[attr-defined]
            else:
                btn.configure(command=lambda: os.system(f"xdg-open '{CBO_DIR}'"))
        except Exception:
            btn.state(["disabled"])  # type: ignore[attr-defined]
        # optional sound
        if sound and last_state != status and status in ("done", "error"):
            try:
                if os.name == "nt":
                    import winsound
                    winsound.Beep(880 if status == "done" else 440, 200)
                else:
                    print("\a", end="")
            except Exception:
                pass
        last_state = status
        win.after(interval, _tick)

    _tick()
    win.resizable(False, False)
    win.mainloop()
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Indicator for CBO (bridge.lock)")
    ap.add_argument("--interval", type=int, default=120, help="Update interval in ms (default 120)")
    ap.add_argument("--top", action="store_true", help="Always keep on top")
    ap.add_argument("--scale", type=float, default=1.0, help="UI scale multiplier (0.6-2.0)")
    ap.add_argument("--theme", choices=list(THEMES.keys()), default=DEFAULT_THEME, help="Theme preset")
    ap.add_argument("--sound", action="store_true", help="Play a short tone on done/error")
    ap.add_argument("--once", action="store_true", help="Console one-shot (no GUI), prints a single status line and exits")
    args = ap.parse_args(argv)

    if args.once:
        return _run_console(interval=args.interval, once=True)
    return _run_tk(interval=args.interval, top=args.top, scale=args.scale, theme=args.theme, sound=args.sound)


if __name__ == "__main__":
    raise SystemExit(main())
