#!/usr/bin/env python3
"""
Console Tasks Board for Calyx Terminal.

Reads outgoing/tasks_dashboard.json and prints a compact dashboard.
Optional watch mode to refresh periodically.

Usage:
  python -u Scripts/tasks_board.py
  python -u Scripts/tasks_board.py --watch 3 --regen
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(ROOT, 'outgoing', 'tasks_dashboard.json')
GEN_SCRIPT = os.path.join(ROOT, 'tools', 'generate_task_dashboard.py')


def regen() -> None:
    if not os.path.exists(GEN_SCRIPT):
        return
    try:
        subprocess.run([sys.executable, GEN_SCRIPT], check=False)
    except Exception:
        pass


def load() -> dict:
    if not os.path.exists(OUT_JSON):
        return {}
    try:
        with open(OUT_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def render(d: dict) -> str:
    counts = d.get('counts', {})
    human = d.get('human_todos', [])
    goals = d.get('goals_pending', [])
    heartbeats = d.get('heartbeats', [])
    milestones = d.get('milestones', [])

    lines = []
    lines.append('=== Calyx Tasks Board ===')
    lines.append(f"Human TODOs: {counts.get('todos_open', 0)} open / {counts.get('todos_total', 0)} total")
    lines.append(f"Pending goals: {counts.get('goals_pending', 0)}")
    lines.append(f"Heartbeats: {len(heartbeats)} | Milestones: {len(milestones)}")
    lines.append('')

    lines.append('Open TODOs (top 10):')
    shown = 0
    for item in human:
        if item.get('checked'):
            continue
        lines.append(f"- [ ] {item.get('text')}  ({item.get('source_file')}:{item.get('line')})")
        shown += 1
        if shown >= 10:
            break
    if shown == 0:
        lines.append('- none -')
    lines.append('')

    lines.append('Pending goals (top 10):')
    for g in goals[:10]:
        lines.append(f"- {g.get('title')}  [{g.get('filename')}]")
    if not goals:
        lines.append('- none -')
    lines.append('')

    if heartbeats:
        lines.append('Latest heartbeats:')
        for h in heartbeats[:3]:
            lines.append(f"- {h}")
        lines.append('')
    if milestones:
        lines.append('Latest milestones:')
        for m in milestones[:3]:
            lines.append(f"- {m}")
        lines.append('')

    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--watch', type=float, default=0.0, help='Refresh interval in seconds (0 = one-shot)')
    ap.add_argument('--regen', action='store_true', help='Regenerate dashboard on each refresh cycle')
    args = ap.parse_args()

    if args.watch <= 0:
        if args.regen:
            regen()
        d = load()
        print(render(d))
        return

    # watch mode
    try:
        while True:
            if args.regen:
                regen()
            d = load()
            os.system('cls' if os.name == 'nt' else 'clear')
            print(render(d))
            sys.stdout.flush()
            time.sleep(args.watch)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
