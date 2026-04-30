#!/usr/bin/env python3
"""
Signal Examiner - converts Station telemetry into bounded advisory signals.

Reads local runtime/STATE/outgoing artifacts only.
Writes:
  runtime/signals/current_signal_digest.json
  runtime/signals/signal_events.jsonl
  runtime/signals/operator_brief.md
  outgoing/signal_examiner.lock
"""
from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from runtime_truth import add_truth_metadata, load_json


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "runtime"
OUTGOING = REPO_ROOT / "outgoing"
SIGNALS_DIR = RUNTIME / "signals"
STATE_PATH = REPO_ROOT / "STATE.md"

SEVERITY_RANK = {"none": 0, "advisory": 1, "warning": 2, "critical": 3}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_state() -> dict[str, str]:
    values: dict[str, str] = {}
    if not STATE_PATH.exists():
        return values
    try:
        for line in STATE_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            if key:
                values[key] = value.strip()
    except OSError:
        pass
    return values


def _tail_jsonl(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: deque[dict[str, Any]] = deque(maxlen=limit)
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rows.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return list(rows)


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(",") if part.strip() and part.strip().lower() != "none"]


def _parse_checks(checks: str) -> tuple[list[str], list[str]]:
    failed: list[str] = []
    ok: list[str] = []
    for part in _split_csv(checks):
        if "=" not in part:
            continue
        name, status = part.split("=", 1)
        name = name.strip()
        status = status.strip().lower()
        if status == "fail":
            failed.append(name)
        elif status in {"ok", "pass"}:
            ok.append(name)
    return failed, ok


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _add_signal(
    signals: list[dict[str, Any]],
    *,
    signal_id: str,
    severity: str,
    confidence: float,
    summary: str,
    why: str,
    evidence: list[str],
    recommended_action: str,
    requires_operator_confirmation: bool = False,
    governance_weight: str = "normal",
) -> None:
    signals.append(
        {
            "signal_id": signal_id,
            "severity": severity,
            "confidence": round(max(0.0, min(1.0, confidence)), 2),
            "classification": "signal",
            "summary": summary,
            "why": why,
            "evidence": evidence,
            "recommended_action": recommended_action,
            "authority": "advisory_only",
            "requires_operator_confirmation": requires_operator_confirmation,
            "governance_weight": governance_weight,
        }
    )


def _recent_health_pattern(history: list[dict[str, Any]]) -> dict[str, Any]:
    if not history:
        return {"samples": 0}
    samples = history[-12:]
    cpu_values = [float(row.get("cpu_pct")) for row in samples if row.get("cpu_pct") is not None]
    ram_values = [float(row.get("ram_pct")) for row in samples if row.get("ram_pct") is not None]
    health_values = [str(row.get("health") or "").lower() for row in samples]
    return {
        "samples": len(samples),
        "cpu_avg": round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else None,
        "cpu_max": round(max(cpu_values), 1) if cpu_values else None,
        "ram_avg": round(sum(ram_values) / len(ram_values), 1) if ram_values else None,
        "ram_max": round(max(ram_values), 1) if ram_values else None,
        "non_pass_count": sum(1 for value in health_values if value and value not in {"pass", "ok"}),
    }


