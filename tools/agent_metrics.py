#!/usr/bin/env python3
"""
Tool Efficacy Score (TES) computation and logging for Agent1 runs.

We log per-run metrics to logs/agent_metrics.csv to enable comparisons between
conservative (safe) runs and more autonomous modes.

Scoring model (0..100):
- Stability (50%): 1.0 if final status == 'done' and no failure indicated; else 0.0
- Velocity (30%): 1.0 at fast<=90s, 0.0 at slow>=900s (linear in-between)
- Footprint (20%): 1.0 with <=1 files changed, 0.0 with >=10 files changed (linear)

We also emit a human hint to "invite innovation" once stability is good:
- If Stability==1.0 and Velocity>=0.5 and current mode is conservative, suggest
  enabling tests or apply+tests, depending on context.

Note: No external dependencies; writes CSV with headers when creating a new file.
"""
from __future__ import annotations
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
LOG_CSV = ROOT / "logs" / "agent_metrics.csv"
GRANULAR_LOG = ROOT / "logs" / "granular_tes.jsonl"
TES_SCHEMA_VERSION = 3


@dataclass
class RunContext:
    ts: float
    run_dir: str
    duration_s: float
    status: str  # 'done' | 'error' | etc.
    applied: bool
    changed_files_count: int
    run_tests: bool
    failure: bool
    model_id: str | None
    autonomy_mode: str  # 'safe' | 'tests' | 'apply' | 'apply_tests'
    agent_id: int = 1
    compliance: Optional[float] = None
    ethics: Optional[float] = None
    coherence: Optional[float] = None


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _velocity_score(duration_s: float, fast: float = 90.0, slow: float = 900.0) -> float:
    if duration_s <= fast:
        return 1.0
    if duration_s >= slow:
        return 0.0
    return _clamp01(1.0 - (duration_s - fast) / (slow - fast))


def _footprint_score(changed_files_count: int, small: int = 1, large: int = 10) -> float:
    if changed_files_count <= small:
        return 1.0
    if changed_files_count >= large:
        return 0.0
    # linear drop between small..large
    return _clamp01(1.0 - (changed_files_count - small) / float(large - small))


def _stability_score(status: str, failure: bool, mode: str, applied: bool) -> float:
    """
    Graduated stability scoring based on context.
    
    Args:
        status: Run status ('done', 'error', etc.)
        failure: Whether tests/validation failed
        mode: Autonomy mode ('safe', 'tests', 'apply', 'apply_tests')
        applied: Whether changes were actually applied
    
    Returns:
        Stability score 0.0 to 1.0
    """
    # If not done, no stability
    if status != "done":
        return 0.0
    
    # If no failure, perfect stability
    if not failure:
        return 1.0
    
    # If failure but in tests mode without applying changes
    # Grant partial credit (test failures are less severe when not applied)
    if mode == "tests" and not applied:
        # Partial credit: tests failed but no changes applied
        # This reflects that planning succeeded, only validation failed
        return 0.6
    
    # If failure in apply mode, more severe penalty
    if mode in ("apply", "apply_tests") and applied:
        # Applied changes but tests failed - significant issue
        return 0.2
    
    # Other failure cases
    return 0.0


