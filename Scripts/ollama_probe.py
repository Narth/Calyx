#!/usr/bin/env python3
"""
Ollama attribution probe. Samples every 1s for up to 120s.
Windows: netstat -ano, Get-CimInstance, tasklist.
Emits runtime/receipts/perf/ollama_probe__{ts}.json
Stdlib only. No external deps.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CPU_THRESHOLD = 80
MAX_SAMPLES = 120
SAMPLE_INTERVAL = 1.0


def _run(cmd: list[str], timeout: int = 10, cwd: Path | None = None) -> tuple[str, str, int]:
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or REPO_ROOT,
            encoding="utf-8",
            errors="replace",
        )
        return r.stdout or "", r.stderr or "", r.returncode
    except Exception as e:
        return "", str(e), -1


def _find_ollama_pid() -> int | None:
    out, _, _ = _run(["powershell", "-NoProfile", "-Command",
        "Get-Process -Name ollama -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"])
    line = (out or "").strip().split("\n")[0] if out else ""
    try:
        return int(line) if line and line.isdigit() else None
    except ValueError:
        return None


def _get_ollama_cpu_rss(pid: int) -> tuple[float | None, float | None]:
    """Returns (cpu_percent, rss_mb). Uses WMI snapshot."""
    out, _, _ = _run(["powershell", "-NoProfile", "-Command", f"""
        $p = Get-Process -Id {pid} -ErrorAction SilentlyContinue
        if (-not $p) {{ return }}
        $rss = [math]::Round($p.WorkingSet64 / 1MB, 2)
        $cpu = $null
        try {{
            $perf = Get-CimInstance -ClassName Win32_PerfFormattedData_PerfProc_Process -Filter "IDProcess={pid}" -ErrorAction SilentlyContinue
            if ($perf) {{ $cpu = [math]::Round($perf.PercentProcessorTime, 1) }}
        }} catch {{}}
        Write-Output "$rss|$cpu"
    """], timeout=5)
    line = (out or "").strip().split("\n")[-1] if out else ""
    if "|" in line:
        parts = line.split("|")
        rss = float(parts[0]) if parts[0] and parts[0] != "None" else None
        cpu = float(parts[1]) if len(parts) > 1 and parts[1] and parts[1] != "None" else None
        return cpu, rss
    return None, None


def _get_ollama_models_active() -> list[str] | None:
    out, _, code = _run(["ollama", "ps"], timeout=5)
    if code != 0 or not out:
        return None
    lines = [l.strip() for l in out.split("\n") if l.strip()][1:]  # skip header
    return [l.split()[0] for l in lines if l] if lines else []


def _get_netstat_11434() -> list[dict]:
    """Get connections to :11434. Returns [{local, remote, state, pid}]."""
    out, _, _ = _run(["netstat", "-ano"], timeout=5)
    conns = []
    for line in (out or "").split("\n"):
        if ":11434" not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            local = parts[1] if len(parts) > 1 else ""
            remote = parts[2] if len(parts) > 2 else ""
            state = parts[3] if len(parts) > 3 else ""
            pid_str = parts[-1]
            pid = int(pid_str) if pid_str.isdigit() else None
            conns.append({"local": local, "remote": remote, "state": state, "pid": pid})
        except (ValueError, IndexError):
            pass
    return conns


def _pid_to_process(pid: int) -> dict:
    """Map PID to {pid, name, cmdline?}."""
    out, _, _ = _run(["powershell", "-NoProfile", "-Command", f"""
        $p = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId={pid}" -ErrorAction SilentlyContinue
        if (-not $p) {{ Write-Output "||"; return }}
        $n = $p.Name
        $c = $p.CommandLine
        if (-not $c) {{ $c = "" }}
        Write-Output "$n|$c"
    """], timeout=5)
    line = (out or "").strip().split("\n")[-1] if out else "||"
    parts = line.split("|", 2)
    name = parts[0] if parts else ""
    cmdline = parts[1] if len(parts) > 1 else ""
    if len(parts) > 2:
        cmdline = parts[1] + "|" + parts[2]
    return {"pid": pid, "name": name or "unknown", "cmdline": cmdline[:500] if cmdline else None}


def _classify(ollama_cpu: float | None, rss_mb: float | None, caller_processes: list) -> str:
    if ollama_cpu is None and not caller_processes:
        return "UNKNOWN"
    if ollama_cpu is not None and ollama_cpu >= CPU_THRESHOLD:
        if caller_processes:
            return "HAMMERED_BY_CLIENT"
        return "STUCK_NO_CLIENTS"
    if ollama_cpu is not None and ollama_cpu > 0:
        return "ACTIVE_GENERATION"
    return "UNKNOWN"


def _read_node_id() -> str:
    p = REPO_ROOT / "runtime" / "node_id.txt"
    if p.exists():
        return p.read_text(encoding="utf-8").strip() or "unknown"
    return "unknown"


def run_probe(duration_s: int = 30, max_samples: int = MAX_SAMPLES) -> dict:
    """Run probe for duration_s seconds. Returns summary receipt."""
    perf_dir = REPO_ROOT / "runtime" / "receipts" / "perf"
    perf_dir.mkdir(parents=True, exist_ok=True)

    node_id = _read_node_id()
    samples = []
    spike_ticks = []
    caller_freq: dict[str, int] = {}
    commands_run = []

    end_at = time.monotonic() + min(duration_s, max_samples * int(SAMPLE_INTERVAL))
    tick = 0

    while time.monotonic() < end_at and tick < max_samples:
        tick += 1
        ollama_pid = _find_ollama_pid()
        cpu, rss = _get_ollama_cpu_rss(ollama_pid) if ollama_pid else (None, None)
        models = _get_ollama_models_active()
        conns = _get_netstat_11434()

        # Filter conns: exclude ollama's own PID, get client PIDs
        client_pids = [c["pid"] for c in conns if c.get("pid") and c["pid"] != ollama_pid]
        client_pids = list(dict.fromkeys(client_pids))[:5]
        caller_processes = [_pid_to_process(p) for p in client_pids]
        if not client_pids and ollama_pid:
            caller_processes = [{"pid": None, "name": "NO_CLIENTS_OBSERVED", "cmdline": None}]

        for cp in caller_processes:
            key = cp.get("name") or str(cp.get("pid"))
            if key != "NO_CLIENTS_OBSERVED":
                caller_freq[key] = caller_freq.get(key, 0) + 1

        if cpu is not None and cpu >= CPU_THRESHOLD:
            spike_ticks.append({"tick": tick, "cpu": cpu, "callers": [cp.get("name") for cp in caller_processes]})

        samples.append({
            "tick": tick,
            "ollama_pid": ollama_pid,
            "ollama_cpu_estimate": cpu,
            "ollama_rss_mb": rss,
            "caller_processes": caller_processes,
        })

        time.sleep(SAMPLE_INTERVAL)

    # Build final receipt
    last = samples[-1] if samples else {}
    classification = _classify(
        last.get("ollama_cpu_estimate"),
        last.get("ollama_rss_mb"),
        last.get("caller_processes", []),
    )
    conns_final = _get_netstat_11434()
    caller_processes_final = []
    for c in conns_final:
        if c.get("pid") and c["pid"] != last.get("ollama_pid"):
            caller_processes_final.append(_pid_to_process(c["pid"]))

    if not caller_processes_final:
        caller_processes_final = [{"pid": None, "name": "NO_CLIENTS_OBSERVED", "cmdline": None}]

    top_callers = sorted(caller_freq.items(), key=lambda x: -x[1])[:5]

    receipt = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "node_id": node_id,
        "ollama_pid": last.get("ollama_pid"),
        "ollama_cpu_estimate": last.get("ollama_cpu_estimate"),
        "ollama_rss_mb": last.get("ollama_rss_mb"),
        "ollama_models_active": _get_ollama_models_active(),
        "net_11434_connections": [{"local": c["local"], "remote": c["remote"], "state": c["state"], "pid": c.get("pid")} for c in conns_final],
        "caller_processes": caller_processes_final,
        "classification": classification,
        "evidence": {
            "commands_run": ["Get-Process", "Get-CimInstance", "netstat -ano", "ollama ps"],
            "notes": f"spike_ticks={len(spike_ticks)}, samples={len(samples)}, top_callers={top_callers}",
        },
        "summary": {
            "spike_ticks": len(spike_ticks),
            "spike_ticks_with_clients": sum(1 for s in spike_ticks if s.get("callers") and s["callers"] != ["NO_CLIENTS_OBSERVED"]),
            "top_callers": top_callers,
        },
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = perf_dir / f"ollama_probe__{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False, sort_keys=True)
    return receipt


def main() -> int:
    duration = 30
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            pass
    run_probe(duration_s=duration)
    return 0


if __name__ == "__main__":
    sys.exit(main())
