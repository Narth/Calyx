"""
Run the full OD peer suite with markers and MD outputs.
Assumes resource monitor is already running (spawned separately).

This script will:
- Emit RUN_START
- Iterate prompts in suite, calling od_phase_runner with od_prompt_cmd
- Emit RUN_END

Usage:
  python benchmarks/tools/run_od_peer_batch.py \
    --run-id OD-PEER-2025-12-13-A \
    --suite benchmarks/outcome/suites/od_v2_peer_suite_v1.json \
    --out-dir benchmarks/outcome/OD-PEER-2025-12-13-A \
    --source-dir "benchmarks/outcome/Test 1"
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Batch runner for OD peer suite.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, help="Optional directory containing prior responses (OD-XX.md).")
    parser.add_argument("--mode", choices=["stub", "generate", "station_ingest"], default="station_ingest", help="Generation mode for od_prompt_cmd.")
    parser.add_argument("--min-duration", type=float, default=None, help="Override min duration (seconds).")
    args = parser.parse_args()

    suite_data = json.loads(args.suite.read_text(encoding="utf-8"))
    prompts = [p["prompt_id"] for p in suite_data.get("prompts", [])]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    phase_runner = [sys.executable, "benchmarks/tools/od_phase_runner.py"]
    prompt_cmd = [sys.executable, "benchmarks/tools/od_prompt_cmd.py"]

    # RUN_START
    res = subprocess.run(phase_runner + ["--run-id", args.run_id, "--event", "RUN_START"])
    if res.returncode != 0:
        raise SystemExit("RUN_START failed")

    failures = []
    metas_for_index = []
    for pid in prompts:
        out_md = args.out_dir / f"{pid}.md"
        source_path = args.source_dir / f"{pid}.md" if args.source_dir else None
        cmd_parts = [
            f"\"{sys.executable}\"",
            "benchmarks/tools/od_prompt_cmd.py",
            f"--run-id {args.run_id}",
            f"--prompt-id {pid}",
            f"--suite \"{args.suite}\"",
            f"--out \"{out_md}\"",
            f"--mode {args.mode}",
        ]
        if args.min_duration is not None:
            cmd_parts.append(f"--min-duration {args.min_duration}")
        if source_path and source_path.exists():
            cmd_parts.append(f"--source \"{source_path}\"")
        cmd_str = " ".join(cmd_parts)
        res = subprocess.run(
            phase_runner
            + [
                "--run-id",
                args.run_id,
                "--prompt-id",
                pid,
                "--cmd",
                cmd_str,
                "--output-md",
                out_md,
            ]
        )
        if res.returncode != 0:
            failures.append(pid)
        meta_path = Path(str(out_md) + ".meta.json")
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        metas_for_index.append((pid, out_md, meta))

    # RUN_END
    res = subprocess.run(phase_runner + ["--run-id", args.run_id, "--event", "RUN_END"])
    if res.returncode != 0:
        raise SystemExit("RUN_END failed")

    if failures:
        print("Failures:", failures)
        raise SystemExit("Some prompts failed")

    # Write prompt_index.jsonl with envelope/reflection ids if available
    idx_path = args.out_dir / "prompt_index.jsonl"
    with idx_path.open("w", encoding="utf-8") as f:
        for pid, out_md, meta in metas_for_index:
            f.write(
                json.dumps(
                    {
                        "run_id": args.run_id,
                        "prompt_id": pid,
                        "md_path": str(out_md),
                        "envelope_id": meta.get("envelope_id"),
                        "reflection_id": meta.get("reflection_id"),
                        "reflection_source": meta.get("reflection_source"),
                        "ingested_at_utc": meta.get("ingested_at_utc"),
                        "reflection_timestamp_utc": meta.get("reflection_timestamp_utc"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    print("Batch complete.")


if __name__ == "__main__":
    main()
