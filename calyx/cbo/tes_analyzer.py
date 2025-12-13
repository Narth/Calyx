"""Analyze TES (Tool Efficacy Score) trends for Station Calyx."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional


@dataclass(slots=True)
class TesSummary:
    """Lightweight summary of TES performance."""

    available: bool
    sample_count: int
    latest_tes: Optional[float]
    mean_last_20: Optional[float]
    velocity_last_20: Optional[float]
    last_updated: Optional[str]
    trend: str
    details: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "sample_count": self.sample_count,
            "latest_tes": self.latest_tes,
            "mean_last_20": self.mean_last_20,
            "velocity_last_20": self.velocity_last_20,
            "last_updated": self.last_updated,
            "trend": self.trend,
            "details": self.details,
        }


class TesAnalyzer:
    """Reads logs/agent_metrics.csv and exposes TES trend information."""

    def __init__(self, root: Path) -> None:
        self.metrics_path = root / "logs" / "agent_metrics.csv"

    def compute_summary(self, *, limit: int = 200) -> TesSummary:
        """Return TES summary, focusing on recent history."""

        if not self.metrics_path.exists():
            return TesSummary(
                available=False,
                sample_count=0,
                latest_tes=None,
                mean_last_20=None,
                velocity_last_20=None,
                last_updated=None,
                trend="unknown",
                details={"reason": "metrics_file_missing"},
            )

        rows = self._read_rows(limit=limit)
        if not rows:
            return TesSummary(
                available=False,
                sample_count=0,
                latest_tes=None,
                mean_last_20=None,
                velocity_last_20=None,
                last_updated=None,
                trend="unknown",
                details={"reason": "no_rows"},
            )

        tes_values = [row["tes"] for row in rows if row.get("tes") is not None]
        if not tes_values:
            return TesSummary(
                available=False,
                sample_count=len(rows),
                latest_tes=None,
                mean_last_20=None,
                velocity_last_20=None,
                last_updated=rows[-1].get("iso_ts"),
                trend="unknown",
                details={"reason": "no_tes_values"},
            )

        latest = tes_values[-1]
        last_updated = rows[-1].get("iso_ts")
        last_20 = tes_values[-20:]
        mean_20 = mean(last_20) if last_20 else None

        last_10 = tes_values[-10:]
        prev_10 = tes_values[-20:-10]
        velocity = None
        if last_10 and prev_10:
            velocity = mean(last_10) - mean(prev_10)

        trend = "stable"
        if velocity is not None:
            if velocity >= 1.0:
                trend = "improving"
            elif velocity <= -1.0:
                trend = "declining"

        details = {
            "window_last_20": len(last_20),
            "window_last_10": len(last_10),
            "window_prev_10": len(prev_10),
        }

        return TesSummary(
            available=True,
            sample_count=len(tes_values),
            latest_tes=latest,
            mean_last_20=mean_20,
            velocity_last_20=velocity,
            last_updated=last_updated,
            trend=trend,
            details=details,
        )

    def _read_rows(self, *, limit: int) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        try:
            with self.metrics_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    records.append(self._normalize_row(row))
        except Exception:
            return []
        if limit > 0:
            records = records[-limit:]
        return records

    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = dict(row)
        iso_ts = row.get("iso_ts") or row.get("timestamp")
        normalized["iso_ts"] = str(iso_ts) if iso_ts else None
        normalized["tes"] = self._parse_float(row.get("tes"))
        return normalized

    @staticmethod
    def _parse_float(value: Any) -> Optional[float]:
        if value in (None, "", "nan"):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
