"""
Local LLM runner wrapper (Safe Mode, append-only).

Invokes an external llama.cpp-style binary with a GGUF model.
Reads prompt from --prompt-file (required).
Writes a single JSON record to --out-json with timing and stdout/stderr.

Usage:
  python benchmarks/tools/local_llm_runner.py \
    --runner tools/bin/llama.cpp/llama.exe \
    --model-path tools/models/Qwen2.5-Omni-7B-Q4_K_M.gguf \
    --model-id Qwen2.5-Omni-7B-Q4_K_M \
    --prompt-file /path/to/prompt.txt \
    --n-predict 512 --temperature 0.7 --top-p 0.9 --seed 42 \
    --timeout-sec 60 \
    --out-json /tmp/llm_out.json

If the runner path is missing, exits nonzero with reason "MISSING_RUNNER".
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def run(args):
    runner = Path(args.runner)
    if not runner.exists():
        return {
            "status": "MISSING_RUNNER",
            "reason": f"Runner not found: {runner}",
            "started_at_utc": now_iso(),
            "ended_at_utc": now_iso(),
            "duration_ms": 0,
            "stdout": "",
            "stderr": "",
            "return_code": None,
        }

    with open(args.prompt_file, "r", encoding="utf-8") as f:
        prompt = f.read()

    # llama-cli: -m model -f prompt_file -n N --temp T --top-p P --seed S
    cmd = [
        str(runner),
        "-m",
        str(args.model_path),
        "-f",
        str(args.prompt_file),
        "-n",
        str(args.n_predict),
        "--temp",
        str(args.temperature),
        "--top-p",
        str(args.top_p),
        "--seed",
        str(args.seed),
    ]

    started = time.time()
    started_iso = now_iso()
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=args.timeout_sec,
        )
        ended_iso = now_iso()
        duration_ms = int((time.time() - started) * 1000)
        out = proc.stdout or ""
        err = proc.stderr or ""
        # truncate to keep JSON small
        def truncate(s, limit=8000):
            return s if len(s) <= limit else s[:limit] + "\n...[truncated]..."

        return {
            "status": "OK",
            "started_at_utc": started_iso,
            "ended_at_utc": ended_iso,
            "duration_ms": duration_ms,
            "return_code": proc.returncode,
            "stdout": truncate(out),
            "stderr": truncate(err),
            "model_id": args.model_id,
            "runner": str(runner),
        }
    except subprocess.TimeoutExpired as e:
        ended_iso = now_iso()
        duration_ms = int((time.time() - started) * 1000)
        return {
            "status": "TIMEOUT",
            "started_at_utc": started_iso,
            "ended_at_utc": ended_iso,
            "duration_ms": duration_ms,
            "return_code": None,
            "stdout": "",
            "stderr": f"timeout after {args.timeout_sec}s",
            "model_id": args.model_id,
            "runner": str(runner),
        }
    except Exception as e:
        ended_iso = now_iso()
        duration_ms = int((time.time() - started) * 1000)
        return {
            "status": "ERROR",
            "started_at_utc": started_iso,
            "ended_at_utc": ended_iso,
            "duration_ms": duration_ms,
            "return_code": None,
            "stdout": "",
            "stderr": f"{type(e).__name__}: {e}",
            "model_id": args.model_id,
            "runner": str(runner),
        }


def main():
    p = argparse.ArgumentParser(description="Local LLM runner (llama.cpp wrapper).")
    p.add_argument("--runner", required=True, help="Path to llama executable")
    p.add_argument("--model-path", required=True, help="Path to GGUF model")
    p.add_argument("--model-id", required=True, help="Model identifier string")
    p.add_argument("--prompt-file", required=True, help="File containing prompt text")
    p.add_argument("--n-predict", type=int, default=512)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--top-p", type=float, default=0.9)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--timeout-sec", type=int, default=120)
    p.add_argument("--out-json", required=True, help="Where to write JSON output")
    args = p.parse_args()

    result = run(args)
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if result.get("status") != "OK":
        sys.exit(1)


if __name__ == "__main__":
    main()
