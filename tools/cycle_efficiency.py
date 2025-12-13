#!/usr/bin/env python3
"""
SVF Cycle — periodic efficiency check + new vote + tie detection.

Behavior:
- Every --interval seconds (default 90), generate a new efficiency report and ballot
  using tools/svf_efficiency.py.
- Tally all votes across ballots. If a tie occurs for the top count (and total votes > 0),
  emit a tie decree and exit to request outside assistance.
- Otherwise, continue the cycle.

Outputs (when events occur):
- Shared report(s):       outgoing/shared_logs/svf_efficiency_<ts>.md
- Vote ballot(s):         outgoing/dialogues/svf_vote_<ts>.md
- Tie decree (on tie):    outgoing/overseer_reports/verdicts/DECREE_<date>_SVF_TIE.md
- Cycle status logs:      outgoing/shared_logs/svf_cycle_status_<ts>.md
"""
from __future__ import annotations

import argparse
import subprocess
import time
import sys
from pathlib import Path
from typing import Dict, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
SHARED_LOGS = OUT / "shared_logs"
VERDICTS = OUT / "overseer_reports" / "verdicts"

# Import tally helpers from svf_efficiency
try:
    # Allow running as module
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.svf_efficiency import _tally_votes, _proposals, _read_metrics, _summary, METRICS_CSV  # type: ignore
except Exception:
    _tally_votes = None  # type: ignore


def _write_status(msg: str) -> Path:
    ts = int(time.time())
    SHARED_LOGS.mkdir(parents=True, exist_ok=True)
    p = SHARED_LOGS / f"svf_cycle_status_{ts}.md"
    lines = [
        "[C:REPORT] — SVF Efficiency Cycle Status",
        "",
        msg,
        "",
        "Generated under Shared Voice Protocol v1.0",
    ]
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def _tie(counts: Dict[str, int]) -> Tuple[bool, int, int]:
    total = sum(counts.values())
    if total <= 0:
        return False, 0, total
    top = max(counts.values()) if counts else 0
    winners = [k for k, v in counts.items() if v == top and top > 0]
    return (len(winners) >= 2), top, total


def _write_tie_decree(counts: Dict[str, int]) -> Path:
    VERDICTS.mkdir(parents=True, exist_ok=True)
    date = time.strftime("%Y-%m-%d")
    p = VERDICTS / f"DECREE_{date}_SVF_TIE.md"
    lines = [
        "[C:DECREE] — SVF Optimization Tie",
        "",
        "Subject: Tie detected; outside assistance requested",
        "",
        "Tally:",
    ]
    for k in sorted(counts.keys()):
        lines.append(f"- {k}: {counts[k]}")
    lines.extend([
        "",
        "Action:",
        "- Escalate to human oversight / outside assistance to break the tie.",
        "",
        "Generated under Shared Voice Protocol v1.0",
    ])
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="SVF Cycle — periodic monitor and voting")
    ap.add_argument("--interval", type=float, default=90.0, help="Seconds between cycles")
    ap.add_argument("--max-cycles", type=int, default=0, help="Stop after N cycles (0=infinite)")
    args = ap.parse_args(argv)

    cycles = 0
    _write_status("SVF cycle monitor started.")
    while True:
        cycles += 1
        # Wait interval
        try:
            time.sleep(max(1.0, float(args.interval)))
        except Exception:
            time.sleep(90.0)
        # Step 1: run efficiency analyzer to produce report + ballot
        try:
            subprocess.run([sys.executable, "-u", "tools/svf_efficiency.py"], cwd=str(ROOT), check=False)
        except Exception:
            pass
        # Step 2: tally votes and check tie
        counts = {"A": 0, "B": 0, "C": 0}
        try:
            if _tally_votes is not None:
                counts, _by_agent = _tally_votes()
        except Exception:
            pass
        tied, top, total = _tie(counts)
        if tied:
            dec = _write_tie_decree(counts)
            _write_status(f"Tie detected (top={top}, total={total}). Decree -> {dec}")
            break
        else:
            _write_status(f"Cycle {cycles} complete: no tie (top={top}, total votes={total}).")
        if args.max_cycles and cycles >= args.max_cycles:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