def compute_scores(ctx: RunContext) -> Dict[str, float]:
    stability = _stability_score(ctx.status, ctx.failure, ctx.autonomy_mode, ctx.applied)
    velocity = _velocity_score(ctx.duration_s)
    footprint = _footprint_score(ctx.changed_files_count)
    tes_v2 = round(100.0 * (0.5 * stability + 0.3 * velocity + 0.2 * footprint), 1)

    def _norm(value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        try:
            return _clamp01(float(value))
        except Exception:
            return None

    ethics = _norm(ctx.ethics)
    compliance = _norm(ctx.compliance)
    if compliance is None and ethics is not None:
        compliance = ethics
    coherence = _norm(ctx.coherence)

    compliance_for_formula = compliance if compliance is not None else stability
    coherence_for_formula = coherence if coherence is not None else stability
    tes_v3 = round(
        100.0
        * (
            0.4 * stability
            + 0.2 * velocity
            + 0.15 * footprint
            + 0.15 * compliance_for_formula
            + 0.10 * coherence_for_formula
        ),
        1,
    )

    return {
        "stability": stability,
        "velocity": velocity,
        "footprint": footprint,
        "tes": tes_v2,
        "tes_v3": tes_v3,
        "compliance": compliance,
        "ethics": ethics,
        "coherence": coherence,
    }


def _autonomy_hint(ctx: RunContext, scores: Dict[str, float]) -> str:
    # Invite innovation: if stable and reasonably fast, suggest bumping autonomy
    # Updated threshold: stable if >0.8 (allows partial credit in tests mode)
    if scores["stability"] >= 0.8 and scores["velocity"] >= 0.5:
        if ctx.autonomy_mode == "safe":
            return "Consider enabling --run-tests for validation"
        if ctx.autonomy_mode == "tests":
            return "Consider enabling --apply --run-tests"
    return ""


def log_run_metrics(ctx: RunContext) -> None:
    scores = compute_scores(ctx)
    hint = _autonomy_hint(ctx, scores)

    LOG_CSV.parent.mkdir(parents=True, exist_ok=True)
    new_file = not LOG_CSV.exists()

    with LOG_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow([
                "iso_ts",
                "tes",
                "stability",
                "velocity",
                "footprint",
                "duration_s",
                "status",
                "applied",
                "changed_files",
                "run_tests",
                "autonomy_mode",
                "model_id",
                "run_dir",
                "hint",
                "compliance",
                "ethics",
                "coherence",
                "tes_v3",
                "tes_schema",
            ])
        iso_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

        def _fmt_optional(value: Optional[float]) -> str:
            if value is None:
                return ""
            return f"{value:.3f}"

        writer.writerow([
            iso_ts,
            scores["tes"],
            round(scores["stability"], 3),
            round(scores["velocity"], 3),
            round(scores["footprint"], 3),
            round(ctx.duration_s, 1),
            ctx.status,
            int(ctx.applied),
            ctx.changed_files_count,
            int(ctx.run_tests),
            ctx.autonomy_mode,
            ctx.model_id or "",
            ctx.run_dir,
            hint,
            _fmt_optional(scores.get("compliance")),
            _fmt_optional(scores.get("ethics")),
            _fmt_optional(scores.get("coherence")),
            scores.get("tes_v3"),
            TES_SCHEMA_VERSION,
        ])

    _append_granular_entry(ctx, scores)


def _append_granular_entry(ctx: RunContext, scores: Dict[str, float]) -> None:
    """Persist per-agent TES record for adaptive monitoring."""
    try:
        GRANULAR_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": f"agent{int(ctx.agent_id)}",
            "task_type": ctx.autonomy_mode,
            "phase": ctx.autonomy_mode,
            "tes": scores["tes"],
            "tes_v3": scores.get("tes_v3"),
            "stability": scores["stability"],
            "velocity": scores["velocity"],
            "footprint": scores["footprint"],
            "compliance": scores.get("compliance"),
            "ethics": scores.get("ethics"),
            "coherence": scores.get("coherence"),
            "duration": round(ctx.duration_s, 1),
            "success": ctx.status == "done" and not ctx.failure,
            "status": ctx.status,
            "applied": bool(ctx.applied),
            "run_tests": bool(ctx.run_tests),
            "changed_files": ctx.changed_files_count,
            "model_id": ctx.model_id or "",
            "run_dir": ctx.run_dir,
        }
        with GRANULAR_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # Per-agent telemetry is best-effort; never fail the main logging path.
        pass


__all__ = [
    "RunContext",
    "compute_scores",
    "log_run_metrics",
    "TES_SCHEMA_VERSION",
]
