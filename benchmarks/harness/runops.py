"""
RunOps — General orchestrator for benchmark run lifecycle.
Supports: scan → monitor → verify → report for arbitrary run types via CLI args or presets.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

POLL_INTERVAL_SEC = 15
MONITOR_TIMEOUT_SEC = 600


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_seed(instance_id: str) -> int | None:
    if "_seed" in instance_id:
        try:
            return int(instance_id.split("_seed")[-1])
        except ValueError:
            pass
    return None


def scan(
    runtime_root: Path,
    run_id: str,
    *,
    seed_filter: int | None = None,
    models_filter: frozenset[str] | None = None,
) -> list[dict]:
    """
    Scan runtime/benchmarks/autonomous for runs matching run_id, optional seed and model filters.
    Returns list of {run_path, metrics_path, events_path, instance_id, envelope_data, model_id, seed, status}.
    status: "complete" | "incomplete" | "active"
    """
    runtime_root = Path(runtime_root)
    autonomous_dir = runtime_root / "benchmarks" / "autonomous"
    logs_dir = runtime_root / "benchmarks" / "execution_logs"
    candidates = []

    if not autonomous_dir.exists():
        return candidates

    for run_path in autonomous_dir.glob(f"{run_id}__*.run.json"):
        tmp_path = run_path.with_suffix(".run.json.tmp")
        instance_id = run_path.name.replace(f"{run_id}__", "").replace(".run.json", "")
        seed = _parse_seed(instance_id)
        if seed_filter is not None and seed != seed_filter:
            continue

        envelope_data = _load_json(run_path)
        model_id = envelope_data.get("model_id", "")
        if models_filter is not None and model_id not in models_filter:
            continue

        metrics_path = autonomous_dir / f"{run_id}__{instance_id}.metrics.json"
        events_path = logs_dir / f"{run_id}__{instance_id}.events.jsonl"

        if tmp_path.exists():
            status = "active"
        elif envelope_data.get("exit_status") != "normal":
            status = "incomplete"
        elif envelope_data.get("total_cases_completed") != envelope_data.get("total_cases_expected"):
            status = "incomplete"
        else:
            status = "complete"

        candidates.append({
            "run_path": run_path,
            "envelope_path": run_path,
            "metrics_path": metrics_path,
            "events_path": events_path,
            "instance_id": instance_id,
            "envelope_data": envelope_data,
            "model_id": model_id,
            "seed": seed,
            "status": status,
        })
    return sorted(candidates, key=lambda x: (x["model_id"], x["instance_id"]))


def monitor(
    runtime_root: Path,
    candidate: dict,
    *,
    poll_interval: int = POLL_INTERVAL_SEC,
    timeout: int = MONITOR_TIMEOUT_SEC,
) -> dict:
    """Poll until run completes or timeout. Returns updated candidate."""
    run_path = candidate["run_path"]
    tmp_path = run_path.with_suffix(".run.json.tmp")
    expected = candidate["envelope_data"].get("total_cases_expected", 60)
    start = time.monotonic()

    while time.monotonic() - start < timeout:
        if tmp_path.exists():
            time.sleep(poll_interval)
            continue
        envelope_data = _load_json(run_path)
        if not envelope_data:
            time.sleep(poll_interval)
            continue
        if envelope_data.get("exit_status") == "normal" and envelope_data.get("total_cases_completed") == expected:
            candidate["envelope_data"] = envelope_data
            candidate["status"] = "complete"
            return candidate
        time.sleep(poll_interval)

    candidate["status"] = "incomplete"
    candidate["monitor_timeout"] = True
    return candidate


def verify(
    candidate: dict,
    runtime_root: Path,
    run_id: str,
) -> tuple[bool, dict]:
    """Invoke autonomous_verifier on candidate. Returns (pass, results)."""
    from .autonomous_verifier import verify_run

    envelope = candidate["envelope_data"]
    log_path = Path(candidate["events_path"])
    sandbox_root = runtime_root / "sandbox" / run_id
    expected = envelope.get("total_cases_expected", 60)

    results = verify_run(
        envelope_data=envelope,
        log_path=log_path,
        sandbox_root=sandbox_root,
        expected_cases=expected,
        runtime_root=runtime_root,
    )
    return bool(results.get("overall", {}).get("pass")), results


def run_lifecycle(
    runtime_root: Path,
    *,
    run_id: str,
    seed_filter: int | None = None,
    models_filter: frozenset[str] | None = None,
    min_valid_runs: int = 1,
    report_fn: Callable[..., Path] | None = None,
    report_title: str = "Run Report",
    report_filename: str = "runops.report.md",
    poll_interval: int = POLL_INTERVAL_SEC,
    monitor_timeout: int = MONITOR_TIMEOUT_SEC,
) -> dict:
    """
    Full lifecycle: scan → monitor incomplete/active → verify → report.
    report_fn(runtime_root, run_id, valid_runs=valid_runs) -> Path.
    Returns {valid_runs, invalid_runs, verification_failures, report_path, report_generated}.
    """
    runtime_root = Path(runtime_root)
    valid_runs: list[dict] = []
    invalid_runs: list[dict] = []
    verification_failures: list[dict] = []

    candidates = scan(runtime_root, run_id, seed_filter=seed_filter, models_filter=models_filter)

    for c in candidates:
        if c["status"] in ("incomplete", "active"):
            c = monitor(runtime_root, c, poll_interval=poll_interval, timeout=monitor_timeout)
            if c["status"] != "complete":
                invalid_runs.append(c)
                continue
        if c["status"] == "complete":
            passed, verif = verify(c, runtime_root, run_id)
            c["verification"] = verif
            c["verifier_pass"] = passed

            if not passed:
                verification_failures.append({
                    "instance_id": c["instance_id"],
                    "model_id": c["model_id"],
                    "verification": verif,
                })
                invalid_runs.append(c)
            else:
                valid_runs.append(c)

    report_path = runtime_root / "benchmarks" / "reports" / report_filename
    report_path.parent.mkdir(parents=True, exist_ok=True)

    if verification_failures:
        lines = [f"# {report_title}", "", "## VERIFICATION FAILURE — Report Aborted", ""]
        for vf in verification_failures:
            lines.append(f"- **{vf['model_id']}** ({vf['instance_id']}):")
            for k, v in (vf.get("verification") or {}).items():
                if isinstance(v, dict) and "pass" in v and not v.get("pass"):
                    lines.append(f"  - {k}: FAIL")
            lines.append("")
        report_path.write_text("\n".join(lines), encoding="utf-8")
        return {
            "valid_runs": [],
            "invalid_runs": invalid_runs,
            "verification_failures": verification_failures,
            "report_path": report_path,
            "report_generated": False,
        }

    if len(valid_runs) < min_valid_runs and report_fn:
        report_path.write_text(
            f"# {report_title}\n\n"
            f"**Awaiting valid artifacts.** Valid runs: {len(valid_runs)}/{min_valid_runs} required.\n",
            encoding="utf-8",
        )
        return {
            "valid_runs": valid_runs,
            "invalid_runs": invalid_runs,
            "verification_failures": [],
            "report_path": report_path,
            "report_generated": False,
        }

    if report_fn and len(valid_runs) >= min_valid_runs:
        vr_artifacts = [
            {
                "run_path": r["run_path"],
                "envelope_path": r["run_path"],
                "metrics_path": r["metrics_path"],
                "events_path": r["events_path"],
                "instance_id": r["instance_id"],
                "envelope_data": r["envelope_data"],
                "model_id": r["model_id"],
            }
            for r in valid_runs
        ]
        report_path = report_fn(runtime_root, run_id, valid_runs=vr_artifacts, report_filename=report_filename)

    return {
        "valid_runs": valid_runs,
        "invalid_runs": invalid_runs,
        "verification_failures": [],
        "report_path": report_path,
        "report_generated": bool(report_fn and len(valid_runs) >= min_valid_runs),
    }


def _default_verifier(candidate: dict, runtime_root: Path, run_id: str) -> tuple[bool, dict]:
    return verify(candidate, runtime_root, run_id)


PRESETS: dict[str, dict] = {
    "phase4b": {
        "run_id": "autonomous_exec_v0_1_llm_phase4b",
        "seed_filter": 1337,
        "models_filter": frozenset({"tinyllama:latest", "qwen2.5-coder:7b"}),
        "min_valid_runs": 2,
        "report_title": "Phase 4B Minimal Compaction Signal Report",
        "report_subtitle": "Absolute metrics from minimal live confirmation runs (2 models, seed 1337).",
        "report_filename": "phase4b_minimal_compaction_signal.report.md",
    },
}


def run_with_preset(runtime_root: Path, preset_name: str) -> dict:
    """Run lifecycle using a named preset."""
    p = PRESETS.get(preset_name)
    if not p:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PRESETS)}")

    from .compaction_signal_report import write_compaction_signal_report

    rep_filename = p.get("report_filename", f"{preset_name}.report.md")
    rep_title = p.get("report_title", preset_name)
    rep_subtitle = p.get("report_subtitle")

    def report_fn(rt: Path, rid: str, *, valid_runs: list[dict], report_filename: str = "") -> Path:
        return write_compaction_signal_report(
            rt, rid,
            valid_runs=valid_runs,
            report_filename=report_filename or rep_filename,
            title=rep_title,
            subtitle=rep_subtitle,
        )

    return run_lifecycle(
        runtime_root,
        run_id=p["run_id"],
        seed_filter=p.get("seed_filter"),
        models_filter=p.get("models_filter"),
        min_valid_runs=p.get("min_valid_runs", 1),
        report_fn=report_fn,
        report_title=p.get("report_title", preset_name),
        report_filename=rep_filename,
    )


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="RunOps: scan → monitor → verify → report")
    parser.add_argument("--runtime-dir", type=Path, default=Path("runtime"))
    parser.add_argument("--preset", type=str, default=None, help=f"Preset: {', '.join(PRESETS)}")
    parser.add_argument("--run-id", type=str, default=None, help="Override run_id (with --preset or standalone)")
    parser.add_argument("--seed", type=int, default=None, help="Filter by seed (e.g. 1337)")
    parser.add_argument("--models", type=str, default=None, help="Comma-separated model_ids to filter")
    parser.add_argument("--min-valid", type=int, default=1, help="Minimum valid runs to generate report")
    args = parser.parse_args()

    runtime_root = Path(args.runtime_dir)

    if args.preset:
        result = run_with_preset(runtime_root, args.preset)
    else:
        run_id = args.run_id or "autonomous_exec_v0_1_llm"
        models_filter = frozenset(m.strip() for m in args.models.split(",")) if args.models else None
        result = run_lifecycle(
            runtime_root,
            run_id=run_id,
            seed_filter=args.seed,
            models_filter=models_filter,
            min_valid_runs=args.min_valid,
            report_fn=None,
            report_title="Run Report",
            report_filename=f"{run_id}.report.md",
        )

    valid = result["valid_runs"]
    invalid = result["invalid_runs"]
    vf = result["verification_failures"]

    print("\n=== RunOps Lifecycle Output ===\n")
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

    print(f"\nReport: {result['report_path']}")


if __name__ == "__main__":
    main()
