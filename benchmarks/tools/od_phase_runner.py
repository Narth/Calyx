"""
OD Phase Runner: zero-guessing wrapper for prompt execution.

Behavior:
- Emits phase markers (PROMPT_START, PROMPT_END) with run_id/prompt_id.
- Optionally emits RUN_START/RUN_END when --event is provided without a command.
- Executes a command (if provided) between START and END.
- Can inject an MD header with timing info at the top of the output file.
- Logs to logs/system/prompt_phases.jsonl (append-only).

Usage examples:
1) Run a prompt with start/end markers and write header into an MD file:
   python benchmarks/tools/od_phase_runner.py \
     --run-id OD-2025-12-13T06-00-UTC \
     --prompt-id OD-01 \
     --cmd "python generate_prompt.py --id OD-01 --out benchmarks/outcome/OD-01.md" \
     --output-md benchmarks/outcome/OD-01.md

2) Emit a RUN_START marker:
   python benchmarks/tools/od_phase_runner.py --run-id OD-2025-12-13T06-00-UTC --event RUN_START

3) Emit a RUN_END marker:
   python benchmarks/tools/od_phase_runner.py --run-id OD-2025-12-13T06-00-UTC --event RUN_END

Fields written to prompt_phases.jsonl:
- timestamp_utc (ISO8601, ms, Z)
- monotonic_ns
- event (PROMPT_START, PROMPT_END, RUN_START, RUN_END)
- run_id
- prompt_id (if provided)
- pid, host, user
- git_commit (best-effort, else null)
"""

import argparse
import getpass
import json
import socket
import subprocess
import time
import sys
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def monotonic_ns() -> int:
    return time.monotonic_ns()


def git_commit():
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
        return out
    except Exception:
        return None


def append_phase(event: str, run_id: str, prompt_id: str | None, path: Path):
    rec = {
        "timestamp_utc": now_iso(),
        "monotonic_ns": monotonic_ns(),
        "event": event,
        "run_id": run_id,
        "prompt_id": prompt_id,
        "pid": subprocess.os.getpid(),
        "host": socket.gethostname(),
        "user": getpass.getuser(),
        "git_commit": git_commit(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def inject_md_header(output_md: Path, run_id: str, prompt_id: str | None, start_iso: str, end_iso: str):
    if not output_md.exists():
        return
    content = output_md.read_text(encoding="utf-8")
    header = [
        "<!--",
        f"run_id: {run_id}",
        f"prompt_id: {prompt_id}" if prompt_id else "prompt_id: ",
        f"generated_at_start_utc: {start_iso}",
        f"generated_at_end_utc:   {end_iso}",
        "-->",
        "",
    ]
    output_md.write_text("\n".join(header) + content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="OD phase runner with start/end markers and optional command execution.")
    parser.add_argument("--run-id", required=True, help="Shared run identifier, e.g., OD-2025-12-13T06-00-UTC")
    parser.add_argument("--prompt-id", help="Prompt identifier, e.g., OD-01")
    parser.add_argument(
        "--event",
        choices=["RUN_START", "RUN_END"],
        help="Emit a run-level marker without executing a command.",
    )
    parser.add_argument("--cmd", help="Command to execute between PROMPT_START and PROMPT_END.")
    parser.add_argument("--output-md", type=Path, help="If set, injects timing header into this MD file after completion.")
    parser.add_argument(
        "--phase-log",
        type=Path,
        default=Path("logs/system/prompt_phases.jsonl"),
        help="Append-only phase log path (default logs/system/prompt_phases.jsonl)",
    )
    parser.add_argument(
        "--spawn-monitor",
        action="store_true",
        help="Spawn resource_monitor in background (detached). Does NOT emit RUN_START; ensure monitor is running before RUN_START.",
    )
    parser.add_argument(
        "--stop-monitor",
        action="store_true",
        help="Stop background monitor using PID file.",
    )
    parser.add_argument("--monitor-interval", type=float, default=2.0, help="Monitor interval when spawning (seconds).")
    parser.add_argument("--monitor-duration", type=float, default=1800.0, help="Monitor duration when spawning (seconds).")
    parser.add_argument(
        "--monitor-pid-file",
        type=Path,
        default=Path("logs/system/resource_monitor.pid"),
        help="PID file for spawned monitor.",
    )
    parser.add_argument(
        "--monitor-log",
        type=Path,
        default=Path("logs/system/resource_usage.jsonl"),
        help="Monitor output file (for reference).",
    )
    args = parser.parse_args()

    # Monitor control branch
    if args.spawn_monitor or args.stop_monitor:
        if args.spawn_monitor and args.stop_monitor:
            raise SystemExit("Cannot spawn and stop monitor in the same invocation.")
        if args.spawn_monitor:
            args.monitor_pid_file.parent.mkdir(parents=True, exist_ok=True)
            cmd = [
                sys.executable,
                "benchmarks/tools/resource_monitor.py",
                "--interval",
                str(args.monitor_interval),
                "--duration",
                str(args.monitor_duration),
                "--tag",
                args.run_id,
                "--output",
                str(args.monitor_log),
            ]
            creationflags = 0
            if sys.platform.startswith("win"):
                # Hide window and detach
                CREATE_NO_WINDOW = 0x08000000
                creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
            args.monitor_pid_file.write_text(str(proc.pid), encoding="utf-8")
            print(f"Spawned monitor PID {proc.pid} -> {args.monitor_pid_file} (tag={args.run_id})")
            return
        if args.stop_monitor:
            if not args.monitor_pid_file.exists():
                raise SystemExit("Monitor PID file not found.")
            try:
                pid = int(args.monitor_pid_file.read_text().strip())
            except Exception:
                raise SystemExit("Invalid PID file.")
            try:
                if sys.platform.startswith("win"):
                    subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.run(["kill", "-TERM", str(pid)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"Requested monitor stop for PID {pid}")
            except Exception as e:
                print(f"Monitor stop failed: {e}")
            return

    # Run-level marker only
    if args.event:
        append_phase(args.event, args.run_id, args.prompt_id, args.phase_log)
        print(f"Emitted {args.event} for run {args.run_id}")
        return

    if not args.cmd:
        raise SystemExit("Either --event or --cmd must be provided.")

    if not args.prompt_id:
        raise SystemExit("--prompt-id is required when running a command.")

    # Prompt start
    start_rec = append_phase("PROMPT_START", args.run_id, args.prompt_id, args.phase_log)
    start_iso = start_rec["timestamp_utc"]

    # Execute command
    result = subprocess.run(args.cmd, shell=True)
    if result.returncode != 0:
        # Even on failure, emit END with a note in stdout.
        print(f"Command failed with return code {result.returncode}")

    # Prompt end
    end_rec = append_phase("PROMPT_END", args.run_id, args.prompt_id, args.phase_log)
    end_iso = end_rec["timestamp_utc"]

    # Inject header if requested
    if args.output_md:
        inject_md_header(args.output_md, args.run_id, args.prompt_id, start_iso, end_iso)

    print(f"Completed prompt {args.prompt_id} run {args.run_id} | start {start_iso} end {end_iso}")


if __name__ == "__main__":
    main()
