#!/usr/bin/env python
"""
TES helper: summarize BloomOS kernel seed telemetry.

Observation-only:
- Reads logs/bloomos/kernel_seed_observations.jsonl
- Writes reports/tes_kernel_seed_summary.md
- No config writes, no gating, no autonomy changes.
"""

import json
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "logs" / "bloomos" / "kernel_seed_observations.jsonl"
REPORT_PATH = REPO_ROOT / "reports" / "tes_kernel_seed_summary.md"


def load_observations():
    if not LOG_PATH.exists():
        return []

    observations = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                observations.append(json.loads(line))
            except json.JSONDecodeError:
                # Keep going; TES is observational only.
                continue
    return observations


def summarize(observations: list[dict]) -> tuple[dict, dict]:
    """
    Build a summary over all kernel seed observations and return:
      - summary: aggregate booleans + latest gate info
      - latest: the most recent observation dict (or {} if none)
    """

    def gate(obs: dict) -> dict:
        """Return a safe bloom_gate dict (never None)."""
        bg = obs.get("bloom_gate")
        return bg if isinstance(bg, dict) else {}

    count = len(observations)

    if not observations:
        # No observations yet – keep everything explicit but safe.
        summary = {
            "count": 0,
            "ever_activation_true": False,
            "ever_non_conceptual_status": False,
            "gate_status": "UNKNOWN",
            "activation_allowed": False,
        }
        return summary, {}

    # Aggregate over all observations
    ever_activation_true = any(
        bool(gate(obs).get("activation_allowed")) for obs in observations
    )

    # We treat anything *other than* these as “non-conceptual”
    conceptual_markers = {"CONCEPTUAL_ONLY", "conceptual_only"}

    ever_non_conceptual_status = any(
        isinstance(gate(obs).get("bloom_status"), str)
        and gate(obs)["bloom_status"] not in conceptual_markers
        for obs in observations
    )

    # Latest observation and its gate
    latest = observations[-1]
    latest_gate = gate(latest)

    summary = {
        "count": count,
        "ever_activation_true": ever_activation_true,
        "ever_non_conceptual_status": ever_non_conceptual_status,
        "gate_status": latest_gate.get("bloom_status", "UNKNOWN"),
        "activation_allowed": bool(latest_gate.get("activation_allowed")),
    }

    return summary, latest




def write_report(summary: dict, latest: dict) -> None:
    """
    Render a human-readable TES summary for the kernel seed.
    """

    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "tes_kernel_seed_summary.md"

    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    count = summary.get("count", 0)
    ever_activation_true = summary.get("ever_activation_true", False)
    ever_non_conceptual_status = summary.get("ever_non_conceptual_status", False)
    gate_status = summary.get("gate_status", "UNKNOWN")
    activation_allowed = summary.get("activation_allowed", False)

    lines: list[str] = []
    lines.append("# TES Summary – Kernel Seed Safe Mode")
    lines.append("")
    lines.append(f"- Generated at: **{now}**")
    lines.append(f"- Total observations: **{count}**")
    lines.append(f"- Ever `activation_allowed = true`: **{ever_activation_true}**")
    lines.append(
        f"- Ever non-conceptual `bloom_status`: **{ever_non_conceptual_status}**"
    )
    lines.append(f"- Latest `bloom_status`: **{gate_status}**")
    lines.append(f"- Latest `activation_allowed`: **{activation_allowed}**")
    lines.append("")
    lines.append("## Latest Observation Snapshot")
    lines.append("")
    if latest:
        # Pretty-print the latest observation as JSON
        try:
            latest_json = json.dumps(latest, indent=2, sort_keys=True)
        except Exception:
            latest_json = str(latest)
        lines.append("```json")
        lines.append(latest_json)
        lines.append("```")
    else:
        lines.append("_No observations found in logs/bloomos/kernel_seed_observations.jsonl_")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote TES kernel seed summary to {report_path}")



def main():
    observations = load_observations()
    summary, latest = summarize(observations)
    write_report(summary, latest)


if __name__ == "__main__":
    main()
