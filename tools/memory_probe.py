"""Memory probe for Station Calyx

Collects a system-wide memory snapshot and top processes by RSS.
Writes a JSON report to outgoing/memory_snapshot_<iso>.json and prints a short summary.

Usage:
  python -u tools/memory_probe.py

This is read-only and safe to run at any time.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

OUT = Path(__file__).resolve().parents[1] / "outgoing"
OUT.mkdir(parents=True, exist_ok=True)


def probe_with_psutil(limit: int = 20):
    import psutil

    vm = psutil.virtual_memory()
    procs = []
    for p in psutil.process_iter(attrs=["pid", "name", "username", "create_time", "cmdline"]):
        try:
            with p.oneshot():
                info = p.info
                mem = p.memory_info()
                procs.append({
                    "pid": info.get("pid"),
                    "name": info.get("name"),
                    "username": info.get("username"),
                    "create_time": info.get("create_time"),
                    "cmdline": info.get("cmdline"),
                    "rss": getattr(mem, "rss", None),
                    "vms": getattr(mem, "vms", None),
                })
        except Exception:
            continue
    procs = sorted(procs, key=lambda x: x.get("rss") or 0, reverse=True)[:limit]
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "virtual_memory": {
            "total": vm.total,
            "available": vm.available,
            "percent": vm.percent,
            "used": vm.used,
            "free": vm.free,
        },
        "top_processes": procs,
    }


def probe_with_tasklist(limit: int = 20):
    # Fallback for systems without psutil: use tasklist and parse output
    import subprocess

    proc = subprocess.run(["tasklist", "/FO", "CSV", "/V"], capture_output=True, text=True)
    lines = proc.stdout.splitlines()
    # CSV header; Windows tasklist CSV format is: "Image Name","PID","Session Name","Session#","Mem Usage","Status","User Name","CPU Time","Window Title"
    import csv
    reader = csv.DictReader(lines)
    procs = []
    for r in reader:
        mem = r.get("Mem Usage", "0").replace(",", "").replace(" K", "000").strip()
        try:
            rss = int(mem)
        except Exception:
            rss = None
        procs.append({
            "pid": int(r.get("PID")) if r.get("PID") else None,
            "name": r.get("Image Name"),
            "username": r.get("User Name"),
            "cmdline": None,
            "rss": rss,
            "vms": None,
        })
    procs = sorted(procs, key=lambda x: x.get("rss") or 0, reverse=True)[:limit]
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "note": "tasklist fallback",
        "top_processes": procs,
    }


def main():
    try:
        data = probe_with_psutil(limit=30)
    except Exception:
        data = probe_with_tasklist(limit=30)

    iso = data.get("ts", datetime.now(timezone.utc).isoformat()).replace(":", "-")
    out_path = OUT / f"memory_snapshot_{iso}.json"
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)

    # Print a short human summary (top 10)
    print("Memory snapshot written to:", out_path)
    vm = data.get("virtual_memory")
    if vm:
        print(f"System memory: percent={vm.get('percent')} used={vm.get('used')} free={vm.get('free')}")

    print("Top processes by RSS:")
    for p in data.get("top_processes", [])[:10]:
        rss = p.get("rss") or 0
        print(f" - pid={p.get('pid')} name={p.get('name')} rss={rss} cmd={' '.join(p.get('cmdline') or [])}")


if __name__ == "__main__":
    main()
