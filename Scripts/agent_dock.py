r"""Agent1 Status Dock — slim always-on-top bar.

Shows a compact state dot, status message, and goal preview. Designed to be
minimally obtrusive and readable. Intended as a companion to the watcher.

Usage:
  python -u .\Scripts\agent_dock.py [--top] [--theme calm|neon|retro] [--sound]
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

THEMES = {
    "calm": {"bg": "#f6f8fa", "fg": "#24292f", "running": "#1f6feb", "done": "#238636", "error": "#d1242f", "idle": "#6e7681"},
    "neon": {"bg": "#0d1117", "fg": "#c9d1d9", "running": "#58a6ff", "done": "#3fb950", "error": "#ff7b72", "idle": "#8b949e"},
    "retro": {"bg": "#fff8dc", "fg": "#2c241b", "running": "#1e90ff", "done": "#2e8b57", "error": "#b22222", "idle": "#8b8878"},
}


def _read_hb() -> Optional[Dict[str, Any]]:
    try:
        return json.loads(LOCK.read_text(encoding="utf-8"))
    except Exception:
        return None


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Agent1 top bar dock")
    ap.add_argument("--top", action="store_true", help="Keep on top")
    ap.add_argument("--theme", choices=list(THEMES.keys()), default="calm")
    ap.add_argument("--sound", action="store_true", help="Beep on done/error")
    args = ap.parse_args(argv)

    try:
        import tkinter as tk
    except Exception:
        print("Dock requires Tkinter.")
        return 2

    palette = THEMES[args.theme]
    win = tk.Tk()
    win.title("Agent1 Dock")
    if args.top:
        win.attributes("-topmost", True)
    try:
        win.configure(bg=palette["bg"])
    except Exception:
        pass
    # A slim fixed-height bar
    win.geometry("620x48")
    frm = tk.Frame(win, bg=palette["bg"])
    frm.pack(fill=tk.BOTH, expand=True)

    dot = tk.Label(frm, text="●", fg=palette["idle"], bg=palette["bg"], font=("Segoe UI", 16, "bold"))
    dot.pack(side=tk.LEFT, padx=(10, 8))
    msg = tk.Label(frm, text="", fg=palette["fg"], bg=palette["bg"], anchor="w", font=("Segoe UI", 11, "bold"))
    msg.pack(side=tk.LEFT, padx=(0, 8))
    gp = tk.Label(frm, text="", fg=palette["fg"], bg=palette["bg"], anchor="w", font=("Segoe UI", 10))
    gp.pack(side=tk.LEFT, fill=tk.X, expand=True)

    last_status: Optional[str] = None

    def _tick():
        nonlocal last_status
        hb = _read_hb() or {}
        status = str(hb.get("status", "idle"))
        status_color = palette.get(status, palette["idle"]) if isinstance(status, str) else palette["idle"]
        dot.configure(fg=status_color)
        sm = hb.get("status_message") or hb.get("goal_preview") or ""
        msg.configure(text=sm[:80])
        gp.configure(text=(hb.get("goal_preview") or "")[:120])
        if args.sound and last_status != status and status in ("done", "error"):
            try:
                if os.name == "nt":
                    import winsound
                    winsound.Beep(880 if status == "done" else 440, 200)
                else:
                    print("\a", end="")
            except Exception:
                pass
        last_status = status
        win.after(300, _tick)

    _tick()
    win.resizable(False, False)
    win.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
