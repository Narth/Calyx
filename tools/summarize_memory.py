"""Summarize memory_samples.jsonl and watcher snapshots into a CSV for analysis.

Usage:
    python tools/summarize_memory.py --out outgoing/memory_summary.csv

Produces a CSV with columns:
  ts,source,run_dir,pid,rss,vms,system_mem_percent,extra_json
Also writes a per-run max-rss report to outgoing/memory_summary_runs.csv
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"


def iter_agent_samples():
    for p in OUT.glob("agent_run_*/memory_samples.jsonl"):
        run_dir = p.parent.name
        try:
            with p.open("r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        obj = json.loads(line)
                        obj["_run_dir"] = run_dir
                        yield obj
                    except Exception:
                        continue
        except Exception:
            continue


def iter_watcher_snapshots():
    for p in OUT.glob("memory_watch_snapshots/*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            # memory_probe outputs a dict with 'system' and 'processes'
            ts = data.get("ts") or data.get("timestamp") or None
            yield {"ts": ts or data.get("system", {}).get("ts"), "_watch_file": p.name, **data}
        except Exception:
            continue


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(OUT / "memory_summary.csv"))
    parser.add_argument("--runs-out", default=str(OUT / "memory_summary_runs.csv"))
    args = parser.parse_args(argv)
    out_path = Path(args.out)
    runs_path = Path(args.runs_out)

    rows = []
    max_by_run = {}

    for s in iter_agent_samples():
        ts = s.get("ts")
        pid = s.get("pid")
        rss = s.get("rss")
        vms = s.get("vms")
        sys_pct = s.get("system_mem_percent")
        run_dir = s.get("_run_dir")
        extra = dict(s)
        extra.pop("ts", None)
        extra.pop("pid", None)
        extra.pop("rss", None)
        extra.pop("vms", None)
        extra.pop("system_mem_percent", None)
        extra.pop("_run_dir", None)
        rows.append((ts, "agent_sample", run_dir, pid, rss, vms, sys_pct, json.dumps(extra)))
        if run_dir:
            cur = max_by_run.get(run_dir, 0) or 0
            if rss and rss > cur:
                max_by_run[run_dir] = rss

    for s in iter_watcher_snapshots():
        ts = s.get("ts")
        sys = s.get("system", {})
        sys_pct = sys.get("percent") if isinstance(sys, dict) else None
        # For watcher snapshots, pick top process if present
        procs = s.get("processes") or []
        top = procs[0] if procs else {}
        pid = top.get("pid")
        rss = top.get("rss")
        vms = top.get("vms")
        rows.append((ts, "watcher_snapshot", None, pid, rss, vms, sys_pct, json.dumps({"file": s.get("_watch_file")})))

    # Write CSV
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["ts","source","run_dir","pid","rss","vms","system_mem_percent","extra_json"])
        for r in sorted(rows, key=lambda x: x[0] or 0):
            writer.writerow(r)

    # Write runs summary
    with runs_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["run_dir","max_rss_bytes"])
        for run, rss in sorted(max_by_run.items(), key=lambda x: x[1], reverse=True):
            writer.writerow([run, rss])

    print(f"Summary written to: {out_path}")
    print(f"Per-run max RSS written to: {runs_path}")


if __name__ == "__main__":
    main()
