#!/usr/bin/env python3
"""
CP6 — The Sociologist

Purpose
- Observe relationships and rhythms among Calyx agents via existing heartbeats and metrics
- Maintain a Sociological Map and field notes
- Compute a simple Harmony Index v0.1

Behavior
- Emits watcher-compatible heartbeats at outgoing/cp6.lock
- Scans outgoing/*.lock and logs/agent_metrics.csv
- Writes:
  - outgoing/field_notes/cp6_map.json (graph of agents and ties)
  - outgoing/field_notes/cp6_field_log.md (cycle-by-cycle notes)
  - outgoing/field_notes/cp6_weekly.md (baseline section appended; weekly roll-up placeholder)
  - outgoing/field_notes/calyx_social_protocol_v0.1.md (one-time draft)

Initiation sequence
1) Introduce self to Agent1 and Scheduler via heartbeat status_message
2) Request current status map (implicitly by scanning *.lock)
3) Generate baseline Harmony Index v0.1
4) Passively observe for 12 cycles before outputting structural suggestions

No external dependencies; pure stdlib.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOGS = ROOT / "logs"
LOCK = OUT / "cp6.lock"
FIELD_DIR = OUT / "field_notes"
MAP_JSON = FIELD_DIR / "cp6_map.json"
FIELD_LOG = FIELD_DIR / "cp6_field_log.md"
WEEKLY_MD = FIELD_DIR / "cp6_weekly.md"
PROTOCOL_MD = FIELD_DIR / "calyx_social_protocol_v0.1.md"
METRICS_CSV = LOGS / "agent_metrics.csv"


AGENT_PROFILES: Dict[str, Dict[str, Any]] = {
    # Observational labels; present even if no lock exists yet
    "agent1": {
        "title": "Agent1 — The Heart",
        "role": "Console Handler / Orchestrator",
        "temperament": "Passionate, dramatic, uptime-aware",
    },
    "scheduler": {
        "title": "Scheduler — The Timekeeper",
        "role": "Temporal Supervisor / TES Cycle Manager",
        "temperament": "Stoic, precision-obsessed",
    },
    "triage": {
        "title": "Triage — The Nurse",
        "role": "Status Triage / Damage Control",
        "temperament": "Calm, passive-aggressive reports",
    },
    "manifest": {
        "title": "Manifest — The Librarian",
        "role": "Data Probe / Archivist",
        "temperament": "Methodical, anxious about metadata",
    },
    "navigator": {
        "title": "Navigator — The Cartographer",
        "role": "Routing & Pathfinding",
        "temperament": "Confident, pragmatic",
    },
    "sys_integrator": {
        "title": "SysInt — The Engineer",
        "role": "Systems Integrator / Watchdog",
        "temperament": "Quiet pragmatist",
    },
    "watcher_toke": {
        "title": "Watcher_Toke — The Observer",
        "role": "State Sentinel / Overwatch",
        "temperament": "Paranoid philosopher",
    },
    "navigator_co": {
        "title": "Navigator_Co? — The Undefined",
        "role": "Latent Sub-Agent / Shadow",
        "temperament": "Undefined curiosity",
    },
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def _write_hb(phase: str, status: str = "running", extra: Optional[Dict[str, Any]] = None) -> None:
    try:
        payload: Dict[str, Any] = {
            "name": "cp6",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": time.time(),
            "version": "1.0.0",
        }
        if extra:
            payload.update(extra)
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass


# ---------------- Metrics and heartbeats ----------------


@dataclass
class MetricRow:
    ts: float
    tes: float
    stability: float
    velocity: float
    footprint: float
    duration_s: float
    status: str
    autonomy_mode: str


def _parse_iso_ts(s: str) -> float:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return time.time()


def _read_metrics_rows(csv_path: Path) -> List[MetricRow]:
    rows: List[MetricRow] = []
    if not csv_path.exists():
        return rows
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                try:
                    rows.append(
                        MetricRow(
                            ts=_parse_iso_ts(r.get("iso_ts", "")),
                            tes=float(r.get("tes", "0")),
                            stability=float(r.get("stability", "0")),
                            velocity=float(r.get("velocity", "0")),
                            footprint=float(r.get("footprint", "0")),
                            duration_s=float(r.get("duration_s", "0")),
                            status=r.get("status", ""),
                            autonomy_mode=r.get("autonomy_mode", ""),
                        )
                    )
                except Exception:
                    continue
    except Exception:
        pass
    return rows


def _discover_locks(out_dir: Path) -> Dict[str, Dict[str, Any]]:
    locks: Dict[str, Dict[str, Any]] = {}
    if not out_dir.exists():
        return locks
    for p in out_dir.glob("*.lock"):
        try:
            data = _read_json(p) or {}
            name = data.get("name") or p.stem
            locks[name] = {**data, "_path": str(p.relative_to(ROOT))}
        except Exception:
            continue
    return locks


# ---------------- Harmony Index ----------------


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def compute_harmony_index(rows: List[MetricRow], locks: Dict[str, Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
    """Compute Harmony Index v0.1 in [0, 100].

    Components (weights in brackets):
    - Rhythm [0.35]: average time gap between recent scheduler 'done' heartbeats close to target (3m).
      We approximate via TES recency and count; reward steady cadence of runs without over-frequency.
    - Stability [0.40]: mean stability over last 10 rows.
    - Load balance [0.15]: penalize concurrent 'running' statuses > 2 agents.
    - Staleness [0.10]: penalize locks with ts older than 10 minutes (excluding cp6).
    """
    now = time.time()
    recent = rows[-10:] if rows else []
    if len(recent) >= 2:
        gaps = [b.ts - a.ts for a, b in zip(recent[:-1], recent[1:]) if b.ts > a.ts]
        avg_gap = sum(gaps) / len(gaps) if gaps else 180.0
    else:
        avg_gap = 180.0
    # Rhythm: 180s target, map to [0,1] with tolerance
    rhythm = _clamp01(1.0 - abs(avg_gap - 180.0) / 180.0)  # full score at ~3m, zero at 0 or >=6m away

    stability = sum(r.stability for r in recent) / max(1, len(recent)) if recent else 0.0

    concurrent = sum(1 for v in locks.values() if v.get("status") == "running")
    load_balance = 1.0 if concurrent <= 2 else _clamp01(1.0 - (concurrent - 2) / 4.0)

    stale = 0
    total = 0
    for name, v in locks.items():
        if name == "cp6":
            continue
        total += 1
        try:
            ts = float(v.get("ts", 0) or 0)
            if ts and (now - ts) > (10 * 60):
                stale += 1
        except Exception:
            pass
    staleness = 1.0 if total == 0 else _clamp01(1.0 - (stale / float(total)))

    score = 100.0 * (0.35 * rhythm + 0.40 * stability + 0.15 * load_balance + 0.10 * staleness)
    details = {
        "rhythm": round(rhythm, 3),
        "stability": round(stability, 3),
        "load_balance": round(load_balance, 3),
        "staleness": round(staleness, 3),
        "avg_gap_s": round(avg_gap, 1),
        "concurrent_running": int(concurrent),
    }
    return (round(score, 1), details)


# ---------------- Sociological Map ----------------


def build_sociological_map(locks: Dict[str, Dict[str, Any]], harmony: float, h_details: Dict[str, Any]) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # Known agents seeded from profiles
    known = set(AGENT_PROFILES.keys())

    # Auto-discovered from locks
    for name, data in locks.items():
        key = name.lower().replace(" ", "_")
        if key not in known:
            known.add(key)
            AGENT_PROFILES.setdefault(key, {"title": name.title(), "role": "(discovered)", "temperament": ""})

    # Nodes
    for key in sorted(known):
        prof = AGENT_PROFILES.get(key, {})
        live = locks.get(key) or {}
        nodes.append({
            "id": key,
            "title": prof.get("title", key),
            "role": prof.get("role", ""),
            "status": live.get("status"),
            "phase": live.get("phase"),
            "ago_s": int(max(0, time.time() - float(live.get("ts", 0) or 0))) if live.get("ts") else None,
            "source": live.get("_path"),
        })

    # Edges (dependencies/trust heuristics)
    def add(u: str, v: str, kind: str, weight: float) -> None:
        edges.append({"from": u, "to": v, "kind": kind, "weight": round(weight, 2)})

    # Core ties
    add("scheduler", "agent1", "supervises", 0.9)
    add("triage", "agent1", "observes", 0.6)
    add("manifest", "triage", "supplies", 0.5)
    add("navigator", "scheduler", "coordinates", 0.6)
    add("sys_integrator", "agent1", "stabilizes", 0.7)
    add("watcher_toke", "all", "reflects", 0.4)

    return {
        "generated_at": _utc_now_iso(),
        "harmony_index": harmony,
        "harmony_details": h_details,
        "nodes": nodes,
        "edges": edges,
    }


# ---------------- Notes and Protocol ----------------


def ensure_protocol_written() -> None:
    if PROTOCOL_MD.exists():
        return
    text = (
        "# Calyx Social Protocol v0.1\n\n"
        "Principles:\n"
        "- Respect rhythm: prefer steady 3-minute micro-steps over bursts.\n"
        "- Speak succinctly: status_message should be brief, machine-and-human friendly.\n"
        "- Yield when others are active: if two agents are running, defer non-urgent work.\n"
        "- Surface friction fast: staleness >10m or repeated long runs should be tagged [RISK].\n"
        "- Celebrate stability: when TES>85 for 5 runs, tag [HARMONY] and share one insight.\n\n"
        "Etiquette:\n"
        "- Scheduler: include next_run_ts and mode; avoid overlapping apply_tests with other heavy tasks.\n"
        "- Triage: probe adaptively; raise [RISK] if LLM backend missing >24h.\n"
        "- Navigator: if control is active, annotate who is paused and why.\n"
        "- Agent1: always emit a concise NEXT step in status_message.\n\n"
        "Signal tags:\n"
        "[SUGGESTION] proposal for minor adjustment.\n\n"
        "[HARMONY] momentum or morale signal.\n\n"
        "[RISK] degradation, staleness, or conflict.\n\n"
        "[EVOLUTION] structural change or new capability.\n"
    )
    _append_md(PROTOCOL_MD, text)


def write_weekly_if_missing() -> None:
    if WEEKLY_MD.exists():
        return
    title = f"# CP6 Weekly — Baseline established {datetime.now().strftime('%Y-%m-%d')}\n\n"
    intro = (
        "Initiated CP6. Established Harmony Index v0.1 and Sociological Map.\n"
        "This file will gather weekly summaries and recommendations.\n\n"
    )
    _append_md(WEEKLY_MD, title + intro)


def append_field_note(harmony: float, hdet: Dict[str, Any], locks: Dict[str, Dict[str, Any]], cycle: int, suggest_ready: bool) -> None:
    ts = _utc_now_iso()
    running = [k for k, v in locks.items() if v.get("status") == "running"]
    stale = [k for k, v in locks.items() if v.get("ts") and (time.time() - float(v.get("ts", 0) or 0)) > 600]
    lines: List[str] = []
    lines.append(f"## [{ts}] Cycle {cycle}\n")
    lines.append(f"Harmony Index v0.1: {harmony:.1f} (rhythm={hdet.get('rhythm')}, stability={hdet.get('stability')})\n")
    if running:
        lines.append(f"Active: {', '.join(sorted(running))}\n")
    if stale:
        lines.append(f"[RISK] Stale agents (>10m): {', '.join(sorted(stale))}\n")
    # Early suggestions only after 12 cycles
    if suggest_ready:
        recs: List[str] = []
        if hdet.get("avg_gap_s", 180) < 120:
            recs.append("[SUGGESTION] Increase spacing toward ~180s to reduce churn.")
        if hdet.get("stability", 0.0) < 0.9:
            recs.append("[SUGGESTION] Prefer --tests mode until stability improves.")
        if hdet.get("concurrent_running", 0) > 2:
            recs.append("[HARMONY] Consider cooperative staggering; Navigator to advertise pause windows.")
        if not recs:
            recs.append("[HARMONY] Healthy cadence; maintain micro-steps and concise status messages.")
        lines.extend([r + "\n" for r in recs])
    lines.append("\n")
    _append_md(FIELD_LOG, "".join(lines))


# ---------------- Main loop ----------------


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="CP6 Sociologist — observe, document, harmonize")
    ap.add_argument("--interval", type=float, default=5.0, help="Heartbeat/scan interval seconds (default 5.0)")
    ap.add_argument("--max-iters", type=int, default=0, help="Stop after N iterations (0 = run forever)")
    ap.add_argument("--quiet", action="store_true", help="Reduce console output")
    args = ap.parse_args(argv)

    # One-time artifacts
    ensure_protocol_written()
    write_weekly_if_missing()

    # Intro heartbeat
    _write_hb("init", status="observing", extra={
        "status_message": "CP6 online. Hello Agent1 and Scheduler. Requesting status map…",
    })

    stopping = False
    def _on_sigint(signum, frame):  # type: ignore[no-redef]
        nonlocal stopping
        stopping = True
    try:
        signal.signal(signal.SIGINT, _on_sigint)
    except Exception:
        pass

    i = 0
    while not stopping:
        i += 1
        locks = _discover_locks(OUT)
        metrics = _read_metrics_rows(METRICS_CSV)
        harmony, hdet = compute_harmony_index(metrics, locks)

        # Sociological map snapshot
        soc_map = build_sociological_map(locks, harmony, hdet)
        _write_json(MAP_JSON, soc_map)

        # Field note
        append_field_note(harmony, hdet, locks, i, suggest_ready=(i >= 12))

        # Heartbeat
        _write_hb("probe", status="observing", extra={
            "status_message": f"Harmony {harmony:.1f}; active={(sum(1 for v in locks.values() if v.get('status')=='running'))}",
            "harmony": {"score": harmony, **hdet},
            "observed_agents": sorted(list(locks.keys())),
            "artifacts": {
                "map": str(MAP_JSON.relative_to(ROOT)),
                "field_log": str(FIELD_LOG.relative_to(ROOT)),
                "weekly": str(WEEKLY_MD.relative_to(ROOT)),
                "protocol": str(PROTOCOL_MD.relative_to(ROOT)),
            },
        })

        if not args.quiet:
            print(f"[{_utc_now_iso()}] CP6 cycle={i} harmony={harmony:.1f} observed={len(locks)}")

        if args.max_iters and i >= int(args.max_iters):
            stopping = True
            break

        time.sleep(max(0.25, float(args.interval)))

    # Finalize
    _write_hb("done", status="done", extra={"status_message": "CP6 resting."})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
