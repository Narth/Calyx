#!/usr/bin/env python3
"""
CP9 — The Auto-Tuner

Purpose
- Propose tuning recommendations for triage cadence, navigator control thresholds, and scheduler promotion gates
  based on CP7 chronicles and recent metrics.

Behavior
- Emits watcher-compatible heartbeats at outgoing/cp9.lock
- Reads logs/agent_metrics.csv and outgoing/chronicles/*
- Writes outgoing/tuning/recommendations.json and a brief summary Markdown

No external dependencies; pure stdlib.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOCK = OUT / "cp9.lock"
METRICS = ROOT / "logs" / "agent_metrics.csv"
TUN_DIR = OUT / "tuning"
REC_JSON = TUN_DIR / "recommendations.json"
REC_MD = TUN_DIR / "recommendations.md"
VERSION = "0.1.0"


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
            "name": "cp9",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": time.time(),
            "version": VERSION,
        }
        if extra:
            payload.update(extra)
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _parse_rows(csv_path: Path, n: int = 50) -> List[Dict[str, Any]]:
    """Parse last n rows from CSV (default 50 for accurate recent baseline, updated 2025-10-26 per CBO team meeting)"""
    rows: List[Dict[str, Any]] = []
    if not csv_path.exists():
        return rows
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)[-max(1, n):]
    return rows


def _float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def analyze(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {
            "status": "insufficient_data",
            "message": "No metrics found; keep CP9 idle until more runs accumulate.",
            "recommendations": [],
        }
    avg_tes = sum(_float(r.get("tes")) for r in rows) / len(rows)
    avg_stab = sum(_float(r.get("stability")) for r in rows) / len(rows)
    avg_dur = sum(_float(r.get("duration_s")) for r in rows) / len(rows)

    recs: List[Dict[str, Any]] = []
    # Triage cadence
    if avg_dur > 240.0 or avg_tes < 85.0:
        recs.append({
            "id": "triage::slower_idle",
            "title": "Increase idle probe interval",
            "suggest": {"relaxed_probe_sec": 180},
            "reason": f"avg_duration={avg_dur:.1f}s or avg_TES={avg_tes:.1f} suggests saving cycles when idle",
        })
    else:
        recs.append({
            "id": "triage::balanced",
            "title": "Use balanced probe schedule",
            "suggest": {"initial_probe_sec": 20, "relaxed_probe_sec": 120},
            "reason": f"avg_duration={avg_dur:.1f}s and avg_TES={avg_tes:.1f} support tighter checks during activity",
        })

    # Scheduler promotion gates (keep conservative)
    if avg_stab >= 0.9 and avg_tes >= 85.0:
        recs.append({
            "id": "scheduler::promote_when_stable",
            "title": "Enable auto-promote (tests) after 5 stable runs",
            "suggest": {"promote_after": 5, "mode": "tests"},
            "reason": f"avg_stability={avg_stab:.2f} and avg_TES={avg_tes:.1f}",
        })
    else:
        recs.append({
            "id": "scheduler::hold",
            "title": "Hold promotions until stability improves",
            "suggest": {"mode": "safe"},
            "reason": f"avg_stability={avg_stab:.2f} or avg_TES={avg_tes:.1f} below threshold",
        })

    # Navigator override guidance
    if avg_dur > 300.0:
        recs.append({
            "id": "navigator::long_runs",
            "title": "Use override interval 45–60s during long runs",
            "suggest": {"probe_interval_sec": 60},
            "reason": f"avg_duration={avg_dur:.1f}s implies reducing incidental probes",
        })
    else:
        recs.append({
            "id": "navigator::adaptive",
            "title": "Prefer adaptive control; avoid fixed 30s overrides",
            "suggest": {"adaptive": True},
            "reason": "Adaptive mode reduces unnecessary probes when idle",
        })

    return {
        "status": "ok",
        "summary": {
            "avg_tes": round(avg_tes, 2),
            "avg_stability": round(avg_stab, 3),
            "avg_duration_s": round(avg_dur, 1),
        },
        "recommendations": recs,
    }


def write_recommendations(rec: Dict[str, Any]) -> Dict[str, Any]:
    _write_json(REC_JSON, rec)
    lines = ["# CP9 Tuning Recommendations\n\n"]
    s = rec.get("summary", {})
    lines.append(f"- avg TES: {s.get('avg_tes')}\n")
    lines.append(f"- avg stability: {s.get('avg_stability')}\n")
    lines.append(f"- avg duration: {s.get('avg_duration_s')}s\n\n")
    for r in rec.get("recommendations", []):
        lines.append(f"- {r.get('title')}: {r.get('reason')} -> suggest {r.get('suggest')}\n")
    _append_md(REC_MD, "".join(lines))
    return {"open_path": str(REC_MD.relative_to(ROOT)), "json": str(REC_JSON.relative_to(ROOT))}


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="CP9 Auto-Tuner — propose cadence and promotion tuning")
    ap.add_argument("--interval", type=float, default=15.0)
    ap.add_argument("--max-iters", type=int, default=0)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    i = 0
    while True:
        i += 1
        rows = _parse_rows(METRICS, n=10)
        rec = analyze(rows)
        paths = write_recommendations(rec)
        status = "observing" if rec.get("status") == "ok" else "warn"
        s = rec.get("summary") or {}
        msg = f"cp7: tuning avgTES={s.get('avg_tes')} stab={s.get('avg_stability')} -> recs"
        _write_hb("analyze", status=status, extra={
            "status_message": msg,
            "summary": rec.get("summary"),
            "open_path": paths.get("open_path"),
        })
        if not args.quiet:
            print(f"[CP9] cycle={i} status={rec.get('status')} -> {paths.get('open_path')}")
        if args.max_iters and i >= int(args.max_iters):
            break
        time.sleep(max(0.5, float(args.interval)))

    _write_hb("done", status="done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
