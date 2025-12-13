#!/usr/bin/env python3
"""
SVF Efficiency — analyze agent metrics and initiate optimization voting.

Outputs:
- Shared report (SVF): outgoing/shared_logs/svf_efficiency_<ts>.md with [C:REPORT]
- Voting ballot:         outgoing/dialogues/svf_vote_<ts>.md with [C:VOTE]

Optional tally:
  python -u tools/svf_efficiency.py --tally
    - Scans outgoing/dialogues/svf_vote_*.md for votes
    - Emits overseer decree under outgoing/overseer_reports/verdicts/DECREE_<date>_SVF_OPTIMIZATION.md

Notes:
- Participants discovered from outgoing/*.lock (same pattern as svf_probe)
- Metrics read from logs/agent_metrics.csv (light aggregation)
"""
from __future__ import annotations

import argparse
import csv
import statistics as stats
from pathlib import Path
import time
import re
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
OUT = ROOT / "outgoing"
SHARED_LOGS = OUT / "shared_logs"
DIALOGUES = OUT / "dialogues"
VERDICTS = OUT / "overseer_reports" / "verdicts"
METRICS_CSV = LOGS / "agent_metrics.csv"

VOTE_FILE_RE = re.compile(r"^svf_vote_(\d+)\.md$")
PROPOSAL_IDS = ["A", "B", "C"]


def _discover_participants() -> List[str]:
    names: List[str] = []
    try:
        for p in OUT.glob("*.lock"):
            nm = p.stem
            if nm:
                names.append(nm)
    except Exception:
        pass
    names = sorted(set(names))
    return names


