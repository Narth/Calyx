#!/usr/bin/env python3
"""
Generate a unified tasks dashboard for Calyx Terminal.

Scans:
- TODO.MD: Markdown checkboxes (- [ ] / - [x])
- Outgoing goals: outgoing/goal_*.txt (pending/archived goals)
- Heartbeats index: logs/HEARTBEATS.md (latest entries)
- Milestones: MILESTONES.md (section headings)

Outputs:
- outgoing/tasks_dashboard.json — machine-readable summary
- logs/TASKS.md — human-readable rollup

Safe, read-only outside of writing the two outputs.
"""
from __future__ import annotations
import json
import os
import re
import glob
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple, Dict, Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTGOING = os.path.join(ROOT, 'outgoing')
LOGS = os.path.join(ROOT, 'logs')

CHECKBOX_RE = re.compile(r"^\s*[-*]\s+\[( |x|X)\]\s+(.*)")
HEADING_RE = re.compile(r"^##\s+(.*)")

@dataclass
class TodoItem:
    text: str
    checked: bool
    source_file: str
    line: int

@dataclass
class GoalItem:
    filename: str
    title: str
    size: int

@dataclass
class Dashboard:
    human_todos: List[TodoItem]
    goals_pending: List[GoalItem]
    heartbeats: List[str]
    milestones: List[str]
    agents: List[Dict[str, Any]]
    triage: Dict[str, Any]
    telemetry: Dict[str, Any]


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                return f.read()
        except Exception:
            return None
    except FileNotFoundError:
        return None


def parse_markdown_checkboxes(path: str) -> List[TodoItem]:
    text = _read_text(path)
    items: List[TodoItem] = []
    if not text:
        return items
    for i, line in enumerate(text.splitlines(), start=1):
        m = CHECKBOX_RE.match(line)
        if m:
            checked = m.group(1).lower() == 'x'
            body = m.group(2).strip()
            if body:
                items.append(TodoItem(text=body, checked=checked, source_file=os.path.relpath(path, ROOT), line=i))
    return items


def parse_heartbeats(path: str) -> List[str]:
    text = _read_text(path)
    if not text:
        return []
    headings = []
    for line in text.splitlines():
        m = HEADING_RE.match(line)
        if m:
            headings.append(m.group(1).strip())
    return headings


def parse_milestones(path: str) -> List[str]:
    # collect "## " section headings (skip Accolades unless a heading)
    return parse_heartbeats(path)


def list_goal_files() -> List[GoalItem]:
    paths = sorted(glob.glob(os.path.join(OUTGOING, 'goal_*.txt')))
    items: List[GoalItem] = []
    for p in paths:
        try:
            size = os.path.getsize(p)
        except OSError:
            size = 0
        title = os.path.basename(p)
        # peek first line if available
        text = _read_text(p)
        if text:
            first_line = text.splitlines()[0].strip()
            if first_line and len(first_line) < 200:
                title = f"{os.path.basename(p)} — {first_line}"
        items.append(GoalItem(filename=os.path.relpath(p, ROOT), title=title, size=size))
    return items


def read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def collect_agent_heartbeats() -> List[Dict[str, Any]]:
    agents: List[Dict[str, Any]] = []
    for name in ("agent1", "triage"):
        lock_path = os.path.join(OUTGOING, f"{name}.lock")
        data = read_json(lock_path) or {}
        if data:
            agents.append({
                "name": name,
                "phase": data.get("phase"),
                "status": data.get("status"),
                "ts": data.get("ts"),
                "run_dir": data.get("run_dir"),
                "summary": data.get("summary"),
                "goal_preview": data.get("goal_preview") if name == "agent1" else None,
            })
        else:
            agents.append({"name": name, "phase": None, "status": "idle", "ts": None, "run_dir": None})
    # sort: running first, then by name
    def key(a: Dict[str, Any]):
        return (0 if a.get("status") == "running" else 1, a.get("name",""))
    return sorted(agents, key=key)


