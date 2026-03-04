"""
Phase 4B minimal report — backward-compatible wrapper over compaction_signal_report.
Use compaction_signal_report for capability-based naming.
"""
from __future__ import annotations

from pathlib import Path

from .compaction_signal_report import write_compaction_signal_report


def write_phase4b_minimal_report(
    runtime_root: Path,
    run_id: str = "autonomous_exec_v0_1_llm_phase4b",
    *,
    valid_runs: list[dict] | None = None,
) -> Path:
    """
    Backward-compatible wrapper. Produces phase4b_minimal_compaction_signal.report.md.
    Delegates to write_compaction_signal_report with Phase 4B defaults.
    """
    return write_compaction_signal_report(
        runtime_root,
        run_id,
        valid_runs=valid_runs,
        report_filename="phase4b_minimal_compaction_signal.report.md",
        title="Phase 4B Minimal Compaction Signal Report",
        subtitle="Absolute metrics from minimal live confirmation runs (2 models, seed 1337).",
    )


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Phase 4B minimal compaction signal report (wrapper)")
    parser.add_argument("--runtime-dir", type=Path, default=Path("runtime"))
    parser.add_argument("--run-id", type=str, default="autonomous_exec_v0_1_llm_phase4b")
    args = parser.parse_args()
    path = write_phase4b_minimal_report(args.runtime_dir, args.run_id)
    print(f"Report: {path}")


if __name__ == "__main__":
    main()
