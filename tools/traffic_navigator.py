"""Traffic Navigator: monitor and (optionally) control traffic routes and resource pressure.

Monitor-only mode (default):
- Writes outgoing/navigator.lock every --interval seconds with status="running" and phase="probe".
- Checks:
    - Agent1 + Triage heartbeats: detect contention (both running, non-probe triage), staleness, and idle states.
    - Disk space (repo and outgoing): warn if < 1 GB free.
    - CPU/memory (optional psutil): warn if CPU > 85% or available RAM < 500 MB; degrades gracefully without psutil.
- Sets a succinct status_message and a summary dict so the Watcher shows an "ok: ..." line.

Control mode (--control):
- Computes and writes navigator_control.lock with recommended controls consumed by triage_probe:
    - pause_until: epoch seconds to temporarily pause probes when Agent1 and Triage contend.
    - probe_interval_sec: interval override when system is hot or memory is low.
- Generates navigator_filters.json capturing learned heuristics from recent traffic (for audit + future use).
- Optionally posts a message to the Watcher command channel (best-effort; requires watcher to be running & unlocked).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
NAV_LOCK = OUT / "navigator.lock"
AGENT_LOCK = OUT / "agent1.lock"
TRIAGE_LOCK = OUT / "triage.lock"
CONTROL_LOCK = OUT / "navigator_control.lock"
FILTERS_JSON = OUT / "navigator_filters.json"
VERSION = "0.1.0"
LEADER_LOCK = OUT / "traffic_navigator.leader.lock"


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_hb(phase: str, status: str = "running", extra: Optional[Dict[str, Any]] = None) -> None:
    try:
        payload: Dict[str, Any] = {
            "name": "navigator",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": time.time(),
            "version": VERSION,
        }
        if extra:
            payload.update(extra)
        NAV_LOCK.parent.mkdir(parents=True, exist_ok=True)
        NAV_LOCK.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _acquire_leader_lock(stale_sec: int = 900) -> bool:
    """Best-effort single-writer guard via an exclusive lock file.

    Returns True if this process acquired leadership, False if another healthy
    leader is present. If a stale lock is detected (older than stale_sec), the
    lock will be removed and reacquired.
    """
    try:
        LEADER_LOCK.parent.mkdir(parents=True, exist_ok=True)
        # Try exclusive create
        with open(LEADER_LOCK, "x", encoding="utf-8") as f:
            payload = {
                "pid": os.getpid(),
                "ts": time.time(),
                "host": os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "unknown",
                "argv": sys.argv,
                "name": "traffic_navigator",
            }
            f.write(json.dumps(payload, ensure_ascii=False, indent=2))
        # Register atexit cleanup
        try:
            import atexit

            def _cleanup() -> None:
                try:
                    # Best-effort: only remove if it still looks like ours
                    data = _read_json(LEADER_LOCK) or {}
                    if int(data.get("pid") or -1) == os.getpid():
                        LEADER_LOCK.unlink(missing_ok=True)
                except Exception:
                    pass

            atexit.register(_cleanup)
        except Exception:
            pass
        return True
    except FileExistsError:
        # Check staleness
        try:
            age = time.time() - LEADER_LOCK.stat().st_mtime
            if age > float(stale_sec):
                # Stale; take over
                try:
                    LEADER_LOCK.unlink()
                except Exception:
                    pass
                # Retry once
                try:
                    with open(LEADER_LOCK, "x", encoding="utf-8") as f:
                        payload = {
                            "pid": os.getpid(),
                            "ts": time.time(),
                            "host": os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "unknown",
                            "argv": sys.argv,
                            "name": "traffic_navigator",
                            "note": "recovered_stale_lock",
                        }
                        f.write(json.dumps(payload, ensure_ascii=False, indent=2))
                    return True
                except Exception:
                    return False
            else:
                return False
        except Exception:
            # If we cannot assess, play it safe and do not acquire
            return False
    except Exception:
        # Any other error: do not proceed as leader
        return False


def _cpu_mem_snapshot() -> Dict[str, Any]:
    snap: Dict[str, Any] = {"backend": None}
    try:
        import psutil  # type: ignore
        snap["backend"] = "psutil"
        snap["cpu_percent"] = float(psutil.cpu_percent(interval=0.1))
        vm = psutil.virtual_memory()
        snap["mem_available_mb"] = int(vm.available / (1024 * 1024))
    except Exception:
        # Degrade gracefully when psutil is missing
        snap["backend"] = "none"
        snap["cpu_percent"] = None
        snap["mem_available_mb"] = None
    return snap


def _disk_free_mb(path: Path) -> int:
    try:
        usage = shutil.disk_usage(str(path))
        return int(usage.free / (1024 * 1024))
    except Exception:
        return -1


def evaluate(policy: str = "strict", stale_sec: int = 120) -> Dict[str, Any]:
    now = time.time()
    a = _read_json(AGENT_LOCK) or {}
    t = _read_json(TRIAGE_LOCK) or {}
    a_status = a.get("status") or "idle"
    t_status = t.get("status") or "idle"
    t_phase = t.get("phase") or "?"
    a_ago = int(max(0.0, now - float(a.get("ts") or 0.0))) if a else None
    t_ago = int(max(0.0, now - float(t.get("ts") or 0.0))) if t else None

    conflicts: list[str] = []
    notes: list[str] = []

    # Contention: both running and triage is not simple probe
    if a_status == "running" and t_status == "running" and str(t_phase) != "probe":
        conflicts.append("agent_and_triage_running")

    # Staleness
    if a_status == "running" and a_ago is not None and a_ago > int(stale_sec):
        conflicts.append("agent_stale")
    if t_status == "running" and t_ago is not None and t_ago > int(stale_sec):
        conflicts.append("triage_stale")

    # Disk space checks
    free_repo = _disk_free_mb(ROOT)
    free_out = _disk_free_mb(OUT)
    if free_repo >= 0 and free_repo < 1024:  # < 1 GB
        conflicts.append("disk_low_repo")
    if free_out >= 0 and free_out < 1024:
        conflicts.append("disk_low_outgoing")

    # CPU/Memory (optional)
    snap = _cpu_mem_snapshot()
    cpu = snap.get("cpu_percent")
    avail = snap.get("mem_available_mb")
    if isinstance(cpu, (int, float)) and cpu > 85.0:
        conflicts.append("cpu_hot")
    if isinstance(avail, int) and avail > -1 and avail < 500:
        conflicts.append("mem_low")

    # Policy tweaks (for future use)
    if policy == "lenient":
        # ignore cpu_hot in lenient mode
        conflicts = [c for c in conflicts if c != "cpu_hot"]

    healthy = len(conflicts) == 0

    if healthy:
        msg = "Routes nominal; resources OK"
    else:
        msg = f"Attention: {', '.join(conflicts)}"

    summary = {"healthy": healthy, "routes_ok": healthy, "no_conflicts": healthy}

    return {
        "status_message": msg,
        "summary": summary,
        "routes": {
            "agent1": a_status,
            "triage": f"{t_status}:{t_phase}",
        },
        "conflicts": conflicts,
        "resource": {
            "disk_mb": {"repo": free_repo, "outgoing": free_out},
            "cpu": cpu,
            "mem_available_mb": avail,
            "backend": snap.get("backend"),
        },
        "ago_s": {"agent1": a_ago, "triage": t_ago},
    }


def _decide_controls(evald: Dict[str, Any], now: float, policy: str, pause_sec: int, min_interval_hot: int, min_interval_cool: int) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[str]]:
    """From the evaluation snapshot, decide control overrides and learned filters.

    Returns (control_dict, filters_dict, human_message).
    """
    conflicts = list(evald.get("conflicts", []))
    res = evald.get("resource", {}) if isinstance(evald, dict) else {}
    cpu = res.get("cpu")
    avail = res.get("mem_available_mb")

    control: Dict[str, Any] = {}
    filters: Dict[str, Any] = {
        "suppress_probe_when_agent_running": True,
        "hot_cpu_min_interval_sec": int(min_interval_hot),
        "cool_cpu_min_interval_sec": int(min_interval_cool),
        "pause_on_contention_sec": int(pause_sec),
        "learned_at": int(now),
    }
    msgs: list[str] = []

    if "agent_and_triage_running" in conflicts:
        control["pause_until"] = int(now + max(10, pause_sec))
        msgs.append(f"pause triage until +{pause_sec}s (contention)")

    # Interval override policy
    hot = (isinstance(cpu, (int, float)) and cpu > 85.0) or (isinstance(avail, int) and avail >= 0 and avail < 500)
    if hot:
        control["probe_interval_sec"] = int(max(min_interval_hot, 45))
        msgs.append(f"probe interval {control['probe_interval_sec']}s (hot)")
    else:
        control["probe_interval_sec"] = int(max(min_interval_cool, 12))

    message = ", ".join(msgs) if msgs else None
    return control, filters, message


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Traffic Navigator — resource and routing monitor")
    ap.add_argument("--interval", type=float, default=3.0, help="Heartbeat interval seconds (default 3.0)")
    ap.add_argument("--policy", choices=["strict", "lenient"], default="strict", help="Conflict policy (default strict)")
    ap.add_argument("--stale-sec", type=int, default=120, help="Consider a row stale after this many seconds (default 120)")
    ap.add_argument("--max-iters", type=int, default=0, help="Optional: stop after N iterations (0 = run forever)")
    # Control mode flags
    ap.add_argument("--control", action="store_true", help="Enable control mode: write control lock + filters for triage_probe to consume")
    ap.add_argument("--pause-sec", type=int, default=90, help="On contention, pause triage for this many seconds (default 90)")
    ap.add_argument("--hot-interval", type=int, default=120, help="Min probe interval when system is hot (default 120)")
    ap.add_argument("--cool-interval", type=int, default=30, help="Default probe interval when system is cool (default 30)")
    ap.add_argument("--no-leader-guard", action="store_true", help="Disable single-writer guard (not recommended)")
    args = ap.parse_args(argv)

    # Single-writer guard to prevent conflicting control lock writers
    if not args.no_leader_guard:
        if not _acquire_leader_lock():
            # Another healthy navigator is active; exit quietly
            return 0

    i = 0
    # Initial
    snap = evaluate(policy=args.policy, stale_sec=args.stale_sec)
    _write_hb("probe", status="monitoring", extra=snap)
    if args.control:
        now = time.time()
        ctl, flt, msg = _decide_controls(snap, now, args.policy, int(args.pause_sec), int(args.hot_interval), int(args.cool_interval))
        _write_json(CONTROL_LOCK, ctl)
        _write_json(FILTERS_JSON, flt)
        # Best-effort notify watcher
        try:
            from tools.agent_control import post_command  # type: ignore
            if msg:
                post_command("append_log", {"text": f"[navigator] control: {msg}"}, sender="navigator")
        except Exception:
            pass

    try:
        while True:
            i += 1
            snap = evaluate(policy=args.policy, stale_sec=args.stale_sec)
            _write_hb("probe", status="monitoring", extra=snap)
            if args.control:
                now = time.time()
                ctl, flt, msg = _decide_controls(snap, now, args.policy, int(args.pause_sec), int(args.hot_interval), int(args.cool_interval))
                _write_json(CONTROL_LOCK, ctl)
                _write_json(FILTERS_JSON, flt)
                try:
                    from tools.agent_control import post_command  # type: ignore
                    if msg:
                        post_command("append_log", {"text": f"[navigator] control: {msg}"}, sender="navigator")
                except Exception:
                    pass
            time.sleep(max(0.25, float(args.interval)))
            if args.max_iters and i >= int(args.max_iters):
                break
    except KeyboardInterrupt:
        pass

    time.sleep(0.5)
    _write_hb("done", status="done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