def collect_triage_reports() -> Dict[str, Any]:
    reports = sorted(glob.glob(os.path.join(OUTGOING, 'triage_agent_run_*.json')))
    # Also accept generic triage_*.json
    reports.extend(sorted(glob.glob(os.path.join(OUTGOING, 'triage_*.json'))))
    reports = sorted(set(reports))
    latest: Optional[str] = reports[-1] if reports else None
    summary: Dict[str, Any] = {}
    if latest:
        data = read_json(latest) or {}
        phase_a = bool((data.get("phase_a") or {}).get("ok"))
        phase_b = data.get("phase_b") or {}
        phase_c = data.get("phase_c") or {}
        # consider basic pass if compile_ok true and (pytest_ok if present)
        compile_ok = bool(phase_c.get("compile_ok"))
        pytest_ok = phase_c.get("pytest_ok")
        stability_ok = compile_ok and (True if pytest_ok in (None, True) else False)
        review_ok = (
            bool(phase_b.get("diff_present")) and
            (phase_b.get("files_ok") in (True, None)) and
            (phase_b.get("try_it_snippet_ok") in (True, None))
        )
        summary = {
            "latest": os.path.relpath(latest, ROOT),
            "phase_a": phase_a,
            "phase_b": review_ok,
            "phase_c": stability_ok,
            "compile_ok": compile_ok,
            "pytest_ok": pytest_ok if pytest_ok is not None else None,
            "run_dir": data.get("run_dir"),
        }
    return {"latest": summary, "count": len(reports)}


def read_telemetry_state() -> Dict[str, Any]:
    path = os.path.join(OUTGOING, 'telemetry', 'state.json')
    data = read_json(path) or {}
    # normalize minimal summary fields
    drift = (data.get('drift') or {}).get('agent1_scheduler') or {}
    active = data.get('active_count')
    counts = data.get('status_counts') or {}
    return {
        'active_count': active if isinstance(active, int) else 0,
        'drift_agent1_scheduler': {
            'latest': drift.get('latest'),
            'avg': drift.get('avg'),
            'samples': drift.get('samples'),
        },
        'status_counts': {
            'running': int(counts.get('running') or 0),
            'done': int(counts.get('done') or 0),
            'error': int(counts.get('error') or 0),
            'other': int(counts.get('other') or 0),
        }
    }


def ensure_dirs():
    os.makedirs(OUTGOING, exist_ok=True)
    os.makedirs(LOGS, exist_ok=True)


def build_dashboard() -> Dashboard:
    ensure_dirs()
    todos: List[TodoItem] = []
    for name in ('TODO.MD', 'COPILOT_TASK.md'):
        path = os.path.join(ROOT, name)
        todos.extend(parse_markdown_checkboxes(path))

    heartbeats = parse_heartbeats(os.path.join(ROOT, 'logs', 'HEARTBEATS.md'))
    milestones = parse_milestones(os.path.join(ROOT, 'MILESTONES.md'))
    goals = list_goal_files()
    agents = collect_agent_heartbeats()
    triage = collect_triage_reports()
    telemetry = read_telemetry_state()

    return Dashboard(
        human_todos=todos,
        goals_pending=goals,
        heartbeats=heartbeats,
        milestones=milestones,
        agents=agents,
        triage=triage,
        telemetry=telemetry,
    )


def write_json(d: Dashboard, path: str):
    payload = {
        'human_todos': [asdict(x) for x in d.human_todos],
        'goals_pending': [asdict(x) for x in d.goals_pending],
        'heartbeats': d.heartbeats,
        'milestones': d.milestones,
        'agents': d.agents,
        'triage': d.triage,
        'telemetry': d.telemetry,
        'counts': {
            'todos_total': len(d.human_todos),
            'todos_open': sum(1 for x in d.human_todos if not x.checked),
            'goals_pending': len(d.goals_pending),
            'heartbeats': len(d.heartbeats),
            'milestones': len(d.milestones),
            'agents': len([a for a in d.agents if a.get('status') != 'idle']),
            'triage_reports': int(d.triage.get('count', 0)),
            'agents_active': int(d.telemetry.get('active_count') or 0),
        }
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)


