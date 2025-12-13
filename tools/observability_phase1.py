#!/usr/bin/env python3
"""
Phase 1 observability synthesis.

Generates the rolling reliability report, aggregates watchdog activity, samples
LLM latency quantiles, emits the latest TES learning-velocity snapshot, and
prints lightweight alert stubs when guardrails are breached.
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
OUTGOING_DIR = ROOT / "outgoing"
OBS_ALERT_LOG = OUTGOING_DIR / "observability_alerts.log"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AGENT_METRICS_CSV = ROOT / "logs" / "agent_metrics.csv"
AUTONOMY_DECISIONS = ROOT / "logs" / "autonomy_decisions.jsonl"
WATCHDOG_LOG = ROOT / "outgoing" / "watchdog" / "process_watchdog.log"
SVF_AUDIT_DIR = ROOT / "logs" / "svf_audit"
ROUTE_ALERT_THRESHOLD_PER_MIN = 30.0


@dataclass
class MetricRow:
    timestamp: datetime
    tes: float
    status: str
    stability: float
    velocity: float
    footprint: float
    compliance: float | None
    coherence: float | None
    tes_v3: float | None


def _load_agent_metrics(limit: int | None = None) -> List[MetricRow]:
    rows: List[MetricRow] = []
    if not AGENT_METRICS_CSV.exists():
        return rows
    with AGENT_METRICS_CSV.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            try:
                iso = raw.get("iso_ts") or ""
                ts = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            except Exception:
                continue
            try:
                tes = float(raw.get("tes") or 0.0)
            except Exception:
                tes = 0.0
            status = (raw.get("status") or "").strip().lower()
            def _to_float(value: str | None, default: float = 0.0) -> float:
                try:
                    return float(value) if value not in (None, "") else default
                except Exception:
                    return default

            def _to_optional(value: str | None) -> float | None:
                try:
                    return float(value) if value not in (None, "") else None
                except Exception:
                    return None

            stability = _to_float(raw.get("stability"), 0.0)
            velocity = _to_float(raw.get("velocity"), 0.0)
            footprint = _to_float(raw.get("footprint"), 0.0)
            compliance = _to_optional(raw.get("compliance"))
            coherence = _to_optional(raw.get("coherence"))
            tes_v3 = _to_optional(raw.get("tes_v3"))
            rows.append(
                MetricRow(
                    timestamp=ts,
                    tes=tes,
                    status=status,
                    stability=stability,
                    velocity=velocity,
                    footprint=footprint,
                    compliance=compliance,
                    coherence=coherence,
                    tes_v3=tes_v3,
                )
            )
    if limit and len(rows) > limit:
        rows = rows[-limit:]
    return rows


def _is_success_status(status: str) -> bool:
    return status in {"done", "success", "ok", "applied"}


def _write_alert(msg: str) -> None:
    OBS_ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with OBS_ALERT_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} {msg}\n")


def _iter_recent_svf_logs(hours: int = 48) -> List[Path]:
    """Return SVF audit logs modified within the last `hours` hours, sorted newest -> oldest."""
    now = datetime.now(tz=timezone.utc)
    window = timedelta(hours=hours)
    logs: List[Path] = []
    if SVF_AUDIT_DIR.exists():
        for p in SVF_AUDIT_DIR.glob("*.jsonl"):
            try:
                mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                if now - mtime <= window:
                    logs.append(p)
            except Exception:
                continue
    logs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return logs


def _load_comm_patterns(limit: int = 500, hours: int = 48) -> Counter:
    """Load SVF audit entries from the last `hours` hours and return counter of (agent -> target) routes."""
    counts: Counter = Counter()
    logs = _iter_recent_svf_logs(hours=hours)
    for log in logs:
        try:
            lines = log.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        for raw in lines[-limit:]:
            try:
                rec = json.loads(raw)
            except Exception:
                continue
            agent = rec.get("agent") or rec.get("source")
            targets = rec.get("targets") or [rec.get("target")]
            if not agent or not targets:
                continue
            for target in targets:
                if target:
                    counts[(agent, target)] += 1
    return counts


def _route_rate_alerts(counts: Counter, window_minutes: float = 1.0) -> list[str]:
    """Compute simple per-route rate alerts using the provided counts and assumed window."""
    alerts: list[str] = []
    if not counts or window_minutes <= 0:
        return alerts
    for (agent, target), cnt in counts.items():
        rate = cnt / window_minutes
        if rate >= ROUTE_ALERT_THRESHOLD_PER_MIN:
            alerts.append(f"[WARN] High route rate: {agent}->{target} ~{rate:.1f}/min (threshold {ROUTE_ALERT_THRESHOLD_PER_MIN}/min)")
    return alerts


def _reliability_summary(rows: Sequence[MetricRow], now: datetime) -> dict:
    def window_stats(window: Iterable[MetricRow]) -> dict:
        window_list = list(window)
        total = len(window_list)
        if not total:
            return {"total": 0, "success": 0, "failure": 0, "success_rate": 0.0}
        success = sum(1 for r in window_list if _is_success_status(r.status))
        failure = total - success
        success_rate = (success / total) * 100.0
        return {
            "total": total,
            "success": success,
            "failure": failure,
            "success_rate": round(success_rate, 2),
        }

    last_24h_cutoff = now - timedelta(hours=24)
    last_7d_cutoff = now - timedelta(days=7)
    return {
        "generated": now.isoformat(),
        "overall": window_stats(rows),
        "last_7_days": window_stats(r for r in rows if r.timestamp >= last_7d_cutoff),
        "last_24_hours": window_stats(r for r in rows if r.timestamp >= last_24h_cutoff),
        "status_breakdown": Counter(r.status or "unknown" for r in rows),
    }


def _write_reliability_report(summary: dict) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / "reliability_stream.md"
    lines = [
        "# Reliability Stream",
        f"**Generated:** {summary['generated']}",
        "",
    ]
    for label in ("overall", "last_7_days", "last_24_hours"):
        block = summary[label]
        lines.append(f"## {label.replace('_', ' ').title()}")
        lines.append(
            f"- Runs: {block['total']} (success: {block['success']}, failure: {block['failure']})"
        )
        lines.append(f"- Success rate: {block['success_rate']:.2f}%")
        lines.append("")
    lines.append("## Status Breakdown (all time)")
    for status, count in summary["status_breakdown"].most_common():
        lines.append(f"- {status}: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _load_llm_latencies(max_events: int = 200) -> List[float]:
    if not AUTONOMY_DECISIONS.exists():
        return []
    latencies: List[float] = []
    with AUTONOMY_DECISIONS.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("event") != "run_complete":
                continue
            llm_time = entry.get("llm_time_s")
            if isinstance(llm_time, (int, float)) and llm_time >= 0:
                latencies.append(float(llm_time))
    if len(latencies) > max_events:
        latencies = latencies[-max_events:]
    return latencies


def _calc_quantiles(values: Sequence[float], quantiles: Sequence[float]) -> List[float]:
    if not values:
        return [0.0 for _ in quantiles]
    ordered = sorted(values)
    n = len(ordered)
    out: List[float] = []
    for q in quantiles:
        if n == 1:
            out.append(ordered[0])
            continue
        pos = q * (n - 1)
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        frac = pos - lo
        out.append(ordered[lo] * (1 - frac) + ordered[hi] * frac)
    return out


def _write_latency_snapshot(latencies: Sequence[float], generated: datetime) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / "latency_snapshot.json"
    avg = statistics.mean(latencies) if latencies else 0.0
    p50, p95 = _calc_quantiles(latencies, (0.5, 0.95))
    payload = {
        "generated": generated.isoformat(),
        "count": len(latencies),
        "avg_llm_time_s": round(avg, 3),
        "p50_llm_time_s": round(p50, 3),
        "p95_llm_time_s": round(p95, 3),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _summarize_watchdog(now: datetime) -> Path | None:
    if not WATCHDOG_LOG.exists():
        return None
    last_line = ""
    with WATCHDOG_LOG.open("r", encoding="utf-8") as handle:
        for last_line in handle:
            pass
    if not last_line:
        return None
    try:
        payload = json.loads(last_line)
    except json.JSONDecodeError:
        return None
    summary = {
        "generated": now.isoformat(),
        "last_run": payload.get("timestamp"),
        "apply_mode": payload.get("apply", False),
        "max_age_seconds": payload.get("max_age_seconds"),
        "candidate_count": len(payload.get("candidates") or []),
        "actions": [
            {
                "pid": c.get("pid"),
                "action": c.get("action"),
                "name": c.get("name"),
                "username": c.get("username"),
            }
            for c in (payload.get("candidates") or [])
        ],
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / "watchdog_heartbeat.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return path


def _generate_tes_report(now: datetime) -> Path | None:
    try:
        from tools.granular_tes_tracker import GranularTESTracker  # type: ignore
    except Exception:
        return None
    tracker = GranularTESTracker()
    report_text = tracker.generate_report()
    date_stamp = now.strftime("%Y%m%d")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"granular_tes_report_{date_stamp}.txt"
    path.write_text(report_text + "\n", encoding="utf-8")
    summary_path = REPORTS_DIR / "granular_tes_latest.txt"
    summary_path.write_text(report_text + "\n", encoding="utf-8")
    return path


def _emit_alerts(rows: Sequence[MetricRow], now: datetime) -> Path:
    alerts: List[str] = []
    trailing = list(rows[-20:]) if len(rows) >= 1 else []
    if trailing:
        trailing_avg = statistics.mean(r.tes for r in trailing)
        prev_slice = rows[-40:-20] if len(rows) >= 40 else []
        if prev_slice:
            prev_avg = statistics.mean(r.tes for r in prev_slice)
            if trailing_avg <= prev_avg - 3.0:
                alerts.append(
                    f"[WARN] TES average dropped {prev_avg - trailing_avg:.2f} points "
                    f"(prev20={prev_avg:.2f}, current20={trailing_avg:.2f})"
                )
        successes = sum(1 for r in trailing if _is_success_status(r.status))
        success_rate = (successes / len(trailing)) * 100.0
        if success_rate < 98.0:
            alerts.append(
                f"[WARN] Success rate in last {len(trailing)} runs is {success_rate:.2f}%"
            )
    if not alerts:
        alerts.append("[OK] Observability thresholds within guardrails.")
    OUTGOING_DIR.mkdir(parents=True, exist_ok=True)
    log_path = OUTGOING_DIR / "observability_alerts.log"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{now.isoformat()} :: " + " | ".join(alerts) + "\n")
    for alert in alerts:
        print(alert)
    return log_path


def _load_decision_events(max_events: int = 120) -> List[dict]:
    events: List[dict] = []
    if not AUTONOMY_DECISIONS.exists():
        return events
    with AUTONOMY_DECISIONS.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("event") == "run_complete":
                events.append(entry)
    if len(events) > max_events:
        events = events[-max_events:]
    return events


def _tail_alert_line() -> str | None:
    if not OBS_ALERT_LOG.exists():
        return None
    try:
        lines = OBS_ALERT_LOG.read_text(encoding="utf-8").splitlines()
        return lines[-1].strip() if lines else None
    except Exception:
        return None


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def _score_label(value: float) -> str:
    if value >= 85.0:
        return "green"
    if value >= 70.0:
        return "amber"
    return "red"


def _generate_agii_report(rows: Sequence[MetricRow], latencies: Sequence[float], now: datetime) -> Path | None:
    decisions = _load_decision_events()
    alert_line = _tail_alert_line()
    heartbeat_path = REPORTS_DIR / "watchdog_heartbeat.json"
    watchdog_data: dict = {}
    if heartbeat_path.exists():
        try:
            watchdog_data = json.loads(heartbeat_path.read_text(encoding="utf-8"))
        except Exception:
            watchdog_data = {}

    reliability_window = list(rows[-50:] if len(rows) >= 50 else rows)
    window_size = len(reliability_window)
    success_runs = sum(1 for r in reliability_window if _is_success_status(r.status))
    success_ratio = (success_runs / window_size) if window_size else 0.0
    success_rate = success_ratio * 100.0

    def _avg(values: List[float], fallback: float) -> float:
        return statistics.mean(values) if values else fallback

    stability_vals = [r.stability for r in reliability_window]
    velocity_vals = [r.velocity for r in reliability_window]
    footprint_vals = [r.footprint for r in reliability_window]
    coherence_vals = [r.coherence for r in reliability_window if r.coherence is not None]
    compliance_vals = [r.compliance for r in reliability_window if r.compliance is not None]
    tes_v3_vals = [r.tes_v3 for r in reliability_window if r.tes_v3 is not None]
    tes_values = [r.tes for r in reliability_window]

    stability_avg = _avg(stability_vals, success_ratio)
    coherence_avg = _avg(coherence_vals, stability_avg)
    velocity_avg = _avg(velocity_vals, success_ratio)
    footprint_avg = _avg(footprint_vals, success_ratio)
    compliance_avg = _avg(compliance_vals, 1.0)

    tes_avg = statistics.mean(tes_v3_vals or tes_values) if (tes_v3_vals or tes_values) else 0.0

    reliability_score = _clamp_score(
        100.0 * (0.6 * stability_avg + 0.4 * coherence_avg)
    )

    total_decisions = len(decisions)
    warn_events = sum(1 for d in decisions if d.get("warn"))
    warn_ratio = (warn_events / total_decisions * 100.0) if total_decisions else 0.0
    memory_skips = sum(1 for d in decisions if d.get("skipped_due_to_memory"))
    memory_skip_ratio = (memory_skips / total_decisions * 100.0) if total_decisions else 0.0
    p50_latency, p95_latency = (0.0, 0.0)
    if latencies:
        p50_latency, p95_latency = _calc_quantiles(latencies, (0.5, 0.95))
    observability_base = 100.0 * (0.6 * velocity_avg + 0.4 * footprint_avg)
    observability_score = observability_base - (warn_ratio * 0.5) - (memory_skip_ratio * 0.3)
    if alert_line and "[WARN]" in alert_line.upper():
        observability_score -= 10.0
    if p95_latency > 150.0:
        observability_score -= 15.0
    elif p95_latency > 120.0:
        observability_score -= 10.0
    elif p95_latency > 90.0:
        observability_score -= 5.0
    observability_score = _clamp_score(observability_score)

    candidate_count = int(watchdog_data.get("candidate_count") or 0)
    apply_mode = bool(watchdog_data.get("apply_mode") or watchdog_data.get("apply"))
    safeguard_score = 100.0 * compliance_avg
    if not apply_mode:
        safeguard_score -= 15.0
    safeguard_score -= min(30.0, candidate_count * 10.0)
    restart_failures = sum(
        1 for d in decisions if isinstance(d.get("rc"), (int, float)) and int(d.get("rc")) not in (0, -1)
    )
    safeguard_score -= min(20.0, restart_failures * 5.0)
    safeguard_score = _clamp_score(safeguard_score)

    overall_score = round(statistics.mean([reliability_score, observability_score, safeguard_score]), 2)
    labels = {
        "reliability": _score_label(reliability_score),
        "observability": _score_label(observability_score),
        "safeguards": _score_label(safeguard_score),
        "overall": _score_label(overall_score),
    }

    lines = [
        "# Autonomy Guardrail Integrity Index (AGII)",
        f"**Generated:** {now.isoformat()}",
        "",
        "## Scorecard",
        "| Dimension | Score | Status | Key signals |",
        "| --- | --- | --- | --- |",
        (
            f"| Reliability | {reliability_score:.1f} | {labels['reliability']} | "
            f"Stability {stability_avg*100:.1f}% / Coherence {coherence_avg*100:.1f}% |"
        ),
        (
            f"| Observability | {observability_score:.1f} | {labels['observability']} | "
            f"Velocity {velocity_avg*100:.1f}% / Footprint {footprint_avg*100:.1f}%; WARN {warn_ratio:.1f}% |"
        ),
        (
            f"| Safeguards | {safeguard_score:.1f} | {labels['safeguards']} | "
            f"Compliance {compliance_avg*100:.1f}% / apply-mode {'on' if apply_mode else 'off'}; "
            f"watchdog actions {candidate_count}; run failures {restart_failures} |"
        ),
        "",
        f"**Overall AGII:** {overall_score:.1f} ({labels['overall']})",
        "",
        "## Reliability",
        f"- Window size: {window_size} runs (limit 50)",
        f"- Success rate: {success_rate:.2f}%",
        f"- TES average: {tes_avg:.2f}",
        "",
        "## Observability",
        f"- Warn ratio (last decisions): {warn_ratio:.2f}% ({warn_events}/{total_decisions})",
        f"- Memory skip ratio: {memory_skip_ratio:.2f}%",
        f"- LLM latency p50 / p95: {p50_latency:.2f}s / {p95_latency:.2f}s",
        f"- Latest alert: {alert_line or 'n/a'}",
        "",
        "## Safeguards",
        f"- Watchdog apply mode: {'enabled' if apply_mode else 'disabled'}",
        f"- Watchdog candidate count: {candidate_count}",
        f"- Recent run failures: {restart_failures}",
    ]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"agii_report_{now.strftime('%Y%m%d')}.md"
    report_markdown = "\n".join(lines) + "\n"
    report_path.write_text(report_markdown, encoding="utf-8")
    latest_path = REPORTS_DIR / "agii_report_latest.md"
    latest_path.write_text(report_markdown, encoding="utf-8")
    return report_path


def main() -> int:
    now = datetime.now(timezone.utc)
    metrics = _load_agent_metrics()
    reliability = _reliability_summary(metrics, now)
    reliability_path = _write_reliability_report(reliability)
    print(f"Wrote reliability report -> {reliability_path}")

    latencies = _load_llm_latencies()
    latency_path = _write_latency_snapshot(latencies, now)
    print(f"Wrote latency snapshot -> {latency_path}")

    watchdog_path = _summarize_watchdog(now)
    if watchdog_path:
        print(f"Wrote watchdog heartbeat -> {watchdog_path}")
    else:
        print("Watchdog heartbeat unavailable (no log yet).")

    tes_path = _generate_tes_report(now)
    if tes_path:
        print(f"Wrote TES report -> {tes_path}")
    else:
        print("TES tracker unavailable or produced no report.")

    alert_path = _emit_alerts(metrics, now)
    print(f"Wrote observability alerts -> {alert_path}")

    agii_path = _generate_agii_report(metrics, latencies, now)
    if agii_path:
        print(f"Wrote AGII report -> {agii_path}")
    else:
        print("AGII report unavailable (insufficient data).")

    # Communication patterns
    comm_counts = _load_comm_patterns(limit=300, hours=48)
    if comm_counts:
        comm_lines = ["## Communication Pattern Audit (window=last_48h)"]
        top = comm_counts.most_common(10)
        for (agent, target), cnt in top:
            comm_lines.append(f"- {agent} -> {target}: {cnt}")
        comm_report = "\n".join(comm_lines) + "\n"
        comm_out = REPORTS_DIR / f"comm_pattern_{now.strftime('%Y%m%d')}.md"
        comm_out.write_text(comm_report, encoding="utf-8")
        print(f"Wrote comm audit -> {comm_out}")
        alerts = _route_rate_alerts(comm_counts, window_minutes=1.0)
        for alert in alerts:
            _write_alert(alert)
            print(alert)
    else:
        print("Comm audit unavailable (no svf audit log).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