def examine(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    global REPO_ROOT, RUNTIME, OUTGOING, SIGNALS_DIR, STATE_PATH
    REPO_ROOT = repo_root
    RUNTIME = repo_root / "runtime"
    OUTGOING = repo_root / "outgoing"
    SIGNALS_DIR = RUNTIME / "signals"
    STATE_PATH = repo_root / "STATE.md"

    state = _read_state()
    health = load_json(RUNTIME / "station_health.json") or {}
    service_failure = load_json(RUNTIME / "service_failure_status.json") or {}
    topology = load_json(RUNTIME / "runtime_topology_snapshot.json") or {}
    heartbeat = load_json(RUNTIME / "station_heartbeat.json") or {}
    cp6 = load_json(OUTGOING / "cp6.lock") or {}
    cp7 = load_json(OUTGOING / "cp7.lock") or {}
    cp9 = load_json(OUTGOING / "cp9.lock") or {}
    history = _tail_jsonl(RUNTIME / "station_health_history.jsonl", 24)

    signals: list[dict[str, Any]] = []
    failed_checks, ok_checks = _parse_checks(state.get("checks", ""))
    health_status = str(state.get("health") or health.get("health") or "unknown").lower()
    runtime_truth_state = str(state.get("runtime_truth_state") or "").lower()
    topology_truth_state = str(state.get("runtime_topology_truth_state") or "").lower()
    topology_risk = str(state.get("runtime_topology_risk") or "unknown").upper()
    active_services = _split_csv(state.get("runtime_topology_active_services", ""))
    duplicates = _split_csv(state.get("runtime_topology_duplicates", ""))
    ambiguous = _split_csv(state.get("runtime_topology_authority_ambiguous", ""))
    failure_count = _as_int(state.get("failure_flags_active"), 0)
    failure_services = _split_csv(state.get("failure_flag_services", ""))
    history_pattern = _recent_health_pattern(history)

    if len(failed_checks) >= 2 and active_services:
        confidence = 0.78 + min(0.17, len(failed_checks) * 0.03)
        _add_signal(
            signals,
            signal_id="service-coherence-loss",
            severity="critical" if len(failed_checks) >= 4 else "warning",
            confidence=confidence,
            summary="Canonical services are failing while Station support loops remain active.",
            why="This indicates the Station may be breathing through support loops while core operator surfaces are not coherently available.",
            evidence=[
                f"STATE.md: checks={state.get('checks', '')}",
                f"STATE.md: runtime_topology_active_services={state.get('runtime_topology_active_services', '')}",
            ],
            recommended_action="Run patch_readiness, then consider governed full sunrise if the failure set persists.",
            requires_operator_confirmation=True,
            governance_weight="high",
        )

    if health_status in {"pass", "ok"} and failed_checks:
        _add_signal(
            signals,
            signal_id="health-service-contradiction",
            severity="warning",
            confidence=0.82,
            summary="Hardware health is passing while service checks are failing.",
            why="A pass health reading does not imply operational coherence when service liveness disagrees.",
            evidence=[
                f"STATE.md: health={state.get('health', '')}",
                f"STATE.md: checks={state.get('checks', '')}",
            ],
            recommended_action="Treat health as load readiness only; inspect service failures before adding work.",
            requires_operator_confirmation=False,
        )

    if runtime_truth_state == "stale" or topology_truth_state == "stale":
        stale_surfaces = []
        if runtime_truth_state == "stale":
            stale_surfaces.append("STATE.md/runtime truth")
        if topology_truth_state == "stale":
            stale_surfaces.append("runtime topology")
        _add_signal(
            signals,
            signal_id="truth-surface-staleness",
            severity="warning",
            confidence=0.86,
            summary="One or more derived truth surfaces are stale.",
            why="Stale advisory surfaces reduce confidence in automated summaries and increase operator inspection burden.",
            evidence=[
                f"STATE.md: runtime_truth_state={state.get('runtime_truth_state', '')}",
                f"STATE.md: runtime_topology_truth_state={state.get('runtime_topology_truth_state', '')}",
                f"STATE.md: runtime_truth_label={state.get('runtime_truth_label', '')}",
            ],
            recommended_action="Refresh STATE through the governed heartbeat path before relying on summaries.",
            requires_operator_confirmation=False,
        )

    if topology_risk == "CRITICAL" or duplicates or ambiguous:
        _add_signal(
            signals,
            signal_id="topology-authority-ambiguity",
            severity="critical" if topology_risk == "CRITICAL" else "warning",
            confidence=0.9 if topology_risk == "CRITICAL" else 0.76,
            summary="Runtime topology shows duplicate or authority-ambiguous services.",
            why="Duplicate loops and ambiguous authority can make the Station appear active while weakening singular operational understanding.",
            evidence=[
                f"STATE.md: runtime_topology_risk={state.get('runtime_topology_risk', '')}",
                f"STATE.md: runtime_topology_duplicates={state.get('runtime_topology_duplicates', '')}",
                f"STATE.md: runtime_topology_authority_ambiguous={state.get('runtime_topology_authority_ambiguous', '')}",
            ],
            recommended_action="Inspect runtime_topology_snapshot.json and normalize duplicate/ambiguous service ownership.",
            requires_operator_confirmation=True,
            governance_weight="high",
        )

    if failure_count > 0:
        _add_signal(
            signals,
            signal_id="service-failure-watch-active",
            severity="warning" if failure_count < 4 else "critical",
            confidence=0.84,
            summary="Service failure watch reports active failure flags.",
            why="Failure flags are an explicit cross-service signal, not a single noisy probe.",
            evidence=[
                f"runtime/service_failure_status.json: active_count={failure_count}",
                f"STATE.md: failure_flag_services={state.get('failure_flag_services', '')}",
                f"STATE.md: failure_risk_lane={state.get('failure_risk_lane', '')}",
            ],
            recommended_action="Use the failure risk lane to decide between single-service restart and full sunrise candidate.",
            requires_operator_confirmation=True,
        )

    if history_pattern.get("samples", 0) >= 6:
        cpu_max = history_pattern.get("cpu_max")
        ram_max = history_pattern.get("ram_max")
        non_pass_count = int(history_pattern.get("non_pass_count") or 0)
        if (cpu_max is not None and cpu_max >= 90) or (ram_max is not None and ram_max >= 90) or non_pass_count >= 4:
            _add_signal(
                signals,
                signal_id="recent-resource-instability",
                severity="warning",
                confidence=0.72,
                summary="Recent health history shows repeated resource stress or non-pass samples.",
                why="Persistence across samples is stronger than an isolated resource spike.",
                evidence=[
                    f"runtime/station_health_history.jsonl: samples={history_pattern.get('samples')}",
                    f"runtime/station_health_history.jsonl: cpu_max={cpu_max} ram_max={ram_max} non_pass_count={non_pass_count}",
                ],
                recommended_action="Defer heavy work or let Navigator cool the cadence until recent samples stabilize.",
                requires_operator_confirmation=False,
            )

    if not signals:
        top_level = "none"
        top_signal = "none"
        operator_brief = "No cohesive operational signal detected. Current telemetry reads as routine noise or insufficient evidence."
    else:
        signals.sort(key=lambda row: (SEVERITY_RANK.get(row["severity"], 0), row["confidence"]), reverse=True)
        top_level = signals[0]["severity"]
        top_signal = signals[0]["signal_id"]
        operator_brief = signals[0]["summary"]

    digest = {
        "schema": "station.signal_digest.v1",
        "tool": "signal_examiner",
        "ts_utc": _utc_now_iso(),
        "authority": "advisory_only",
        "authority_boundary_note": "Signal Examiner may notice, correlate, summarize, and recommend. It may not execute remediation or expand authority.",
        "signal_level": top_level,
        "top_signal": top_signal,
        "signal_count": len(signals),
        "requires_operator_confirmation": any(bool(s.get("requires_operator_confirmation")) for s in signals),
        "operator_brief": operator_brief,
        "observed_context": {
            "failed_checks": failed_checks,
            "ok_checks": ok_checks,
            "health": health_status,
            "runtime_truth_state": runtime_truth_state or "unknown",
            "runtime_topology_truth_state": topology_truth_state or "unknown",
            "runtime_topology_risk": topology_risk,
            "active_services": active_services,
            "failure_count": failure_count,
            "failure_services": failure_services,
            "cp6_harmony": (cp6.get("harmony") or {}),
            "cp7_diagnostics": (cp7.get("diagnostics") or {}),
            "cp9_recommendations": (cp9.get("recommendations") or [])[:5],
            "heartbeat_truth_state": heartbeat.get("truth_state", "unknown"),
            "topology_schema": topology.get("schema", ""),
            "service_failure_schema": service_failure.get("schema", ""),
            "recent_health_pattern": history_pattern,
        },
        "signals": signals,
    }
    return add_truth_metadata(digest, "signal_digest")


def write_artifacts(digest: dict[str, Any]) -> None:
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    OUTGOING.mkdir(parents=True, exist_ok=True)

    digest_path = SIGNALS_DIR / "current_signal_digest.json"
    digest_path.write_text(json.dumps(digest, indent=2), encoding="utf-8")

    lock = {
        "tool": "signal_examiner",
        "ts_utc": digest.get("ts_utc"),
        "signal_level": digest.get("signal_level"),
        "top_signal": digest.get("top_signal"),
        "signal_count": digest.get("signal_count"),
        "operator_brief": digest.get("operator_brief"),
        "authority": "advisory_only",
        "digest_path": str(digest_path.relative_to(REPO_ROOT)).replace("\\", "/"),
    }
    lock = add_truth_metadata(lock, "signal_digest")
    (OUTGOING / "signal_examiner.lock").write_text(json.dumps(lock, indent=2), encoding="utf-8")

    brief = [
        "# Station Signal Brief",
        "",
        f"ts_utc: {digest.get('ts_utc', '')}",
        f"signal_level: {digest.get('signal_level', 'unknown')}",
        f"top_signal: {digest.get('top_signal', 'unknown')}",
        f"signal_count: {digest.get('signal_count', 0)}",
        f"requires_operator_confirmation: {str(digest.get('requires_operator_confirmation', False)).lower()}",
        "",
        str(digest.get("operator_brief") or ""),
        "",
        "Authority: advisory_only. No remediation is authorized by this artifact.",
    ]
    (SIGNALS_DIR / "operator_brief.md").write_text("\n".join(brief) + "\n", encoding="utf-8")

    if digest.get("signal_count", 0) > 0:
        event = {
            "ts_utc": digest.get("ts_utc"),
            "signal_level": digest.get("signal_level"),
            "top_signal": digest.get("top_signal"),
            "signal_count": digest.get("signal_count"),
            "requires_operator_confirmation": digest.get("requires_operator_confirmation"),
            "operator_brief": digest.get("operator_brief"),
        }
        with (SIGNALS_DIR / "signal_events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Examine local Station telemetry for cohesive operational signals.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Station Calyx repository root")
    parser.add_argument("--json", action="store_true", help="Print digest JSON to stdout")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    digest = examine(repo_root)
    write_artifacts(digest)
    if args.json:
        print(json.dumps(digest, indent=2))
    else:
        print(
            "signal_level={level} top_signal={top} signal_count={count}".format(
                level=digest.get("signal_level"),
                top=digest.get("top_signal"),
                count=digest.get("signal_count"),
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
