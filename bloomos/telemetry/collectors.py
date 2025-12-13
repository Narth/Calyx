"""
Passive telemetry collectors (read-only).

Aggregates host health and advisory summaries from existing Station Calyx logs.
No actions are taken. Safe Mode enforced.
"""

from __future__ import annotations

import csv
import json
import os
from typing import Any, Dict, Optional

AGII_REPORT = os.path.join("reports", "agii_report_latest.md")
TES_METRICS = os.path.join("logs", "agent_metrics.csv")
CAS_EVENTS = os.path.join("logs", "cas", "events.jsonl")
FORECASTS = os.path.join("logs", "predictive_forecasts.jsonl")
EARLY_WARNINGS = os.path.join("logs", "early_warnings.jsonl")


def _load_last_csv(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
            return rows[-1] if rows else None
    except Exception:
        return None


def _load_last_jsonl(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    last = None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    last = json.loads(line)
                except Exception:
                    continue
        return last
    except Exception:
        return None


def _load_text(path: str) -> Optional[str]:
    if not os.path.exists(path):
        return None
    try:
        return open(path, "r", encoding="utf-8").read()
    except Exception:
        return None


def collect() -> Dict[str, Any]:
    """
    Return a passive telemetry state dict.
    """
    return {
        "tes_last": _load_last_csv(TES_METRICS),
        "agii_text": _load_text(AGII_REPORT),
        "cas_last": _load_last_jsonl(CAS_EVENTS),
        "forecast_last": _load_last_jsonl(FORECASTS),
        "early_warning_last": _load_last_jsonl(EARLY_WARNINGS),
    }


__all__ = ["collect"]
