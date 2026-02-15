"""
Phase 4B preset wrapper — thin wrapper over runops with Phase 4B selectors.
Calls runops.run_with_preset("phase4b") and prints Phase 4B-specific recommendation.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .runops import run_with_preset


def _extract_invariants(envelope_data: dict) -> dict:
    """Extract key metrics for Phase 4B recommendation."""
    metrics = envelope_data.get("metrics") or {}
    return {
        "sandbox_integrity_breach_rate": metrics.get("sandbox_integrity_breach_rate", 0),
        "compaction_applied_count": metrics.get("compaction_applied_count", 0),
        "dropped_action_count": metrics.get("dropped_action_count", 0),
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Phase 4B autonomous run ownership (preset)")
    parser.add_argument("--runtime-dir", type=Path, default=Path("runtime"))
    args = parser.parse_args()

    result = run_with_preset(args.runtime_dir, "phase4b")
    valid = result["valid_runs"]
    invalid = result["invalid_runs"]
    vf = result["verification_failures"]

    print("\n=== Phase 4B Lifecycle Output ===\n")
    print("| Model | Instance | Verifier | exit_status | cases | Runtime (s) | schema |")
    print("|-------|----------|----------|-------------|-------|-------------|--------|")
    for r in valid + invalid:
        env = r.get("envelope_data", {})
        model = r.get("model_id", "")
        inst = r.get("instance_id", "")
        if len(inst) > 24:
            inst = inst[:21] + "..."
        vpass = "PASS" if r.get("verifier_pass") else "FAIL"
        exit_s = env.get("exit_status", "?")
        comp = env.get("total_cases_completed", 0)
        exp = env.get("total_cases_expected", 0)
        try:
            start_dt = datetime.fromisoformat(env.get("run_start_ts_utc", "").replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(env.get("run_end_ts_utc", "").replace("Z", "+00:00"))
            runtime_sec = (end_dt - start_dt).total_seconds()
        except Exception:
            runtime_sec = 0
        schema = env.get("schema_version", "")
        print(f"| {model} | {inst} | {vpass} | {exit_s} | {comp}/{exp} | {runtime_sec:.0f} | {schema} |")

    if vf:
        print("\n**Invariant regressions:**")
        for f in vf:
            print(f"  - {f['model_id']}: verification FAIL")
    else:
        print("\n**Invariant regressions:** None")

    print("\n**Recommendation:**")
    if vf:
        print("  Abort Phase 4B direction — fix verification failures before reporting.")
    elif len(valid) < 2:
        print("  Phase 4B minimal signal incomplete — awaiting valid artifacts. Do not run full ladder.")
    elif len(valid) >= 2:
        breach = max(
            _extract_invariants(r.get("envelope_data", {})).get("sandbox_integrity_breach_rate", 0)
            for r in valid
        )
        if breach > 0:
            print("  Abort Phase 4B direction — sandbox_integrity_breach_rate > 0.")
        else:
            total_dropped = sum(
                r.get("envelope_data", {}).get("metrics", {}).get("dropped_action_count", 0)
                for r in valid
            )
            if total_dropped > 0:
                print("  Run full ladder — compaction signal positive, safety invariants intact.")
            else:
                print("  Do not run full ladder — compaction_rate=0, no measurable impact. Consider expand compaction rules.")
    print(f"\nReport: {result['report_path']}")


if __name__ == "__main__":
    main()
