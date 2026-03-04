#!/usr/bin/env python3
"""
Ollama gate stress test. Proves gating works via receipts.
Protocol: baseline probe 30s -> stress burst -> after probe 30s -> summary receipt.
Uses gate directly (no real Ollama calls). Stdlib only.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def _run_probe(duration_s: int = 30) -> dict:
    import importlib.util
    spec = importlib.util.spec_from_file_location("ollama_probe", REPO_ROOT / "Scripts" / "ollama_probe.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run_probe(duration_s=duration_s)


def _stress_burst() -> dict:
    """Burst requests through gate. Returns {gate_denies, gate_allows, inflight_peak, cooldown_events}."""
    from calyx.kernel.ollama_gate import check, release, record_failure, record_success

    allows = 0
    denies = 0
    cooldown_events = 0
    inflight_peak = 0

    # Burst from same caller_key (expect rate_limit + inflight_cap)
    caller = "stress_burst_single"
    for i in range(15):
        r = check(caller_key=caller, request_metadata={"burst": i})
        if r.get("allowed"):
            allows += 1
            inflight_peak = max(inflight_peak, 1)
            release(caller)
        else:
            denies += 1
            if r.get("reason") == "cooldown":
                cooldown_events += 1
        time.sleep(0.05)

    # Multiple caller_keys (each gets own slot)
    for k in ["stress_a", "stress_b", "stress_c"]:
        r = check(caller_key=k, request_metadata={"caller": k})
        if r.get("allowed"):
            allows += 1
            release(k)
        else:
            denies += 1
        time.sleep(0.1)

    # Trigger cooldown via failures
    fail_caller = "stress_cooldown"
    for _ in range(5):
        r = check(caller_key=fail_caller, request_metadata={"cooldown_test": 1})
        if r.get("allowed"):
            allows += 1
            release(fail_caller)
            record_failure(fail_caller)
        else:
            denies += 1
            if r.get("reason") == "cooldown":
                cooldown_events += 1
        time.sleep(0.2)

    return {
        "gate_denies": denies,
        "gate_allows": allows,
        "inflight_peak": inflight_peak,
        "cooldown_events": cooldown_events,
    }


def main() -> int:
    perf_dir = REPO_ROOT / "runtime" / "receipts" / "perf"
    perf_dir.mkdir(parents=True, exist_ok=True)

    print("Baseline probe 30s...")
    baseline = _run_probe(30)
    baseline_summary = baseline.get("summary", {})
    print(f"  spike_ticks={baseline_summary.get('spike_ticks', 0)}, top_callers={baseline_summary.get('top_callers', [])}")

    print("Stress burst...")
    during = _stress_burst()
    print(f"  denies={during['gate_denies']}, allows={during['gate_allows']}, cooldown_events={during['cooldown_events']}")

    print("After probe 30s...")
    after = _run_probe(30)
    after_summary = after.get("summary", {})

    verdict = "PASS" if during["gate_denies"] > 0 else "FAIL"
    if during["gate_denies"] == 0:
        verdict = "FAIL"
        next_actions = ["Gate did not deny any requests; check OLLAMA_GATE_ENABLED and config"]
    else:
        next_actions = []

    summary = {
        "baseline": {
            "spike_ticks": baseline_summary.get("spike_ticks", 0),
            "top_callers": baseline_summary.get("top_callers", []),
        },
        "during": {
            "gate_denies": during["gate_denies"],
            "gate_allows": during["gate_allows"],
            "inflight_peak": during["inflight_peak"],
            "cooldown_events": during["cooldown_events"],
        },
        "after": {
            "spike_ticks": after_summary.get("spike_ticks", 0),
            "top_callers": after_summary.get("top_callers", []),
        },
        "verdict": verdict,
        "next_actions": next_actions,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = perf_dir / f"ollama_stress_summary__{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(f"Summary: {path}")
    print(f"Verdict: {verdict}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
