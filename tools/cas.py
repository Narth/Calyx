#!/usr/bin/env python3
"""
CAS v0.1 utilities

Implements the Calyx Autonomy Score per the v0.1 spec:
- clamp
- HTI' calculation
- CTC normalization
- per-task CAS
- rolling station CAS
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
CAS_CFG = ROOT / "config" / "cas.yaml"

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def clamp(x: float, a: float, b: float) -> float:
    return max(a, min(b, x))


def load_config() -> Dict[str, Any]:
    cfg: Dict[str, Any] = {}
    if yaml and CAS_CFG.exists():
        try:
            cfg = yaml.safe_load(CAS_CFG.read_text(encoding="utf-8")) or {}
        except Exception:
            cfg = {}
    return cfg


def hti_prime(hti: float) -> float:
    try:
        val = 1.0 / (1.0 + float(hti))
    except Exception:
        val = 0.0
    return clamp(val, 0.0, 1.0)


def normalize_ctc(usd: float, wall_time_sec: float, tokens: float, medians: Dict[str, float]) -> float:
    """
    Normalize cost/time/compute into [0,1], higher = more expensive.
    Heuristic: compute ratios vs medians, take max ratio, map 1x->0, 2x->~0.33, 4x->1.
    """
    usd_med = float(medians.get("usd", 0.02) or 0.02)
    time_med = float(medians.get("wall_time_sec", 120.0) or 120.0)
    tok_med = float(medians.get("tokens", 2500) or 2500)
    ratios = []
    for val, med in ((usd, usd_med), (wall_time_sec, time_med), (tokens, tok_med)):
        try:
            if med > 0:
                ratios.append(float(val) / float(med))
        except Exception:
            continue
    if not ratios:
        return 0.0
    max_ratio = max(ratios)
    # map ratio to [0,1]: at 1x =>0, 4x=>1, linear between
    score = (max_ratio - 1.0) / 3.0
    return clamp(score, 0.0, 1.0)


def cas_for_task(metrics: Dict[str, Any], medians: Dict[str, float]) -> float:
    cfg = load_config()
    weights = cfg.get("weights", {}) or {}
    w_ifcr = float(weights.get("IFCR", 0.35))
    w_hti = float(weights.get("HTI_prime", -0.20))
    w_srr = float(weights.get("SRR", 0.15))
    w_ctc = float(weights.get("CTC", -0.10))
    w_sft = float(weights.get("SFT", 0.05))
    w_rhr = float(weights.get("RHR", 0.05))
    clamp_min = float(cfg.get("clamp_min", 0.0))
    clamp_max = float(cfg.get("clamp_max", 1.0))

    ifcr = float(metrics.get("IFCR", 0))
    hti_p = hti_prime(float(metrics.get("HTI", 0)))
    srr = float(metrics.get("SRR", 0))
    ctc = metrics.get("CTC")
    if ctc is None:
        # If missing, try to compute from costs if present
        cost = metrics.get("cost", {})
        usd = float(cost.get("usd", 0.0))
        sec = float(cost.get("wall_time_sec", 0.0))
        toks = float(cost.get("tokens", 0.0))
        ctc = normalize_ctc(usd, sec, toks, medians)
    else:
        ctc = float(ctc)
    sft = float(metrics.get("SFT", 0))
    rhr = float(metrics.get("RHR", 0))

    raw = (
        w_ifcr * ifcr
        + w_hti * hti_p
        + w_srr * srr
        + w_ctc * ctc
        + w_sft * sft
        + w_rhr * rhr
    )
    return clamp(raw, clamp_min, clamp_max)


def station_cas(task_rows: Iterable[Dict[str, Any]], days: int = 30) -> Dict[str, Any]:
    cfg = load_config()
    rolling_days = int(cfg.get("rolling_days", days))
    diffs = cfg.get("difficulty_weights", {}) or {}
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=rolling_days)

    total_weight = 0.0
    weighted_sum = 0.0
    sample_size = 0
    per_agent: Dict[str, List[float]] = {}

    for row in task_rows:
        try:
            ts = datetime.fromisoformat(row.get("ended_at", "").replace("Z", "+00:00"))
        except Exception:
            continue
        if ts < cutoff:
            continue
        cas_val = float(row.get("cas", 0.0))
        difficulty = (row.get("difficulty") or "normal").lower()
        weight = float(diffs.get(difficulty, 1.0))
        weighted_sum += cas_val * weight
        total_weight += weight
        sample_size += 1
        agent = row.get("agent_id") or "unknown"
        per_agent.setdefault(agent, []).append(cas_val)

    station = weighted_sum / total_weight if total_weight > 0 else 0.0
    level = "LOW"
    if station > 0.7:
        level = "HIGH"
    elif station > 0.4:
        level = "MEDIUM"

    per_agent_avg = {k: (sum(v) / len(v)) for k, v in per_agent.items()}
    return {
        "station_cas": station,
        "cas_level": level,
        "window_days": rolling_days,
        "sample_size": sample_size,
        "per_agent": per_agent_avg,
    }


def load_events(path: Path) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if not path.exists():
        return events
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                events.append(json.loads(line.strip()))
            except Exception:
                continue
    return events


def main() -> int:
    # Simple self-test: load cfg and print medians
    cfg = load_config()
    print(json.dumps(cfg, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
