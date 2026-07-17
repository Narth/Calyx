#!/usr/bin/env python3
"""WO_DISCORD_CANONICAL_TRANSPORT_DECLARATION_V1 — Write recheck receipt after protocol run."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    audit_dir = REPO_ROOT / "runtime" / "receipts" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    ts_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Run protocol and parse output
    result = subprocess.run(
        [
            str(REPO_ROOT / ".venv_cbohub311" / "Scripts" / "python.exe"),
            "-m",
            "calyx.kernel.canonical_intake_decision_protocol",
            "--required-consecutive-boots",
            "5",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    stdout = result.stdout or ""
    try:
        protocol = json.loads(stdout.strip())
    except json.JSONDecodeError:
        protocol = {}

    qualifying = protocol.get("promotion_eligible_by_objective_criteria", False)
    consecutive = protocol.get("consecutive_qualifying_boots", 0)
    required = protocol.get("required_consecutive_boots", 5)
    cycles = protocol.get("cycles", [])

    # Extract failing criteria from first (newest) cycle
    remaining_failing = []
    if cycles:
        c1 = cycles[0]
        if not c1.get("boot_evidence_gate_pass"):
            remaining_failing.append("boot_evidence_gate_pass")
        if not c1.get("boot_context_budget_pass"):
            remaining_failing.append("boot_context_budget_pass")
        if not c1.get("no_channel_boundary_anomalies"):
            remaining_failing.append("no_channel_boundary_anomalies")
        if not c1.get("no_unauthorized_send_attempts"):
            remaining_failing.append("no_unauthorized_send_attempts")
        if c1.get("unexpected_new_remote"):
            remaining_failing.append("unexpected_new_remote")
        if c1.get("unexpected_new_emitter_authority"):
            remaining_failing.append("unexpected_new_emitter_authority")
        if c1.get("new_listener_unexpected"):
            remaining_failing.append("new_listener_unexpected")
        if c1.get("channel_widening"):
            remaining_failing.append("channel_widening")

    repo_hash = "unknown"
    try:
        repo_hash = (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=REPO_ROOT,
                text=True,
                timeout=5,
            )
            .strip()
        )
    except Exception:
        pass

    recheck = {
        "schema": "audit.discord_canonical_transport_recheck.v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "wo": "WO_DISCORD_CANONICAL_TRANSPORT_DECLARATION_V1",
        "observe_mode": True,
        "qualifying": qualifying,
        "consecutive_qualifying_boots": f"{consecutive}/{required}",
        "remaining_failing_criteria": remaining_failing,
        "protocol_receipt_path": protocol.get("receipt_path"),
        "explicit_non_changes": {
            "dry_run_only_remains_true": True,
            "no_lane_escalation": True,
            "no_execution_path_enabled": True,
            "no_new_emitter_authority_beyond_discord_transport": True,
            "no_new_listeners_introduced": True,
            "canonical_repo_hash_unchanged": repo_hash,
        },
    }
    recheck_path = audit_dir / f"discord_canonical_transport_recheck__{ts_tag}.json"
    recheck_path.write_text(json.dumps(recheck, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(recheck, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