def write_markdown(d: Dashboard, path: str):
    open_count = sum(1 for x in d.human_todos if not x.checked)
    total_count = len(d.human_todos)
    lines: List[str] = []
    lines.append('# Tasks Dashboard')
    lines.append('')
    # Telemetry summary
    tel = d.telemetry or {}
    if tel:
        drift = (tel.get('drift_agent1_scheduler') or {})
        drift_text = 'n/a'
        latest = drift.get('latest')
        avg = drift.get('avg')
        if latest is not None:
            drift_text = f"latest {latest:.2f}s"
        if avg is not None:
            drift_text += f", avg {avg:.2f}s"
        sc = tel.get('status_counts') or {}
        sc_text = f"running {int(sc.get('running') or 0)}, done {int(sc.get('done') or 0)}, error {int(sc.get('error') or 0)}"
        lines.append(f"- Telemetry: {int(tel.get('active_count') or 0)} agents active; {sc_text}; drift(agent1↔scheduler): {drift_text}")
        lines.append('')
    lines.append(f'- Human TODOs: {open_count} open / {total_count} total')
    lines.append(f'- Pending goals: {len(d.goals_pending)}')
    if d.heartbeats:
        lines.append(f'- Heartbeats: {len(d.heartbeats)} (latest: {d.heartbeats[0]})')
    else:
        lines.append('- Heartbeats: 0')
    if d.milestones:
        lines.append(f'- Milestones: {len(d.milestones)} (latest: {d.milestones[0]})')
    else:
        lines.append('- Milestones: 0')
    lines.append('')

    # Section: Agent status
    lines.append('## Agent status')
    if not d.agents:
        lines.append('_None_')
    else:
        for a in d.agents:
            name = a.get('name')
            phase = a.get('phase') or '—'
            status = a.get('status') or 'idle'
            rd = a.get('run_dir')
            extra = []
            if rd:
                extra.append(f"run: {rd}")
            gp = a.get('goal_preview')
            if gp:
                extra.append(gp)
            details = ('  —  '.join(extra)) if extra else ''
            lines.append(f"- {name}: {status} ({phase}){('  —  ' + details) if details else ''}")
    lines.append('')

    # Section: Triage summary
    lines.append('## Triage (3-phase)')
    latest = d.triage.get('latest') or {}
    if not latest:
        lines.append('_No triage reports found._')
    else:
        pa = 'PASS' if latest.get('phase_a') else 'FAIL'
        pb = 'PASS' if latest.get('phase_b') else 'FAIL'
        pc = 'PASS' if latest.get('phase_c') else 'FAIL'
        lines.append(f"Latest: {latest.get('latest','')}  —  A:{pa}  B:{pb}  C:{pc}")
        if latest.get('run_dir'):
            lines.append(f"Run dir: {latest.get('run_dir')}")
    lines.append('')

    # Section: Open TODOs (top 20)
    lines.append('## Open TODOs (top 20)')
    if open_count == 0:
        lines.append('_None_')
    else:
        shown = 0
        for item in d.human_todos:
            if item.checked:
                continue
                lines.append(f'- [ ] {item.text}  (source: {item.source_file}:{item.line})')
            shown += 1
            if shown >= 20:
                break
    lines.append('')

    # Section: Pending goals
    lines.append('## Pending goals')
    if not d.goals_pending:
        lines.append('_None_')
    else:
        for g in d.goals_pending[:20]:
            lines.append(f'- {g.title}  \u2014 `{g.filename}`')
    lines.append('')

    # Section: Latest heartbeats & milestones
    lines.append('## Timeline markers')
    if d.heartbeats:
        lines.append('**Heartbeats:**')
        for h in d.heartbeats[:5]:
            lines.append(f'- {h}')
    else:
        lines.append('**Heartbeats:** _none_')
    lines.append('')
    if d.milestones:
        lines.append('**Milestones:**')
        for m in d.milestones[:5]:
            lines.append(f'- {m}')
    else:
        lines.append('**Milestones:** _none_')
    lines.append('')

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    d = build_dashboard()
    write_json(d, os.path.join(OUTGOING, 'tasks_dashboard.json'))
    write_markdown(d, os.path.join(LOGS, 'TASKS.md'))
    print('Wrote:', os.path.join(OUTGOING, 'tasks_dashboard.json'))
    print('Wrote:', os.path.join(LOGS, 'TASKS.md'))


if __name__ == '__main__':
    main()
