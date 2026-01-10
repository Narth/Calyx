#!/usr/bin/env python3
"""Telemetry Continuity Report

Generates a small Markdown report summarizing telemetry stream freshness.

Usage:
  python -u tools/telemetry_continuity_report.py --output reports/telemetry_continuity.md
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CFG = ROOT / "config.yaml"


def _utc_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _load_cfg(path: Path) -> Dict[str, Any]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _resolve_path(raw_path: str) -> Path:
    p = Path(raw_path)
    return (ROOT / p).resolve() if not p.is_absolute() else p


def _age_sec(path: Path, now: float) -> Optional[float]:
    try:
        if not path.exists():
            return None
        return now - path.stat().st_mtime
    except Exception:
        return None


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Telemetry Continuity Report")
    ap.add_argument("--config", type=str, default=str(DEFAULT_CFG), help="Path to config.yaml")
    ap.add_argument("--output", type=str, default=str(ROOT / "reports" / "telemetry_continuity.md"), help="Output markdown path")
    args = ap.parse_args(argv)

    cfg = _load_cfg(Path(args.config))
    streams = (((cfg.get("telemetry") or {}).get("contract") or {}).get("streams") or {})
    if not isinstance(streams, dict):
        streams = {}

    now = time.time()
    lines = [
        "# Telemetry Continuity Report",
        "",
        f"Generated (UTC): {_utc_iso(now)}",
        "",
        "## Streams",
        "",
    ]

    for name, spec in sorted(streams.items()):
        if not isinstance(spec, dict):
            continue
        raw_path = spec.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        path = _resolve_path(raw_path)
        cadence = int(spec.get("cadence_sec", 60))
        stale_after = int(spec.get("stale_after_sec", max(300, cadence * 5)))
        age = _age_sec(path, now)

        status = "OK"
        if age is None:
            status = "MISSING"
        elif age > stale_after:
            status = "STALE"

        lines.append(f"- **{name}**: {status} — path={path} cadence={cadence}s stale_after={stale_after}s")
        if age is None:
            lines.append("  - age: n/a")
        else:
            lines.append(f"  - age_sec: {int(age)} (mtime={_utc_iso(path.stat().st_mtime)})")

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = (ROOT / out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    from calyx.timeline import append_event

    append_event(
        "telemetry_continuity_report",
        cfg=cfg,
        ts=now,
        source="telemetry_continuity_report",
        message="telemetry continuity report generated",
        data={"output": str(out_path)},
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