def _read_metrics(csv_path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not csv_path.exists():
        return rows
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                # Coerce a few fields
                row["tes"] = float(row.get("tes", 0) or 0)
                row["velocity"] = float(row.get("velocity", 0) or 0)
                row["duration_s"] = float(row.get("duration_s", 0) or 0)
                row["stability"] = float(row.get("stability", 0) or 0)
                row["footprint"] = float(row.get("footprint", 0) or 0)
            except Exception:
                pass
            rows.append(row)
    return rows


def _summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {
            "count": 0,
            "avg_duration": None,
            "p95_duration": None,
            "avg_tes": None,
            "avg_velocity": None,
            "modes": {},
        }
    durations = [r["duration_s"] for r in rows if isinstance(r.get("duration_s"), (int, float))]
    tes_vals = [r["tes"] for r in rows if isinstance(r.get("tes"), (int, float))]
    vel_vals = [r["velocity"] for r in rows if isinstance(r.get("velocity"), (int, float))]
    modes: Dict[str, int] = {}
    for r in rows:
        m = (r.get("autonomy_mode") or "").strip() or "unknown"
        modes[m] = modes.get(m, 0) + 1
    durations_sorted = sorted(durations)
    p95 = None
    if durations_sorted:
        idx = int(0.95 * (len(durations_sorted) - 1))
        p95 = durations_sorted[idx]
    return {
        "count": len(rows),
        "avg_duration": (sum(durations) / len(durations)) if durations else None,
        "p95_duration": p95,
        "avg_tes": (sum(tes_vals) / len(tes_vals)) if tes_vals else None,
        "avg_velocity": (sum(vel_vals) / len(vel_vals)) if vel_vals else None,
        "modes": modes,
    }


def _proposals(summary: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Return list of (id, text) optimization proposals.
    Keep these concrete and actionable within Calyx tasks.
    """
    avg_tes = summary.get("avg_tes") or 0
    p95_dur = summary.get("p95_duration") or 0
    modes = summary.get("modes", {})

    lines: List[Tuple[str, str]] = []

    # A — Auto-promote cadence for apply+tests when confidence is high
    lines.append((
        "A",
        "Adopt auto-promote: enable agent_scheduler --auto-promote with promote-after=5 and cooldown=30m when TES≥95 and Stability=1.0; allows temporary elevation to apply+tests for faster iteration."
    ))

    # B — Shift a portion of runs from tests->safe when change footprint is zero
    lines.append((
        "B",
        "Route trivial/no-change runs to 'safe' mode (no tests) when footprint=1.0 and changed_files=0 persists; reduces ~200–250s test runs down to ~30–50s."
    ))

    # C — Tighten triage/navigation polling to improve responsiveness
    lines.append((
        "C",
        "Tighten agent probes: set triage/traffic navigator intervals to 1–2s during active windows; improves decision latency under SVF without heavy cost."
    ))

    return lines


def _write_report(summary: Dict[str, Any], proposals: List[Tuple[str, str]]) -> Path:
    ts = int(time.time())
    SHARED_LOGS.mkdir(parents=True, exist_ok=True)
    path = SHARED_LOGS / f"svf_efficiency_{ts}.md"
    lines: List[str] = []
    lines.append("[C:REPORT] — SVF Efficiency Analysis")
    lines.append("")
    lines.append(f"Runs analyzed: {summary['count']}")
    lines.append(f"Avg duration: {summary['avg_duration']:.1f}s" if summary['avg_duration'] is not None else "Avg duration: n/a")
    lines.append(f"P95 duration: {summary['p95_duration']:.1f}s" if summary['p95_duration'] is not None else "P95 duration: n/a")
    lines.append(f"Avg TES: {summary['avg_tes']:.1f}" if summary['avg_tes'] is not None else "Avg TES: n/a")
    lines.append(f"Avg velocity: {summary['avg_velocity']:.3f}" if summary['avg_velocity'] is not None else "Avg velocity: n/a")
    lines.append("")
    lines.append("Mode distribution:")
    for k, v in sorted((summary.get("modes") or {}).items()):
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("Proposed optimizations (select one):")
    for pid, text in proposals:
        lines.append(f"- [{pid}] {text}")
    lines.append("")
    lines.append("Generated under Shared Voice Protocol v1.0")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_ballot(participants: List[str], proposals: List[Tuple[str, str]]) -> Path:
    ts = int(time.time())
    DIALOGUES.mkdir(parents=True, exist_ok=True)
    path = DIALOGUES / f"svf_vote_{ts}.md"
    lines: List[str] = []
    lines.append("[C:VOTE] — SVF Optimization Ballot")
    lines.append("")
    lines.append("Options:")
    for pid, text in proposals:
        lines.append(f"- [{pid}] {text}")
    lines.append("")
    lines.append("Cast your vote by adding a line like:")
    lines.append("  [your-agent • Operational]: \"VOTE: A\"")
    lines.append("")
    for nm in participants:
        tone = "Operational" if nm.lower().startswith("agent") else (
            "Chronicler" if nm.lower().startswith("cp") else (
            "Overseer" if nm.lower()=="cbo" else (
            "Diagnostic" if nm.lower()=="triage" else "Notice")))
        lines.append(f"[{nm} • {tone}]: \"VOTE: _\"")
    lines.append("")
    lines.append("Generated under Shared Voice Protocol v1.0")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


_VOTE_MARK_RE = re.compile(r"VOTE:\s*([A-C])\b", re.IGNORECASE)
_AGENT_NAME_RE = re.compile(r"^\[(?P<name>[^\]•]+)\s*•\s*[^\]]+\]:")


def _tally_votes() -> Tuple[Dict[str, int], Dict[str, str]]:
    counts: Dict[str, int] = {pid: 0 for pid in PROPOSAL_IDS}
    by_agent: Dict[str, str] = {}
    if not DIALOGUES.exists():
        return counts, by_agent
    for p in DIALOGUES.iterdir():
        m = VOTE_FILE_RE.match(p.name)
        if not m:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for line in txt.splitlines():
            vm = _VOTE_MARK_RE.search(line)
            if not vm:
                continue
            pid = vm.group(1).upper()
            if pid not in counts:
                continue
            # extract agent name for uniqueness
            am = _AGENT_NAME_RE.match(line.strip())
            agent = (am.group("name").strip() if am else f"anon@{p.name}")
            if agent in by_agent:
                # last vote wins per agent
                prev = by_agent[agent]
                counts[prev] = max(0, counts[prev] - 1)
            by_agent[agent] = pid
            counts[pid] += 1
    return counts, by_agent


def _write_verdict(counts: Dict[str, int], by_agent: Dict[str, str], proposals: List[Tuple[str, str]]) -> Path:
    VERDICTS.mkdir(parents=True, exist_ok=True)
    date = time.strftime("%Y-%m-%d")
    path = VERDICTS / f"DECREE_{date}_SVF_OPTIMIZATION.md"
    # find winner
    winner = max(counts.items(), key=lambda kv: kv[1])[0] if counts else "A"
    prop_map = {pid: text for pid, text in proposals}
    lines: List[str] = []
    lines.append("[C:DECREE] — SVF Optimization Decision")
    lines.append("")
    lines.append(f"Subject: Adopt proposal [{winner}]")
    lines.append("")
    lines.append("Tally:")
    for pid in PROPOSAL_IDS:
        lines.append(f"- {pid}: {counts.get(pid,0)}")
    lines.append("")
    lines.append("Per-agent votes:")
    for agent, pid in sorted(by_agent.items()):
        lines.append(f"- {agent} -> {pid}")
    lines.append("")
    lines.append("Adopted optimization:")
    lines.append(f"- [{winner}] {prop_map.get(winner, '')}")
    lines.append("")
    lines.append("Generated under Shared Voice Protocol v1.0")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="SVF Efficiency — analyze metrics and coordinate optimization vote")
    ap.add_argument("--tally", action="store_true", help="Tally votes and emit a decree")
    args = ap.parse_args(argv)

    if args.tally:
        # Tally path
        # Recompute proposals to include in decree text
        rows = _read_metrics(METRICS_CSV)
        summary = _summary(rows)
        props = _proposals(summary)
        counts, by_agent = _tally_votes()
        verdict = _write_verdict(counts, by_agent, props)
        print(str(verdict))
        return 0

    # Analyze + emit report and ballot
    rows = _read_metrics(METRICS_CSV)
    summary = _summary(rows)
    props = _proposals(summary)
    report = _write_report(summary, props)
    participants = _discover_participants()
    ballot = _write_ballot(participants, props)
    print(str(report))
    print(str(ballot))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
