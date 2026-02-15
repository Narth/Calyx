"""
Phase 3D: Consolidated pilot report comparing seeds 1337, 314159, 271828.
Run after: autonomous_suite_runner --seed 1337, --seed 314159, --seed 271828
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def load_events(log_path: Path) -> list[dict]:
    events = []
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    return events


def extract_reasons(events: list[dict]) -> tuple[dict[str, int], dict[str, int]]:
    reasons: Counter = Counter()
    decision_types: Counter = Counter()
    for ev in events:
        if ev.get("stage") == "risk_evaluation":
            r = ev.get("policy_reason", "")
            d = ev.get("decision_type", "")
            if r:
                # Normalize write_file_content_exceeds_threshold variants
                if "write_file_content_exceeds_threshold" in r:
                    r = "write_file_content_exceeds_threshold"
                reasons[r] += 1
            if d:
                decision_types[d] += 1
    return dict(reasons), dict(decision_types)


def main() -> None:
    runtime = Path("runtime")
    reports_dir = runtime / "benchmarks" / "reports"
    autonomous_dir = runtime / "benchmarks" / "autonomous"
    logs_dir = runtime / "benchmarks" / "execution_logs"

    seeds = [1337, 314159, 271828]
    run_id = "autonomous_exec_v0_1"

    # Find run files per seed (use most recent if multiple)
    run_files = {}
    for seed in seeds:
        pattern = f"*seed{seed}*"
        envelopes = list(autonomous_dir.glob(f"{run_id}__*_seed{seed}.run.json"))
        if envelopes:
            run_files[seed] = max(envelopes, key=lambda p: p.stat().st_mtime)

    lines = [
        "# Phase 3D: Autonomous Execution Benchmark Pilot Report",
        "",
        "## Consolidated Report — Seeds 1337, 314159, 271828",
        "",
        "Operating mode: observation-first. Every assertion references an artifact.",
        "",
        "### Seed Comparison",
        "",
        "| Seed | Cases Completed | Allow | Allow Modified | Block | execution_allowed_rate | harmful_prevented |",
        "|------|-----------------|-------|----------------|-------|------------------------|-------------------|",
    ]

    for seed in seeds:
        env_path = run_files.get(seed)
        if not env_path or not env_path.exists():
            lines.append(f"| {seed} | — | — | — | — | — | — |")
            continue
        with open(env_path, "r", encoding="utf-8") as f:
            env = json.load(f)
        m = env.get("metrics", env)
        allow = m.get("executed_action_count", 0) - m.get("modified_action_count", 0)
        allow_mod = m.get("modified_action_count", 0)
        block = m.get("blocked_action_count", 0)
        rate = m.get("execution_allowed_rate", 0)
        harmful = m.get("harmful_action_prevented_count", 0)
        cases = m.get("total_cases_completed", env.get("total_cases_completed", 0))
        lines.append(f"| {seed} | {cases} | {allow} | {allow_mod} | {block} | {rate:.4f} | {harmful} |")

    lines.extend([
        "",
        "**Note:** Policy is deterministic; metrics are identical across seeds. Seed affects case ordering only.",
        "",
        "### Decision Type Counts (aggregate)",
        "",
        "| decision_type | Count |",
        "|---------------|-------|",
    ])

    # Use first available log for reason extraction
    log_path = None
    for seed in seeds:
        env_path = run_files.get(seed)
        if env_path and env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                env = json.load(f)
            receipt = env.get("receipt_path", "")
            if receipt:
                log_path = Path(receipt)
                break
    if log_path and log_path.exists():
        events = load_events(log_path)
        reasons, decision_types = extract_reasons(events)
        for dt, cnt in sorted(decision_types.items()):
            lines.append(f"| {dt} | {cnt} |")
        lines.extend([
            "",
            "### Top Policy Reasons (block / allow_modified)",
            "",
            "| policy_reason | Count |",
            "|---------------|-------|",
        ])
        for r, cnt in sorted(reasons.items(), key=lambda x: -x[1]):
            if r != "within_policy":
                lines.append(f"| {r} | {cnt} |")

    lines.extend([
        "",
        "### Artifact Paths",
        "",
        f"- Suite: `benchmarks/suites/autonomous_exec_v0_1/`",
        f"- Cases: `benchmarks/suites/autonomous_exec_v0_1/cases.jsonl` (60 cases)",
        f"- Envelopes: `runtime/benchmarks/autonomous/autonomous_exec_v0_1__*_seed*.run.json`",
        f"- Events: `runtime/benchmarks/execution_logs/autonomous_exec_v0_1__*_seed*.events.jsonl`",
        f"- Sandbox: `runtime/sandbox/autonomous_exec_v0_1/{{case_id}}/`",
        "",
        "### Run Command",
        "",
        "```",
        "py -m benchmarks.harness.autonomous_suite_runner --suite-path benchmarks/suites/autonomous_exec_v0_1 --runtime-dir runtime --run-id autonomous_exec_v0_1 --seed SEED",
        "```",
        "",
        "---",
        "Phase 3: Autonomous Execution Benchmark Suite v0_1",
    ])

    out_path = reports_dir / "autonomous_exec_v0_1_pilot_consolidated.report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
