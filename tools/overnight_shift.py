"""Overnight shift supervisor: orchestrates navigator, scheduler, metrics, and logging."""
from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOG_DIR = ROOT / "logs" / "overnight"
CP6_LOCK = OUT / "cp6.lock"
CP7_LOCK = OUT / "cp7.lock"
CBO_LOCK = OUT / "cbo.lock"
AGENT1_LOCK = OUT / "agent1.lock"
AGENT_METRICS = ROOT / "logs" / "agent_metrics.csv"


def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _snapshot() -> str:
    now = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    cp6 = _read_json(CP6_LOCK) or {}
    cp7 = _read_json(CP7_LOCK) or {}
    cbo = _read_json(CBO_LOCK) or {}
    agent1 = _read_json(AGENT1_LOCK) or {}

    tes_row: Optional[dict] = None
    try:
        if AGENT_METRICS.exists():
            with AGENT_METRICS.open("r", encoding="utf-8") as fh:
                for line in fh.readlines()[1:]:
                    pass
                if line:
                    fields = line.strip().split(",")
                    if len(fields) >= 11:
                        tes_row = {
                            "ts": fields[0],
                            "tes": fields[1],
                            "status": fields[6],
                            "duration_s": fields[5],
                            "mode": fields[10],
                        }
    except Exception:
        pass

    def fmt(val: Optional[float], precision: int = 1) -> str:
        if val is None:
            return "n/a"
        try:
            return f"{float(val):.{precision}f}"
        except Exception:
            return str(val)

    lines = [f"## Snapshot {now}Z"]
    harmony = cp6.get("harmony") or {}
    lines.append(
        "- Harmony: "
        f"{fmt(harmony.get('score'))} (rhythm {fmt(harmony.get('rhythm'))}, "
        f"stability {fmt(harmony.get('stability'))}, "
        f"avg_gap_s {fmt(harmony.get('avg_gap_s'), precision=0)})"
    )
    drift = cp7.get("drift") or {}
    lines.append(
        "- Drift: latest "
        f"{fmt(drift.get('latest'), precision=0)} s, avg "
        f"{fmt(drift.get('avg'), precision=0)} s"
    )
    lines.append(
        "- Agent1: phase "
        f"{agent1.get('phase', 'n/a')}, status {agent1.get('status', 'n/a')}"
    )
    if tes_row:
        lines.append(
            "- Last agent run: TES "
            f"{tes_row.get('tes', 'n/a')}, status {tes_row.get('status', 'n/a')}, "
            f"duration_s {tes_row.get('duration_s', 'n/a')}, mode {tes_row.get('mode', 'n/a')}"
        )
    else:
        lines.append("- Last agent run: n/a")
    metrics = cbo.get("metrics") or {}
    lines.append(
        "- CBO metrics: CPU "
        f"{fmt(metrics.get('cpu_pct'))} %, RAM "
        f"{fmt(metrics.get('mem_used_pct'))} %, disk free "
        f"{fmt(metrics.get('disk_free_pct'))} %"
    )
    lines.append("")
    return "\n".join(lines)


def _run_logger(interval: int, output: Path, stop_event: threading.Event) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    while not stop_event.is_set():
        entry = _snapshot()
        with output.open("a", encoding="utf-8") as fh:
            fh.write(entry)
        if stop_event.wait(interval):
            break


@dataclass
class ManagedProcess:
    name: str
    argv: List[str]
    use_wsl: bool = False
    cwd: Path = ROOT
    restart_delay: int = 5
    process: Optional[subprocess.Popen] = field(default=None, init=False)

    def start(self) -> None:
        if self.use_wsl:
            cmd = ["wsl", "bash", "-lc", " ".join(self.argv)]
            self.process = subprocess.Popen(cmd, cwd=self.cwd)
        else:
            self.process = subprocess.Popen(self.argv, cwd=self.cwd)
        print(f"[overnight] {self.name} started (pid {self.process.pid})")

    def ensure_running(self) -> None:
        if self.process is None or self.process.poll() is not None:
            if self.process and self.process.returncode is not None:
                print(f"[overnight] {self.name} exited with {self.process.returncode}, restarting in {self.restart_delay}s")
                time.sleep(self.restart_delay)
            self.start()

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            try:
                if self.use_wsl:
                    self.process.terminate()
                else:
                    self.process.terminate()
                self.process.wait(timeout=10)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
        self.process = None


def main() -> int:
    parser = argparse.ArgumentParser(description="Overnight shift orchestrator")
    parser.add_argument("--interval", type=int, default=10, help="Seconds between health checks (default 10)")
    parser.add_argument("--navigator-interval", type=int, default=3)
    parser.add_argument("--navigator-hot", type=int, default=45)
    parser.add_argument("--navigator-cool", type=int, default=12)
    parser.add_argument("--navigator-pause", type=int, default=90)
    parser.add_argument("--scheduler-interval", type=int, default=240)
    parser.add_argument("--metrics-interval", type=int, default=900)
    parser.add_argument("--log-interval", type=int, default=300)
    parser.add_argument("--log-output", default="logs/overnight/overnight_shift.md")
    args = parser.parse_args()

    log_output = (ROOT / args.log_output).resolve()

    navigator_cmd = [
        sys.executable,
        "-u",
        str(ROOT / "tools" / "traffic_navigator.py"),
        "--control",
        "--interval",
        str(args.navigator_interval),
        "--pause-sec",
        str(args.navigator_pause),
        "--hot-interval",
        str(args.navigator_hot),
        "--cool-interval",
        str(args.navigator_cool),
        "--no-leader-guard",
    ]

    scheduler_cmd = [
        "source ~/.calyx-venv/bin/activate || true && cd /mnt/c/Calyx_Terminal && "
        "python -u tools/agent_scheduler.py "
        f"--interval {args.scheduler_interval} "
        "--mode tests "
        "--agent-args \"--skip-patches --run-tests\""
    ]

    metrics_cmd = [
        "source ~/.calyx-venv/bin/activate || true && cd /mnt/c/Calyx_Terminal && "
        f"python -u tools/metrics_cron.py --interval {args.metrics_interval}"
    ]

    processes = [
        ManagedProcess(name="Traffic Navigator", argv=navigator_cmd),
        ManagedProcess(name="Agent Scheduler", argv=scheduler_cmd, use_wsl=True),
        ManagedProcess(name="Metrics Cron", argv=metrics_cmd, use_wsl=True),
    ]

    stop_event = threading.Event()
    logger_thread = threading.Thread(
        target=_run_logger,
        args=(args.log_interval, log_output, stop_event),
        name="overnight-logger",
        daemon=True,
    )
    logger_thread.start()
    print(f"[overnight] Logging snapshots to {log_output}")

    def shutdown(signum: int, frame) -> None:  # type: ignore[override]
        print(f"[overnight] Received signal {signum}, stopping child processes...")
        stop_event.set()
        for mp in processes:
            mp.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        for mp in processes:
            mp.start()
        while True:
            for mp in processes:
                mp.ensure_running()
            time.sleep(max(5, args.interval))
    finally:
        stop_event.set()
        for mp in processes:
            mp.stop()


if __name__ == "__main__":
    raise SystemExit(main())
