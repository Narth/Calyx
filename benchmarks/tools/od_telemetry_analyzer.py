"""
Outcome Density telemetry analyzer (no heuristics).

Contract (enforced):
- RUN_START and RUN_END must exist in logs/system/prompt_phases.jsonl for the given run_id.
- Each prompt must have PROMPT_START and PROMPT_END.
- Durations use monotonic_ns deltas (primary). If missing, analysis refuses.
- Resource coverage is computed only from resource_usage.jsonl samples tagged with run_id.
- No filesystem mtime inference; missing markers => error.

Outputs:
- reports/outcome_density/<run_id>_telemetry_summary.md
- reports/outcome_density/<run_id>_telemetry_summary.json
- reports/outcome_density/<run_id>_telemetry_by_prompt.csv

Degraded run if:
- coverage_pct < 0.95 OR any gap > 2 * median_interval OR missing GPU power in >50% samples.
"""

import argparse
import json
import statistics
from pathlib import Path
from datetime import datetime, timezone


def parse_iso(ts: str):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def load_phases(run_id: str, path: Path):
    phases = []
    if not path.exists():
        raise SystemExit(f"Phase log missing: {path}")
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("run_id") != run_id:
                continue
            phases.append(obj)
    return phases


def ensure_markers(phases):
    run_start = [p for p in phases if p.get("event") == "RUN_START"]
    run_end = [p for p in phases if p.get("event") == "RUN_END"]
    if not run_start or not run_end:
        raise SystemExit("RUN_START/RUN_END missing for run")
    rs = run_start[-1]
    re = run_end[-1]
    if "monotonic_ns" not in rs or "monotonic_ns" not in re:
        raise SystemExit("monotonic_ns missing in run markers")
    if re["monotonic_ns"] <= rs["monotonic_ns"]:
        raise SystemExit("RUN_END monotonic <= RUN_START")
    return rs, re


def collect_prompts(phases):
    prompt_starts = {}
    prompt_ends = {}
    for p in phases:
        ev = p.get("event")
        pid = p.get("prompt_id")
        if ev == "PROMPT_START":
            prompt_starts.setdefault(pid, []).append(p)
        elif ev == "PROMPT_END":
            prompt_ends.setdefault(pid, []).append(p)
    prompts = {}
    for pid in sorted(set(prompt_starts) | set(prompt_ends)):
        if pid is None:
            continue
        s_list = prompt_starts.get(pid, [])
        e_list = prompt_ends.get(pid, [])
        if not s_list or not e_list:
            raise SystemExit(f"Missing start/end for prompt {pid}")
        s = s_list[-1]
        e = e_list[-1]
        if "monotonic_ns" not in s or "monotonic_ns" not in e:
            raise SystemExit(f"monotonic_ns missing for prompt {pid}")
        if e["monotonic_ns"] <= s["monotonic_ns"]:
            raise SystemExit(f"Negative duration for prompt {pid}")
        prompts[pid] = {
            "start_mono": s["monotonic_ns"],
            "end_mono": e["monotonic_ns"],
            "start_ts": s["timestamp_utc"],
            "end_ts": e["timestamp_utc"],
        }
    return prompts


def load_resource(run_id: str, path: Path, window_start: datetime, window_end: datetime):
    samples = []
    if not path.exists():
        raise SystemExit(f"Resource log missing: {path}")
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("tag") != run_id:
                continue
            ts = obj.get("timestamp")
            try:
                dt = parse_iso(ts)
            except Exception:
                continue
            if dt < window_start or dt > window_end:
                continue
            obj["dt"] = dt
            samples.append(obj)
    samples.sort(key=lambda x: x["dt"])
    return samples


