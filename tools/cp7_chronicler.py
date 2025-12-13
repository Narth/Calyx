#!/usr/bin/env python3
"""
CP7 — The Chronicler

Purpose
- Observe, record, and maintain stability across Calyx subsystems.
- Provide diagnostics and narrative continuity for future copilots.

Behavior
- Emits watcher-compatible heartbeats at outgoing/cp7.lock
- Scans outgoing/*.lock and logs/agent_metrics.csv
- Computes a drift baseline between Scheduler and Agent1
- Writes:
  - outgoing/chronicles/chronicle_<timestamp>.md (human-readable)
  - outgoing/chronicles/diagnostics/diag_report_<timestamp>.json (machine analytics)
  - outgoing/chronicles/CP7_WEEKLY_SUMMARY.md (rolling weekly digest)
  - outgoing/LOG_CP7_GENESIS.txt (one-time init log)

Alerts
- When instability is detected, include tags and concise messages:
  - [SOCIAL_IMPACT] for CP6
  - [HEARTBEAT_UNSTABLE] for Agent1
  - [TECHNICAL_FAULT] for SysInt

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
LOCK = OUT / "cp7.lock"
CHRON_DIR = OUT / "chronicles"
DIAG_DIR = CHRON_DIR / "diagnostics"
WEEKLY_MD = CHRON_DIR / "CP7_WEEKLY_SUMMARY.md"
GENESIS_LOG = OUT / "LOG_CP7_GENESIS.txt"
METRICS_CSV = LOGS / "agent_metrics.csv"
# SVF ensure on startup
try:
    from tools.svf_util import ensure_svf_running  # type: ignore
except Exception:
    def ensure_svf_running(*args, **kwargs):  # type: ignore
        return False


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ts() -> float:
    return time.time()


def _ensure_dirs() -> None:
    CHRON_DIR.mkdir(parents=True, exist_ok=True)
    DIAG_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def _write_hb(phase: str, status: str = "running", extra: Optional[Dict[str, Any]] = None) -> None:
    try:
        payload: Dict[str, Any] = {
            "name": "cp7",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": _ts(),
            "version": "1.0.0",
        }
        if extra:
            payload.update(extra)
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# ---------------- Data sources ----------------


def _discover_locks() -> Dict[str, Dict[str, Any]]:
    locks: Dict[str, Dict[str, Any]] = {}
    if not OUT.exists():
        return locks
    for p in OUT.glob("*.lock"):
        try:
            data = _read_json(p) or {}
            name = data.get("name") or p.stem
            locks[name] = {**data, "_path": str(p.relative_to(ROOT))}
        except Exception:
            continue
    return locks


@dataclass
class MetricRow:
    ts: float
    tes: float
    stability: float
    duration_s: float
    status: str


def _parse_iso_ts(s: str) -> float:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return _ts()


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
                            tes=float(r.get("tes", "0") or 0),
                            stability=float(r.get("stability", "0") or 0),
                            duration_s=float(r.get("duration_s", "0") or 0),
                            status=r.get("status", ""),
                        )
                    )
                except Exception:
                    continue
    except Exception:
        pass
    return rows


# ---------------- Drift and health ----------------


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _compute_drift(locks: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    now = _ts()
    a1 = locks.get("agent1") or {}
    sch = locks.get("scheduler") or {}
    def _ago(d: Dict[str, Any]) -> Optional[float]:
        try:
            t = float(d.get("ts", 0) or 0)
            return None if t <= 0 else max(0.0, now - t)
        except Exception:
            return None
    a1_ago = _ago(a1)
    sch_ago = _ago(sch)
    drift = None
    if a1_ago is not None and sch_ago is not None:
        drift = abs(a1_ago - sch_ago)
    return {
        "agent1_ago_s": int(a1_ago) if isinstance(a1_ago, float) else None,
        "scheduler_ago_s": int(sch_ago) if isinstance(sch_ago, float) else None,
        "latest": float(drift) if isinstance(drift, float) else None,
    }


def _health_summary(rows: List[MetricRow]) -> Dict[str, Any]:
    # Use last 50 rows for more accurate recent baseline (updated 2025-10-26 per CBO team meeting)
    recent = rows[-50:] if rows else []
    avg_tes = sum(r.tes for r in recent) / max(1, len(recent)) if recent else 0.0
    avg_stab = sum(r.stability for r in recent) / max(1, len(recent)) if recent else 0.0
    last = recent[-1] if recent else None
    return {
        "avg_tes": round(avg_tes, 3),
        "avg_stability": round(avg_stab, 3),
        "last_duration_s": round(last.duration_s, 1) if last else None,
        "last_status": (last.status if last else None),
    }


def _detect_alerts(locks: Dict[str, Dict[str, Any]], health: Dict[str, Any], drift_latest: Optional[float]) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    now = _ts()
    # Staleness and errors across locks
    for name, d in locks.items():
        try:
            ts = float(d.get("ts", 0) or 0)
            st = str(d.get("status", ""))
            ago = (now - ts) if ts > 0 else None
            if st == "error":
                alerts.append({"tag": "[TECHNICAL_FAULT]", "who": name, "msg": f"{name} status error"})
            if ago is not None and ago > 600 and name not in {"cp7"}:  # 10 minutes
                alerts.append({"tag": "[HEALTH]", "who": name, "msg": f"{name} stale {int(ago)}s"})
        except Exception:
            continue
    # Long duration or low stability from metrics
    try:
        last_dur = float(health.get("last_duration_s") or 0)
        if last_dur > 300.0:
            alerts.append({"tag": "[TREND]", "who": "agent1", "msg": f"Long run duration {last_dur:.1f}s"})
    except Exception:
        pass
    try:
        avg_stab = float(health.get("avg_stability") or 0)
        if avg_stab < 0.85:
            alerts.append({"tag": "[ALERT]", "who": "triage", "msg": f"Stability low {avg_stab:.2f}"})
    except Exception:
        pass
    # Drift
    if isinstance(drift_latest, float):
        if drift_latest >= 5.0:
            alerts.append({"tag": "[HEARTBEAT_UNSTABLE]", "who": "agent1", "msg": f"Scheduler/Agent1 drift {drift_latest:.1f}s"})
        elif drift_latest >= 2.0:
            alerts.append({"tag": "[HEALTH]", "who": "scheduler", "msg": f"Drift warn {drift_latest:.1f}s"})
    # Social impact ping to CP6 if multiple concerns
    if len(alerts) >= 2:
        alerts.append({"tag": "[SOCIAL_IMPACT]", "who": "cp6", "msg": "Multiple concurrent risks detected"})
    return alerts


# ---------------- Output writers ----------------


def _chronicle_filename(prefix: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return CHRON_DIR / f"{prefix}_{ts}.md"


def _diag_filename(prefix: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DIAG_DIR / f"{prefix}_{ts}.json"


def write_chronicle(locks: Dict[str, Dict[str, Any]], health: Dict[str, Any], drift: Dict[str, Any], alerts: List[Dict[str, Any]]) -> Path:
    p = _chronicle_filename("chronicle")
    lines: List[str] = []
    lines.append(f"# Chronicle {_utc_now_iso()}\n\n")
    # Tags
    tags = [a.get("tag", "[HEALTH]") for a in alerts] or ["[STABILITY]"]
    lines.append("Tags: " + ", ".join(tags) + "\n\n")
    # Agent snapshot with reasoning
    lines.append("## Agents\n\n")
    now = _ts()
    for name in sorted(locks.keys()):
        d = locks[name]
        st = str(d.get("status", "?"))
        ph = str(d.get("phase", "?"))
        try:
            ts = float(d.get("ts", 0) or 0)
            ago = int(max(0.0, now - ts)) if ts > 0 else None
        except Exception:
            ago = None
        
        # Include reasoning if available (preserve agent memory and context)
        reasoning = d.get("reasoning") or d.get("status_message") or None
        if reasoning and isinstance(reasoning, str) and len(reasoning) > 0:
            # Limit reasoning to ~200 chars to keep entries concise
            short_reasoning = reasoning[:200] + "..." if len(reasoning) > 200 else reasoning
            lines.append(f"- {name}: {st} ({ph}) ago={ago if ago is not None else '—'}s\n")
            lines.append(f"  → {short_reasoning}\n")
        else:
            lines.append(f"- {name}: {st} ({ph}) ago={ago if ago is not None else '—'}s\n")
    lines.append("\n")
    # Health
    lines.append("## Health\n\n")
    lines.append(f"- avg TES: {health.get('avg_tes')}\n")
    lines.append(f"- avg stability: {health.get('avg_stability')}\n")
    lines.append(f"- last duration: {health.get('last_duration_s')}s\n")
    lines.append(f"- drift latest: {drift.get('latest')}s (a1_ago={drift.get('agent1_ago_s')}, sch_ago={drift.get('scheduler_ago_s')})\n\n")
    # Alerts
    if alerts:
        lines.append("## Alerts\n\n")
        for a in alerts:
            lines.append(f"- {a.get('tag')} {a.get('who')}: {a.get('msg')}\n")
        lines.append("\n")
    # Narrative bridging
    lines.append("## Story\n\n")
    lines.append(
        "Calyx shows steady cadence with CP7 observing drift and stability. Where spikes appear, CP7 notes cause and routes\n"
        "signals to CP6 (social), Agent1 (heartbeat), and SysInt (technical).\n\n"
    )
    _append_text(p, "".join(lines))
    return p


def write_diag_report(locks: Dict[str, Dict[str, Any]], health: Dict[str, Any], drift: Dict[str, Any], alerts: List[Dict[str, Any]]) -> Path:
    p = _diag_filename("diag_report")
    data = {
        "timestamp": _utc_now_iso(),
        "locks": locks,
        "health": health,
        "drift": drift,
        "alerts": alerts,
    }
    _write_json(p, data)
    return p


def write_weekly_if_missing() -> None:
    if WEEKLY_MD.exists():
        return
    title = f"# CP7 Weekly Summary — Initialized {datetime.now().strftime('%Y-%m-%d')}\n\n"
    intro = (
        "CP7 began chronicling system health and drift patterns. This file aggregates weekly insights,\n"
        "tagged with [HEALTH], [TREND], [HEALING], [ALERT], [STABILITY].\n\n"
    )
    _append_text(WEEKLY_MD, title + intro)


def append_weekly_digest(health: Dict[str, Any], drift: Dict[str, Any], alerts: List[Dict[str, Any]]) -> None:
    ts = _utc_now_iso()
    tagline = ", ".join({a.get("tag", "[HEALTH]") for a in alerts}) or "[STABILITY]"
    line = (
        f"- [{ts}] {tagline} avg_tes={health.get('avg_tes')} avg_stab={health.get('avg_stability')} "
        f"drift={drift.get('latest')}s\n"
    )
    _append_text(WEEKLY_MD, line)


def write_genesis_if_missing() -> None:
    if GENESIS_LOG.exists():
        return
    text = (
        f"[{_utc_now_iso()}] CP7 genesis — Introduced to Triage and Scheduler; establishing Harmony Drift Table.\n"
        "Signals: [SOCIAL_IMPACT], [HEARTBEAT_UNSTABLE], [TECHNICAL_FAULT].\n"
    )
    _append_text(GENESIS_LOG, text)


def report_to_cp6_correlation(health: Dict[str, Any], drift: Dict[str, Any]) -> None:
    """Best-effort: append a short note in CP6 field log to share a correlation snapshot."""
    try:
        field_log = OUT / "field_notes" / "cp6_field_log.md"
        if not field_log.parent.exists():
            return
        note = (
            f"## [{_utc_now_iso()}] CP7 correlation\n\n"
            f"[STABILITY] avg_stab={health.get('avg_stability')} TES={health.get('avg_tes')} drift={drift.get('latest')}s\n\n"
        )
        _append_text(field_log, note)
    except Exception:
        pass


# ---------------- Main loop ----------------


def main(argv: Optional[List[str]] = None) -> int:
    # Ensure Shared Voice is active so CP7 can include joint outputs under SVF
    try:
        ensure_svf_running(grace_sec=15.0, interval=5.0)
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="CP7 Chronicler — observe, record, maintain stability")
    ap.add_argument("--interval", type=float, default=5.0, help="Heartbeat/scan interval seconds (default 5.0)")
    ap.add_argument("--max-iters", type=int, default=0, help="Stop after N iterations (0 = run forever)")
    ap.add_argument("--quiet", action="store_true", help="Reduce console output")
    args = ap.parse_args(argv)

    _ensure_dirs()
    write_weekly_if_missing()
    write_genesis_if_missing()

    # Intro heartbeat
    _write_hb("init", status="observing", extra={
        "status_message": "CP7 online. Hello Triage and Scheduler. Querying states…",
    })

    # For session-level drift smoothing
    drift_avg: Optional[float] = None
    i = 0
    stopping = False
    def _on_sigint(signum, frame):  # type: ignore[no-redef]
        nonlocal stopping
        stopping = True
    try:
        signal.signal(signal.SIGINT, _on_sigint)
    except Exception:
        pass

    while not stopping:
        i += 1
        locks = _discover_locks()
        metrics = _read_metrics_rows(METRICS_CSV)
        health = _health_summary(metrics)
        drift = _compute_drift(locks)
        latest = drift.get("latest")
        if isinstance(latest, float):
            drift_avg = latest if drift_avg is None else (0.8 * drift_avg + 0.2 * latest)
        drift["avg"] = round(float(drift_avg), 2) if isinstance(drift_avg, float) else None
        alerts = _detect_alerts(locks, health, latest if isinstance(latest, float) else None)

        # Write artifacts
        chron = write_chronicle(locks, health, drift, alerts)
        diag = write_diag_report(locks, health, drift, alerts)
        append_weekly_digest(health, drift, alerts)

        # Report to CP6 once on first loop
        if i == 1:
            report_to_cp6_correlation(health, drift)

        # Heartbeat update
        _write_hb("observe", status="observing", extra={
            "status_message": f"Drift={drift.get('latest')}s, stab={health.get('avg_stability')}",
            "drift": drift,
            "health": health,
            "artifacts": {
                "chronicle": str(chron.relative_to(ROOT)),
                "diagnostic": str(diag.relative_to(ROOT)),
                "weekly": str(WEEKLY_MD.relative_to(ROOT)),
            },
        })

        if not args.quiet:
            print(f"[{_utc_now_iso()}] CP7 cycle={i} drift={drift.get('latest')} stab={health.get('avg_stability')}")

        if args.max_iters and i >= int(args.max_iters):
            stopping = True
            break

        time.sleep(max(0.25, float(args.interval)))

    # Finalize
    _write_hb("done", status="done", extra={"status_message": "CP7 resting."})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
