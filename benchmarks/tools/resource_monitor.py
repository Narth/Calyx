"""
Resource monitor for Station Calyx (manual, Safe Mode, append-only).

Usage (example):
  python benchmarks/tools/resource_monitor.py --interval 2 --duration 120 --tag "OD-run-1"

Behavior:
  - Samples CPU and RAM usage using psutil.
  - Optionally attempts to capture GPU memory if NVML is available (best-effort).
  - Appends one JSON object per sample to logs/system/resource_usage.jsonl.
  - Prints a concise line per sample to stdout for at-a-glance monitoring.
Constraints:
  - No schedulers or background daemons; runs only while invoked.
  - Append-only logging; creates logs/system/ if needed.
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil
import subprocess
import re


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def maybe_gpu():
    """Attempt GPU metrics via NVML; if unavailable, fall back to parsing nvidia-smi."""
    # First, try NVML if present.
    try:
        import pynvml  # type: ignore

        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        gpus = []
        for i in range(count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            try:
                power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
            except Exception:
                power = None
            gpus.append(
                {
                    "index": i,
                    "name": pynvml.nvmlDeviceGetName(handle).decode("utf-8", errors="ignore"),
                    "mem_used_mb": round(mem.used / (1024 * 1024), 2),
                    "mem_total_mb": round(mem.total / (1024 * 1024), 2),
                    "util_percent": util.gpu,
                    "power_w": power,
                }
            )
        pynvml.nvmlShutdown()
        return gpus
    except Exception:
        pass

    # Fallback: parse nvidia-smi if available.
    try:
        smi = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,power.draw",
                "--format=csv,noheader,nounits",
            ],
            text=True,
        )
        gpus = []
        for line in smi.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 4:
                continue
            name, util, mem_used, mem_total, *rest = parts
            power = float(rest[0]) if rest else None
            gpus.append(
                {
                    "name": name,
                    "util_percent": float(util),
                    "mem_used_mb": float(mem_used),
                    "mem_total_mb": float(mem_total),
                    "power_w": power,
                }
            )
        return gpus if gpus else None
    except Exception:
        return None


def sample(tag: str | None):
    vm = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=None)
    data = {
        "timestamp": now_iso(),
        "tag": tag,
        "cpu_percent": cpu,
        "ram_used_gb": round(vm.used / (1024 ** 3), 3),
        "ram_total_gb": round(vm.total / (1024 ** 3), 3),
        "ram_percent": vm.percent,
        # Placeholder for CPU package power (not available cross-platform without extra drivers).
        "cpu_power_w": None,
    }
    gpu = maybe_gpu()
    if gpu is not None:
        data["gpu"] = gpu
    return data


def append_log(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Manual resource monitor (Safe Mode, append-only).")
    parser.add_argument("--interval", type=float, default=2.0, help="Sampling interval in seconds (default 2).")
    parser.add_argument("--duration", type=float, default=60.0, help="Total duration in seconds (default 60).")
    parser.add_argument("--tag", type=str, default=None, help="Optional tag to annotate samples (e.g., OD-run-1).")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("logs/system/resource_usage.jsonl"),
        help="Append-only output file (default logs/system/resource_usage.jsonl).",
    )
    args = parser.parse_args()

    end_time = time.time() + args.duration
    count = 0
    while time.time() <= end_time:
        obj = sample(args.tag)
        append_log(args.output, obj)
        count += 1
        summary = f"{obj['timestamp']} | CPU {obj['cpu_percent']:.1f}% | RAM {obj['ram_used_gb']}/{obj['ram_total_gb']} GB ({obj['ram_percent']:.1f}%)"
        if obj.get("cpu_power_w") is not None:
            summary += f" | CPU_PWR {obj['cpu_power_w']:.1f}W"
        if "gpu" in obj and obj["gpu"]:
            gpu_summaries = []
            for g in obj["gpu"]:
                idx = g.get("index", "?")
                gpu_str = f"GPU{idx} {g['util_percent']}% {g['mem_used_mb']}/{g['mem_total_mb']} MB"
                if g.get("power_w") is not None:
                    gpu_str += f" {g['power_w']:.1f}W"
                gpu_summaries.append(gpu_str)
            summary += " | " + "; ".join(gpu_summaries)
        if args.tag:
            summary += f" | tag={args.tag}"
        print(summary, flush=True)
        time.sleep(args.interval)

    print(f"Completed {count} samples -> {args.output}", flush=True)


if __name__ == "__main__":
    main()
