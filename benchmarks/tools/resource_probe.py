"""
Resource probe for Outcome Density runs (manual, no schedulers).

Captures best-effort snapshots of GPU and system usage and appends to
logs/system/resource_usage.jsonl. Prints each sample to stdout as a "check-in."

Usage examples:
  python -m benchmarks.tools.resource_probe --count 1
  python -m benchmarks.tools.resource_probe --count 5 --interval 5 --note "OD run check-in"

Notes:
- Uses nvidia-smi if available for GPU power/memory.
- Uses psutil if available for CPU/RAM; otherwise leaves those fields null.
- Append-only; no daemons or schedulers are introduced.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

LOG_PATH = Path("logs") / "system" / "resource_usage.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def try_psutil() -> Optional[Any]:
    try:
        import psutil  # type: ignore
        return psutil
    except Exception:
        return None


def get_gpu_stats() -> Dict[str, Optional[float]]:
    if not shutil.which("nvidia-smi"):
        return {"gpu_power_w": None, "gpu_mem_mb": None, "gpu_mem_total_mb": None}
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=power.draw,memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ]
        out = subprocess.check_output(cmd, encoding="utf-8").strip().splitlines()
        if not out:
            return {"gpu_power_w": None, "gpu_mem_mb": None, "gpu_mem_total_mb": None}
        parts = [p.strip() for p in out[0].split(",")]
        power = float(parts[0]) if len(parts) > 0 else None
        mem_used = float(parts[1]) if len(parts) > 1 else None
        mem_total = float(parts[2]) if len(parts) > 2 else None
        return {"gpu_power_w": power, "gpu_mem_mb": mem_used, "gpu_mem_total_mb": mem_total}
    except Exception:
        return {"gpu_power_w": None, "gpu_mem_mb": None, "gpu_mem_total_mb": None}


def get_system_stats(psutil_mod: Optional[Any]) -> Dict[str, Optional[float]]:
    if psutil_mod is None:
        return {
            "cpu_percent": None,
            "ram_gb_used": None,
            "ram_percent": None,
        }
    try:
        cpu_percent = psutil_mod.cpu_percent(interval=None)
        mem = psutil_mod.virtual_memory()
        ram_gb_used = mem.used / (1024 ** 3)
        ram_percent = mem.percent
        return {
            "cpu_percent": float(cpu_percent),
            "ram_gb_used": float(ram_gb_used),
            "ram_percent": float(ram_percent),
        }
    except Exception:
        return {
            "cpu_percent": None,
            "ram_gb_used": None,
            "ram_percent": None,
        }


def append_record(obj: Dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.write("\n")


def sample(note: Optional[str]) -> Dict[str, Any]:
    psutil_mod = try_psutil()
    gpu_stats = get_gpu_stats()
    sys_stats = get_system_stats(psutil_mod)
    record: Dict[str, Any] = {
        "timestamp": now_iso(),
        "entry_type": "resource_probe",
        "note": note,
    }
    record.update(gpu_stats)
    record.update(sys_stats)
    append_record(record)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Resource probe check-in for OD runs (manual, append-only).")
    parser.add_argument("--count", type=int, default=1, help="Number of samples (default: 1)")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between samples (default: 5)")
    parser.add_argument("--note", type=str, default=None, help="Optional note to include in the log")
    args = parser.parse_args()

    count = max(1, args.count)
    interval = max(0.1, args.interval)
    for i in range(count):
        rec = sample(args.note)
        print(f"[{rec['timestamp']}] gpu_power_w={rec['gpu_power_w']} gpu_mem_mb={rec['gpu_mem_mb']} ram_gb_used={rec['ram_gb_used']} ram_percent={rec['ram_percent']} cpu_percent={rec['cpu_percent']} note={rec.get('note')}")
        if i + 1 < count:
            time.sleep(interval)


if __name__ == "__main__":
    main()