def aggregate_samples(samples):
    if not samples:
        return None
    cpu = [s.get("cpu_percent") for s in samples if s.get("cpu_percent") is not None]
    ram_gb = [s.get("ram_used_gb") for s in samples if s.get("ram_used_gb") is not None]
    ram_pct = [s.get("ram_percent") for s in samples if s.get("ram_percent") is not None]
    gpu_util = []
    gpu_mem = []
    gpu_power = []
    for s in samples:
        g = s.get("gpu")
        if g and isinstance(g, list) and g:
            g0 = g[0]
            if g0.get("util_percent") is not None:
                gpu_util.append(g0["util_percent"])
            if g0.get("mem_used_mb") is not None:
                gpu_mem.append(g0["mem_used_mb"])
            if g0.get("power_w") is not None:
                gpu_power.append((s["dt"], g0["power_w"]))
    def agg(arr):
        if not arr:
            return {"avg": None, "max": None}
        return {"avg": statistics.fmean(arr), "max": max(arr)}
    energy_wh = None
    power_cov = None
    if len(gpu_power) >= 2:
        gpu_power.sort(key=lambda x: x[0])
        total = 0.0
        covered = 0.0
        for (t1, p1), (t2, p2) in zip(gpu_power, gpu_power[1:]):
            dt = (t2 - t1).total_seconds()
            if dt < 0:
                continue
            total += ((p1 + p2) / 2.0) * dt / 3600.0
            covered += dt
        span = (samples[-1]["dt"] - samples[0]["dt"]).total_seconds()
        energy_wh = total
        power_cov = covered / span if span > 0 else None
    return {
        "n_samples": len(samples),
        "cpu": agg(cpu),
        "ram_gb": agg(ram_gb),
        "ram_percent": agg(ram_pct),
        "gpu_util": agg(gpu_util),
        "gpu_mem_mb": agg(gpu_mem),
        "gpu_power_w": agg([p for _, p in gpu_power]),
        "gpu_energy_wh": energy_wh,
        "power_coverage": power_cov,
    }


