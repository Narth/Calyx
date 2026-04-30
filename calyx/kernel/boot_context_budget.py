"""Boot context-missing budget evaluator and outbound observe-mode guard."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .event_ledger import clear_system_phase, emit, set_system_phase
from .paths import resolve_ledger_dir, resolve_repo_root, resolve_runtime_dir


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _iter_events(repo_root: Path, since_minutes: int = 120) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    ledger_dir = resolve_ledger_dir(repo_root)
    rows: list[tuple[datetime, dict[str, Any]]] = []
    for p in sorted(ledger_dir.glob("station_events__*.jsonl")):
        try:
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                ts = _parse_ts(rec.get("ts") or rec.get("ts_utc"))
                if ts and ts >= cutoff:
                    rows.append((ts, rec))
        except Exception:
            continue
    rows.sort(key=lambda x: x[0])
    return [r for _, r in rows]


def _iter_all_events(repo_root: Path) -> list[dict[str, Any]]:
    ledger_dir = resolve_ledger_dir(repo_root)
    rows: list[tuple[datetime, dict[str, Any]]] = []
    for p in sorted(ledger_dir.glob("station_events__*.jsonl")):
        try:
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                ts = _parse_ts(rec.get("ts") or rec.get("ts_utc"))
                if ts:
                    rows.append((ts, rec))
        except Exception:
            continue
    rows.sort(key=lambda x: x[0])
    return [r for _, r in rows]


def _load_policy(repo_root: Path) -> dict[str, Any]:
    p = repo_root / "policy" / "boot_context_budget.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    return data


def _observe_marker_path(repo_root: Path) -> Path:
    return resolve_runtime_dir(repo_root) / "observe_mode_forced.json"


def _boot_marker_path(repo_root: Path) -> Path:
    return resolve_runtime_dir(repo_root) / "boot_evidence_marker.json"


def _load_boot_marker(repo_root: Path) -> dict[str, Any]:
    p = _boot_marker_path(repo_root)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _caller_guidance(evaluation_scope: str, success: bool) -> str:
    if evaluation_scope == "recent_window":
        if success:
            return "recent_window_observation_only; do_not_treat_as_boot_session_truth_without_current_boot_context"
        return "recent_window_boot_evidence_not_found; refresh_derived_truth_and_check_current_boot_before_interpreting_as_boot_failure"
    if success:
        return "current_boot_session_scoped_result"
    return "current_boot_lookup_failed; refresh_derived_truth_and_verify_boot_session_identity_before_interpreting"


def is_observe_mode_forced(repo_root: Path | None = None) -> tuple[bool, dict[str, Any]]:
    root = (repo_root or resolve_repo_root()).resolve()
    p = _observe_marker_path(root)
    if not p.exists():
        return False, {}
    try:
        return True, json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return True, {"reason": "observe_marker_invalid"}


def assert_outbound_allowed_or_fail(component: str, reason: str = "boot_context_budget_exceeded") -> None:
    forced, marker = is_observe_mode_forced()
    if not forced:
        return
    set_system_phase("boot")
    try:
        emit(
            "ERROR",
            component,
            "governance.assertion.failed",
            "Outbound blocked: observe mode forced",
            data={
                "reason": reason,
                "observe_mode_forced": True,
                "marker_reason": marker.get("reason", ""),
            },
        )
    finally:
        clear_system_phase()
    raise RuntimeError(f"observe_mode_forced: {reason}")


def _evaluate_boot_context_budget_from_boot_event(
    policy: dict[str, Any],
    events: list[dict[str, Any]],
    boot_event: dict[str, Any] | None,
    *,
    evaluation_scope: str,
    boot_session_resolution: str,
    since_minutes: int | None = None,
    boot_session_id: str = "",
) -> dict[str, Any]:
    if not boot_event:
        return {
            "ok": False,
            "reason": "boot_evidence_event_missing",
            "evaluation_scope": evaluation_scope,
            "boot_session_resolution": boot_session_resolution,
            "boot_session_id": boot_session_id,
            "since_minutes": since_minutes,
            "caller_guidance": _caller_guidance(evaluation_scope, False),
            "boot_context_missing_total": 0,
            "boot_context_missing_by_component": {},
            "budget_pass": False,
            "budget_fail_reasons": ["boot_evidence_event_missing"],
            "policy": policy,
        }
    boot_start = _parse_ts(boot_event.get("ts") or boot_event.get("ts_utc"))
    if boot_start is None:
        return {
            "ok": False,
            "reason": "boot_evidence_ts_invalid",
            "evaluation_scope": evaluation_scope,
            "boot_session_resolution": boot_session_resolution,
            "boot_session_id": boot_session_id or (boot_event.get("data") or {}).get("boot_session_id", ""),
            "since_minutes": since_minutes,
            "caller_guidance": _caller_guidance(evaluation_scope, False),
            "boot_context_missing_total": 0,
            "boot_context_missing_by_component": {},
            "budget_pass": False,
            "budget_fail_reasons": ["boot_evidence_ts_invalid"],
            "policy": policy,
        }
    window_seconds = int(policy.get("boot_window_seconds", 60))
    boot_end = boot_start + timedelta(seconds=window_seconds)

    heartbeat_after = [
        _parse_ts(e.get("ts") or e.get("ts_utc"))
        for e in events
        if e.get("event") == "heartbeat.tick" and _parse_ts(e.get("ts") or e.get("ts_utc")) and _parse_ts(e.get("ts") or e.get("ts_utc")) >= boot_start
    ]
    if heartbeat_after:
        hb_min = min(t for t in heartbeat_after if t is not None)
        if hb_min and hb_min < boot_end:
            boot_end = hb_min

    def in_window(rec: dict[str, Any]) -> bool:
        ts = _parse_ts(rec.get("ts") or rec.get("ts_utc"))
        if ts is None:
            return False
        return boot_start <= ts <= boot_end

    missing_events = [
        e for e in events
        if in_window(e) and (e.get("causal_envelope") or {}).get("causal_kind") == "missing"
    ]
    by_component: dict[str, int] = {}
    for e in missing_events:
        comp = str(e.get("component") or "unknown")
        by_component[comp] = by_component.get(comp, 0) + 1

    allowed = policy.get("allowed_components", {})
    total_budget = int(policy.get("total_budget", 0))
    total = sum(by_component.values())

    fail_reasons: list[str] = []
    for comp, count in by_component.items():
        comp_budget = int((allowed.get(comp) or {}).get("budget", 0))
        if comp not in allowed:
            fail_reasons.append(f"component_not_allowed:{comp}")
        elif count > comp_budget:
            fail_reasons.append(f"component_budget_exceeded:{comp}:{count}>{comp_budget}")
    if total > total_budget:
        fail_reasons.append(f"total_budget_exceeded:{total}>{total_budget}")

    return {
        "ok": True,
        "reason": "ok",
        "evaluation_scope": evaluation_scope,
        "boot_session_resolution": boot_session_resolution,
        "boot_session_id": boot_session_id or (boot_event.get("data") or {}).get("boot_session_id", ""),
        "since_minutes": since_minutes,
        "caller_guidance": _caller_guidance(evaluation_scope, True),
        "boot_window_start_ts_utc": boot_start.isoformat(),
        "boot_window_end_ts_utc": boot_end.isoformat(),
        "boot_context_missing_total": total,
        "boot_context_missing_by_component": by_component,
        "allowed_components": allowed,
        "total_budget": total_budget,
        "budget_pass": len(fail_reasons) == 0,
        "budget_fail_reasons": fail_reasons,
        "policy": policy,
    }


def evaluate_current_boot_context_budget(
    repo_root: Path | None = None,
    *,
    boot_session_id: str | None = None,
) -> dict[str, Any]:
    root = (repo_root or resolve_repo_root()).resolve()
    policy = _load_policy(root)
    marker = _load_boot_marker(root)
    resolved_boot_session_id = (boot_session_id or marker.get("boot_session_id") or "").strip()
    events = _iter_all_events(root)
    boot_commits = [e for e in events if e.get("event") == "boot.evidence.bundle.committed"]
    boot_event = None
    resolution = "explicit_boot_session_id" if boot_session_id else "boot_marker"

    if resolved_boot_session_id:
        for rec in reversed(boot_commits):
            if ((rec.get("data") or {}).get("boot_session_id") or "") == resolved_boot_session_id:
                boot_event = rec
                break
    else:
        resolution = "latest_boot_commit_fallback"
        if boot_commits:
            boot_event = boot_commits[-1]

    return _evaluate_boot_context_budget_from_boot_event(
        policy,
        events,
        boot_event,
        evaluation_scope="current_boot",
        boot_session_resolution=resolution,
        boot_session_id=resolved_boot_session_id,
    )


def evaluate_recent_window_for_boot_context_budget(
    repo_root: Path | None = None,
    *,
    since_minutes: int = 120,
) -> dict[str, Any]:
    root = (repo_root or resolve_repo_root()).resolve()
    policy = _load_policy(root)
    events = _iter_events(root, since_minutes=since_minutes)
    boot_commits = [e for e in events if e.get("event") == "boot.evidence.bundle.committed"]
    boot_event = boot_commits[-1] if boot_commits else None
    resolved_boot_session_id = ""
    if boot_event:
        resolved_boot_session_id = ((boot_event.get("data") or {}).get("boot_session_id") or "").strip()
    return _evaluate_boot_context_budget_from_boot_event(
        policy,
        events,
        boot_event,
        evaluation_scope="recent_window",
        boot_session_resolution="recent_window_scan",
        since_minutes=since_minutes,
        boot_session_id=resolved_boot_session_id,
    )


def evaluate_boot_context_budget(repo_root: Path | None = None, since_minutes: int = 120) -> dict[str, Any]:
    return evaluate_current_boot_context_budget(repo_root)


def enforce_boot_context_budget(repo_root: Path | None = None, since_minutes: int = 120) -> dict[str, Any]:
    root = (repo_root or resolve_repo_root()).resolve()
    result = evaluate_current_boot_context_budget(root)
    runtime_dir = resolve_runtime_dir(root)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    marker_path = _observe_marker_path(root)

    if result.get("budget_pass"):
        if marker_path.exists():
            marker_path.unlink(missing_ok=True)
        set_system_phase("boot")
        try:
            emit(
                "INFO",
                "kernel",
                "audit.boot_context_budget.summary",
                "Boot context budget evaluated",
                data={
                    "boot_context_missing_total": result["boot_context_missing_total"],
                    "boot_context_missing_by_component": result["boot_context_missing_by_component"],
                    "budget_pass": True,
                },
            )
        finally:
            clear_system_phase()
        result["observe_mode_forced"] = False
        return result

    marker = {
        "schema": "runtime.observe_mode_forced.v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "reason": "boot_context_budget_exceeded",
        "boot_context_missing_total": result.get("boot_context_missing_total", 0),
        "boot_context_missing_by_component": result.get("boot_context_missing_by_component", {}),
        "budget_fail_reasons": result.get("budget_fail_reasons", []),
        "budget_pass": False,
    }
    marker_path.write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8")
    set_system_phase("boot")
    try:
        emit(
            "ERROR",
            "kernel",
            "audit.boot_context_budget.exceeded",
            "Boot context missing budget exceeded; forcing observe mode",
            data={
                "reason": "boot_context_budget_exceeded",
                "boot_context_missing_total": result.get("boot_context_missing_total", 0),
                "boot_context_missing_by_component": result.get("boot_context_missing_by_component", {}),
                "budget_fail_reasons": result.get("budget_fail_reasons", []),
            },
        )
        emit(
            "ERROR",
            "kernel",
            "governance.assertion.failed",
            "Observe mode forced due to boot context budget exceedance",
            data={
                "reason": "boot_context_budget_exceeded",
                "observe_mode_forced": True,
                "marker_path": str(marker_path),
            },
        )
    finally:
        clear_system_phase()
    result["observe_mode_forced"] = True
    return result


def _main() -> int:
    parser = argparse.ArgumentParser(description="Boot context budget evaluator")
    parser.add_argument("--since-minutes", type=int, default=120)
    parser.add_argument("--enforce", action="store_true")
    parser.add_argument("--mode", choices=["current_boot", "recent_window"], default="current_boot")
    parser.add_argument("--boot-session-id", default="")
    args = parser.parse_args()
    if args.enforce:
        out = enforce_boot_context_budget()
    elif args.mode == "recent_window":
        out = evaluate_recent_window_for_boot_context_budget(since_minutes=args.since_minutes)
    else:
        out = evaluate_current_boot_context_budget(boot_session_id=args.boot_session_id or None)
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("budget_pass", False) else 3


if __name__ == "__main__":
    raise SystemExit(_main())