def coverage_metrics(samples, run_start: datetime, run_end: datetime):
    if len(samples) < 2:
        return {"coverage_pct": 0.0, "median_dt": None, "max_gap": None, "degraded": True, "reason": "insufficient samples"}
    deltas = [(samples[i + 1]["dt"] - samples[i]["dt"]).total_seconds() for i in range(len(samples) - 1) if (samples[i + 1]["dt"] - samples[i]["dt"]).total_seconds() >= 0]
    if not deltas:
        return {"coverage_pct": 0.0, "median_dt": None, "max_gap": None, "degraded": True, "reason": "nonpositive deltas"}
    median_dt = statistics.median(deltas)
    max_gap = max(deltas)
    observed = (samples[-1]["dt"] - samples[0]["dt"]).total_seconds()
    run_span = (run_end - run_start).total_seconds()
    coverage_pct = observed / run_span if run_span > 0 else 0.0
    return {
        "coverage_pct": coverage_pct,
        "median_dt": median_dt,
        "max_gap": max_gap,
        "degraded": (coverage_pct < 0.95) or (max_gap > 2 * median_dt),
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze OD telemetry with zero heuristics.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--phase-log", type=Path, default=Path("logs/system/prompt_phases.jsonl"))
    parser.add_argument("--resource-log", type=Path, default=Path("logs/system/resource_usage.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/outcome_density"))
    parser.add_argument("--prompt-index", type=Path, default=None, help="Optional prompt_index.jsonl to enforce envelopes/reflections.")
    args = parser.parse_args()

    phases = load_phases(args.run_id, args.phase_log)
    run_start, run_end = ensure_markers(phases)
    prompts = collect_prompts(phases)

    # Run window by wall clock (UTC)
    run_start_ts = parse_iso(run_start["timestamp_utc"])
    run_end_ts = parse_iso(run_end["timestamp_utc"])

    # Load resource samples tagged with run_id
    samples = load_resource(args.run_id, args.resource_log, run_start_ts, run_end_ts)
    coverage = coverage_metrics(samples, run_start_ts, run_end_ts)
    agg_all = aggregate_samples(samples) if samples else None

    # Load prompt meta if available
    prompt_meta = {}
    if args.prompt_index and args.prompt_index.exists():
        metas = []
        with args.prompt_index.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    metas.append(json.loads(line))
                except Exception:
                    continue
        for m in metas:
            pid = m.get("prompt_id")
            if pid:
                prompt_meta[pid] = m

    require_station = args.run_id.startswith("OD-GENERATION")
    per_prompt = []
    for pid, info in sorted(prompts.items()):
        p_start = parse_iso(info["start_ts"])
        p_end = parse_iso(info["end_ts"])
        samps = [s for s in samples if p_start <= s["dt"] <= p_end]
        duration_sec = (info["end_mono"] - info["start_mono"]) / 1e9
        non_gen = duration_sec < 1.0  # hard gate
        metrics = None if non_gen else (aggregate_samples(samps) if samps else None)
        meta = prompt_meta.get(pid)
        env_ok = not require_station or (meta and meta.get("envelope_id") and meta.get("reflection_id"))
        refl_source = meta.get("reflection_source") if meta else None
        per_prompt.append(
            {
                "prompt_id": pid,
                "start_utc": info["start_ts"],
                "end_utc": info["end_ts"],
                "duration_sec": duration_sec,
                "n_samples": len(samps),
                "metrics": metrics,
                "non_generation": non_gen,
                "envelope_present": bool(meta and meta.get("envelope_id")),
                "reflection_present": bool(meta and meta.get("reflection_id")),
                "reflection_source": refl_source,
            }
        )

    degraded_reasons = []
    if coverage["degraded"]:
        degraded_reasons.append("resource coverage below threshold or gaps too large")
    if agg_all and agg_all["gpu_power_w"]["avg"] is None:
        degraded_reasons.append("no GPU power data in samples")
    if require_station:
        missing_env = [p for p in per_prompt if not p["envelope_present"] or not p["reflection_present"]]
        if missing_env:
            degraded_reasons.append("missing envelope/reflection metadata for some prompts")
        stub_refl = [p for p in per_prompt if p.get("reflection_source") == "stub"]
        if stub_refl:
            degraded_reasons.append("stub reflections present")
    missing_samples = [p for p in per_prompt if p["metrics"] is None]
    if missing_samples:
        degraded_reasons.append("some prompts have no telemetry metrics (non-generation or no samples)")

    summary = {
        "run_id": args.run_id,
        "run_start_utc": run_start["timestamp_utc"],
        "run_end_utc": run_end["timestamp_utc"],
        "run_duration_sec": (run_end["monotonic_ns"] - run_start["monotonic_ns"]) / 1e9,
        "coverage": coverage,
        "overall": agg_all,
        "per_prompt": per_prompt,
        "degraded": bool(degraded_reasons),
        "degraded_reasons": degraded_reasons,
    }

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{args.run_id}_telemetry_summary.md"
    json_path = out_dir / f"{args.run_id}_telemetry_summary.json"
    csv_path = out_dir / f"{args.run_id}_telemetry_by_prompt.csv"

    # Write JSON
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write MD
    lines = []
    lines.append(f"# Telemetry Summary for {args.run_id}")
    lines.append("")
    lines.append(f"Run: {run_start['timestamp_utc']} to {run_end['timestamp_utc']} (duration {summary['run_duration_sec']:.2f}s)")
    lines.append(f"Degraded: {summary['degraded']} ({'; '.join(degraded_reasons) if degraded_reasons else 'none'})")
    lines.append(f"Coverage pct: {coverage['coverage_pct']:.3f} | median dt: {coverage['median_dt']}s | max gap: {coverage['max_gap']}s")
    lines.append("")
    lines.append("## Overall")
    if agg_all:
        lines.append(f"Samples: {agg_all['n_samples']}")
        lines.append(f"CPU avg/max: {agg_all['cpu']['avg']} / {agg_all['cpu']['max']}")
        lines.append(f"RAM GB avg/max: {agg_all['ram_gb']['avg']} / {agg_all['ram_gb']['max']}")
        lines.append(f"RAM % avg/max: {agg_all['ram_percent']['avg']} / {agg_all['ram_percent']['max']}")
        lines.append(f"GPU util avg/max: {agg_all['gpu_util']['avg']} / {agg_all['gpu_util']['max']}")
        lines.append(f"GPU mem MB avg/max: {agg_all['gpu_mem_mb']['avg']} / {agg_all['gpu_mem_mb']['max']}")
        lines.append(f"GPU power W avg/max: {agg_all['gpu_power_w']['avg']} / {agg_all['gpu_power_w']['max']}")
        lines.append(f"GPU energy Wh: {agg_all['gpu_energy_wh']}")
        lines.append(f"Power coverage: {agg_all['power_coverage']}")
    else:
        lines.append("No samples.")
    lines.append("")
    lines.append("## Per Prompt")
    for p in per_prompt:
        lines.append(f"### {p['prompt_id']}")
        lines.append(f"Window: {p['start_utc']} to {p['end_utc']} (duration {p['duration_sec']:.2f}s)")
        lines.append(f"Envelope: {p['envelope_present']} | Reflection: {p['reflection_present']}")
        lines.append(f"Reflection source: {p.get('reflection_source')}")
        if p["non_generation"]:
            lines.append("Flagged as non-generation (duration < 1s); metrics excluded.")
            lines.append("")
            continue
        if not p["metrics"]:
            lines.append("No samples in prompt window.")
        else:
            m = p["metrics"]
            lines.append(f"Samples: {m['n_samples']}")
            lines.append(f"CPU avg/max: {m['cpu']['avg']} / {m['cpu']['max']}")
            lines.append(f"RAM GB avg/max: {m['ram_gb']['avg']} / {m['ram_gb']['max']}")
            lines.append(f"RAM % avg/max: {m['ram_percent']['avg']} / {m['ram_percent']['max']}")
            lines.append(f"GPU util avg/max: {m['gpu_util']['avg']} / {m['gpu_util']['max']}")
            lines.append(f"GPU mem MB avg/max: {m['gpu_mem_mb']['avg']} / {m['gpu_mem_mb']['max']}")
            lines.append(f"GPU power W avg/max: {m['gpu_power_w']['avg']} / {m['gpu_power_w']['max']}")
            lines.append(f"GPU energy Wh: {m['gpu_energy_wh']}")
            lines.append(f"Power coverage: {m['power_coverage']}")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    # CSV
    with csv_path.open("w", encoding="utf-8") as f:
        f.write("prompt_id,start_utc,end_utc,duration_sec,n_samples,non_generation,envelope_present,reflection_present,cpu_avg,cpu_max,ram_gb_avg,ram_gb_max,ram_pct_avg,ram_pct_max,gpu_util_avg,gpu_util_max,gpu_mem_avg,gpu_mem_max,gpu_power_avg,gpu_power_max,gpu_energy_wh,power_coverage\n")
        for p in per_prompt:
            m = p["metrics"]
            if not m:
                row = [p["prompt_id"], p["start_utc"], p["end_utc"], f"{p['duration_sec']:.2f}", 0, p["non_generation"], p["envelope_present"], p["reflection_present"], "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
            else:
                row = [
                    p["prompt_id"],
                    p["start_utc"],
                    p["end_utc"],
                    f"{p['duration_sec']:.2f}",
                    m["n_samples"],
                    p["non_generation"],
                    p["envelope_present"],
                    p["reflection_present"],
                    m["cpu"]["avg"] if m["cpu"]["avg"] is not None else "",
                    m["cpu"]["max"] if m["cpu"]["max"] is not None else "",
                    m["ram_gb"]["avg"] if m["ram_gb"]["avg"] is not None else "",
                    m["ram_gb"]["max"] if m["ram_gb"]["max"] is not None else "",
                    m["ram_percent"]["avg"] if m["ram_percent"]["avg"] is not None else "",
                    m["ram_percent"]["max"] if m["ram_percent"]["max"] is not None else "",
                    m["gpu_util"]["avg"] if m["gpu_util"]["avg"] is not None else "",
                    m["gpu_util"]["max"] if m["gpu_util"]["max"] is not None else "",
                    m["gpu_mem_mb"]["avg"] if m["gpu_mem_mb"]["avg"] is not None else "",
                    m["gpu_mem_mb"]["max"] if m["gpu_mem_mb"]["max"] is not None else "",
                    m["gpu_power_w"]["avg"] if m["gpu_power_w"]["avg"] is not None else "",
                    m["gpu_power_w"]["max"] if m["gpu_power_w"]["max"] is not None else "",
                    m["gpu_energy_wh"] if m["gpu_energy_wh"] is not None else "",
                    m["power_coverage"] if m["power_coverage"] is not None else "",
                ]
            f.write(",".join(str(x) for x in row) + "\n")

    print("Wrote:", md_path, json_path, csv_path)


if __name__ == "__main__":
    main()
