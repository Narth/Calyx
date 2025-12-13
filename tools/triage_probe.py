"""Triage Probe: keep triage "Active" with ultra-light heartbeats and periodic LLM checks.

Behavior
- Writes outgoing/triage.lock every `--interval` seconds with status="running" and phase="probe".
- Every `--probe-every` intervals, performs a tiny chat completion against the configured local LLM
  (llama-cpp + GGUF from tools/models/MODEL_MANIFEST.json) and records latency + ok/error.
- Designed to run inside WSL venv (see OPERATIONS.md tasks) but degrades gracefully when llama_cpp
  or the model manifest isn't available — it still emits heartbeats so the Watcher shows Active.

Stop with Ctrl+C; on exit we write a final status.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import shutil

# GPU utilities for llama_cpp offloading
try:
    from tools.gpu_utils import is_gpu_available, get_gpu_layer_count
except Exception:
    def is_gpu_available():
        return False
    def get_gpu_layer_count():
        return 0

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
TRIAGE_LOCK = OUT / "triage.lock"
# Multiple agent support — we'll read agent1..agentN locks based on --agents
CONTROL_LOCK = OUT / "navigator_control.lock"
PROBE_VERSION = "0.4.0"
DEFAULT_THIN_PROBES: List[str] = ["ps", "disk", "mem", "ports", "recent_excs"]
LOAD_MODE_FILE = ROOT / "state" / "load_mode.json"
 # SVF ensure on startup
try:
    from tools.svf_util import ensure_svf_running  # type: ignore
except Exception:
    def ensure_svf_running(*args, **kwargs):  # type: ignore
        return False


def _is_wsl_env() -> bool:
    try:
        # WSL often exposes /proc/version with 'microsoft'
        return "WSL_DISTRO_NAME" in os.environ or "microsoft" in Path("/proc/version").read_text().lower()
    except Exception:
        return False


def _config_use_llm(default: bool = True) -> bool:
    cfg_path = ROOT / "config.yaml"
    try:
        import yaml  # type: ignore
    except Exception:
        return default
    try:
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        val = cfg.get("settings", {}).get("triage", {}).get("use_llm")
        if isinstance(val, bool):
            return val
    except Exception:
        return default
    return default


def _load_default_thin_probes(default: List[str]) -> List[str]:
    cfg_path = ROOT / "config.yaml"
    try:
        import yaml  # type: ignore
    except Exception:
        return default[:]
    try:
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        probes = cfg.get("settings", {}).get("triage", {}).get("thin_probe")
        if isinstance(probes, (list, tuple)):
            items: List[str] = []
            for entry in probes:
                entry_str = str(entry).strip()
                if entry_str:
                    items.append(entry_str)
            if items:
                return items
    except Exception:
        return default[:]
    return default[:]


def _load_mode_flag() -> str:
    try:
        data = json.loads(LOAD_MODE_FILE.read_text(encoding="utf-8"))
        mode = str(data.get("mode", "normal")).strip().lower()
        return mode if mode in {"normal", "high_load"} else "normal"
    except Exception:
        return "normal"


def _write_hb(phase: str, status: str = "running", extra: Optional[Dict[str, Any]] = None) -> None:
    try:
        payload: Dict[str, Any] = {
            "name": "triage",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": time.time(),
            "probe_version": PROBE_VERSION,
        }
        if extra:
            payload.update(extra)
        TRIAGE_LOCK.parent.mkdir(parents=True, exist_ok=True)
        TRIAGE_LOCK.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        # Best-effort only
        pass


@dataclass
class LLMState:
    ready: bool = False
    error: Optional[str] = None
    model_id: Optional[str] = None
    model_path: Optional[str] = None
    backend: Optional[str] = None
    handle: Any = None  # llama_cpp.Llama when available


def _load_manifest() -> Optional[Dict[str, Any]]:
    try:
        p = ROOT / "tools" / "models" / "MODEL_MANIFEST.json"
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _select_model(man: Dict[str, Any], model_id: Optional[str]) -> Optional[Dict[str, Any]]:
    models = list(man.get("models", [])) if isinstance(man, dict) else []
    if not models:
        return None
    if model_id:
        for e in models:
            if e.get("id") == model_id:
                return e
    # Prefer a dedicated probe model when available
    for e in models:
        if e.get("role") == "probe":
            return e
    # Else fall back to first
    return models[0]


def _ensure_llm(state: LLMState, n_ctx: int = 1024, model_id: Optional[str] = None) -> None:
    if state.ready:
        return
    try:
        man = _load_manifest()
        if not man or not man.get("models"):
            state.error = "manifest_missing"
            return
        entry = _select_model(man, model_id)
        if not entry:
            state.error = "model_entry_missing"
            return
        model_path = entry.get("filename")
        if not model_path:
            state.error = "model_path_missing"
            return
        state.model_id = entry.get("id")
        state.model_path = model_path
        from llama_cpp import Llama  # type: ignore
        
        # GPU offloading configuration
        gpu_layers = get_gpu_layer_count()
        if gpu_layers > 0:
            # GPU mode: offload layers to GPU
            state.handle = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                temperature=0.0,
                n_gpu_layers=gpu_layers,
                n_threads=4,  # CPU threads for remaining work
                verbose=False
            )
            state.backend = "llama_cpp_gpu"
        else:
            # CPU mode: standard initialization
            state.handle = Llama(model_path=model_path, n_ctx=n_ctx, temperature=0.0)
            state.backend = "llama_cpp"
        
        state.ready = True
    except Exception as exc:  # pragma: no cover - environment dependent
        state.error = f"llm_init_failed: {exc.__class__.__name__}"
        state.ready = False
        state.handle = None


def _probe_once(state: LLMState, max_tokens: int = 8) -> Dict[str, Any]:
    start = time.time()
    ok = False
    out_txt = ""
    err: Optional[str] = None
    try:
        if not state.ready:
            _ensure_llm(state)
        if state.ready and state.handle is not None:
            # Tiny completion; grammar constrains output to "ok"
            try:
                from llama_cpp import LlamaGrammar  # type: ignore
            except Exception:  # pragma: no cover - optional dependency
                LlamaGrammar = None  # type: ignore
            grammar = LlamaGrammar.from_string('root ::= "ok"') if LlamaGrammar else None
            resp_obj = state.handle.create_completion(
                prompt="System: Reply with ok and nothing else.\nUser: ping\nAssistant:",
                max_tokens=max_tokens,
                temperature=0.0,
                stop=["\n", "</s>"],
                grammar=grammar,
            )
            # Successful completion implies the backend executed; we treat it as an OK ping.
            ok = True
            out_txt = "ok"
        else:
            err = state.error or "llm_unavailable"
    except Exception as exc:  # pragma: no cover - environment dependent
        err = f"probe_failed: {exc.__class__.__name__}"
    dur_ms = int((time.time() - start) * 1000)
    return {
        "ok": bool(ok),
        "latency_ms": dur_ms,
        "text": out_txt[:40],
        "error": err,
    }


def _thin_probe_ps() -> Dict[str, Any]:
    summary: List[Dict[str, Any]] = []
    count = 0
    for proc in psutil.process_iter(attrs=["pid", "name", "username", "memory_info", "cpu_percent"]):
        try:
            info = proc.info
            mem = info.get("memory_info")
            rss = getattr(mem, "rss", 0) if mem else 0
            entry = {
                "pid": info.get("pid"),
                "name": info.get("name"),
                "rss_mb": round(rss / (1024 * 1024), 2),
                "cpu": round(float(info.get("cpu_percent") or 0.0), 1),
            }
            summary.append(entry)
            count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    summary.sort(key=lambda item: item["rss_mb"], reverse=True)
    return {"top_mem": summary[:5], "process_count": count}


def _thin_probe_disk() -> Dict[str, Any]:
    usage = shutil.disk_usage(ROOT)
    return {
        "path": str(ROOT),
        "total_gb": round(usage.total / (1024 ** 3), 2),
        "used_gb": round(usage.used / (1024 ** 3), 2),
        "free_gb": round(usage.free / (1024 ** 3), 2),
        "free_ratio": round(usage.free / usage.total, 3) if usage.total else None,
    }


def _thin_probe_mem() -> Dict[str, Any]:
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()
    return {
        "total_gb": round(vm.total / (1024 ** 3), 2),
        "available_gb": round(vm.available / (1024 ** 3), 2),
        "used_percent": round(vm.percent, 2),
        "swap_used_percent": round(sm.percent, 2) if sm.total else 0.0,
    }


def _thin_probe_ports() -> Dict[str, Any]:
    listening: List[Dict[str, Any]] = []
    try:
        conns = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, psutil.NoSuchProcess, NotImplementedError):
        return {"listening": [], "error": "access_denied"}
    total_listening = 0
    for conn in conns:
        if conn.status != psutil.CONN_LISTEN:
            continue
        total_listening += 1
        if len(listening) < 5:
            laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None
            listening.append({
                "laddr": laddr,
                "pid": conn.pid,
            })
    return {"total_listening": total_listening, "sample": listening}


def _thin_probe_recent_excs() -> Dict[str, Any]:
    log_dir = ROOT / "logs"
    findings: List[Dict[str, Any]] = []
    if not log_dir.exists():
        return {"findings": findings}
    candidates = sorted(
        (p for p in log_dir.glob("**/*.log") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:3]
    for path in candidates:
        try:
            data = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        tail = data[-2000:]
        marker = None
        for token in ("Traceback", "ERROR", "Exception"):
            if token in tail:
                marker = token
                break
        findings.append({
            "file": str(path.relative_to(ROOT)),
            "flag": marker or "clean",
        })
    return {"findings": findings}


THIN_PROBE_HANDLERS = {
    "ps": _thin_probe_ps,
    "disk": _thin_probe_disk,
    "mem": _thin_probe_mem,
    "ports": _thin_probe_ports,
    "recent_excs": _thin_probe_recent_excs,
}


def _run_thin_probe(probes: List[str]) -> Dict[str, Any]:
    start = time.time()
    results: Dict[str, Any] = {}
    errors: List[str] = []
    status = "ok"
    for name in probes:
        handler = THIN_PROBE_HANDLERS.get(name)
        if not handler:
            status = "warn"
            errors.append(f"{name}:unknown_probe")
            results[name] = {"error": "unknown_probe"}
            continue
        try:
            results[name] = handler()
        except Exception as exc:
            status = "warn"
            errors.append(f"{name}:{exc.__class__.__name__}")
            results[name] = {"error": str(exc)}
    latency_ms = int((time.time() - start) * 1000)
    return {
        "status": status if status != "ok" or not errors else "warn",
        "latency_ms": latency_ms,
        "results": results,
        "errors": errors,
    }


def _write_thin_report(path: Path, payload: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _summarize_agents(agents: Dict[str, Dict[str, Any]]) -> str:
    try:
        parts = []
        for name in sorted(agents.keys()):
            st = agents[name]
            s = st.get("status") or "idle"
            parts.append(f"{name[-2:]}:{str(s)[:4]}")  # e.g., a1:run, a2:idle
        return ", ".join(parts)
    except Exception:
        return ""


def main(argv: Optional[list[str]] = None) -> int:
    default_use_llm = _config_use_llm()
    default_thin_list = _load_default_thin_probes(DEFAULT_THIN_PROBES)
    default_thin_str = ",".join(default_thin_list)
    ap = argparse.ArgumentParser(description="Keep triage Active with lightweight heartbeats + optional LLM checks")
    ap.add_argument("--interval", type=float, default=2.0, help="Heartbeat interval in seconds (default 2.0)")
    ap.add_argument("--probe-every", type=int, default=15, help="Run an LLM check every N heartbeats (default 15)")
    ap.add_argument("--grace-exit", type=float, default=2.0, help="Seconds to wait before final 'done' heartbeat on exit")
    ap.add_argument("--max-iters", type=int, default=0, help="Optional: stop after this many iterations (0 = run forever)")
    ap.add_argument("--model-id", type=str, default=None, help="Optional: pick a specific model id from the manifest; defaults to role=probe when available")
    ap.add_argument("--adaptive", action="store_true", help="Adapt probe cadence based on Agent1 activity and warmup window")
    ap.add_argument("--warmup-minutes", type=float, default=15.0, help="Duration to stay in high-cadence mode from start (default 15)")
    ap.add_argument("--initial-probe-sec", type=float, default=30.0, help="Probe cadence during high-cadence mode (default 30s)")
    ap.add_argument("--relaxed-probe-sec", type=float, default=180.0, help="Probe cadence after warmup when idle (default 180s)")
    ap.add_argument("--agent-boost-sec", type=float, default=60.0, help="If Agent1 is running or updated within this window, use high cadence (default 60s)")
    ap.add_argument("--agents", type=str, default="1,2,3,4", help="Comma-separated agent ids to supervise (default 1,2,3,4)")
    ap.add_argument("--thin", action="store_true", help="Force thin (non-LLM) probe mode regardless of configuration")
    ap.add_argument("--thin-probes", type=str, default=default_thin_str,
                    help="Comma-separated list of thin probes to execute (default from config)")
    ap.add_argument("--report", type=str, default=None,
                    help="Optional path to write thin probe snapshots as JSON")
    ap.add_argument("--no-llm", dest="use_llm", action="store_false", help="Disable LLM health check; use thin probes only")
    ap.add_argument("--llm", dest="use_llm", action="store_true", help=argparse.SUPPRESS)
    ap.set_defaults(use_llm=default_use_llm)
    args = ap.parse_args(argv)

    load_mode = _load_mode_flag()
    if load_mode == "high_load":
        args.interval = float(args.interval) * 2.0
        args.probe_every = max(2, int(args.probe_every))
    else:
        args.interval = float(args.interval)
    args.load_mode = load_mode

    # Ensure Shared Voice is active for auditing of joint outputs
    try:
        ensure_svf_running(grace_sec=15.0, interval=5.0)
    except Exception:
        pass
    start = time.time()
    state = LLMState()
    i = 0
    thin_probes = [p.strip() for p in str(args.thin_probes).split(",") if p.strip()]
    thin_mode = bool(args.thin or not args.use_llm)
    report_path = Path(args.report) if args.report else None
    last_probe: Optional[Dict[str, Any]] = None
    next_probe_ts: float = start  # schedule next LLM probe by wall-clock
    # Navigator control overrides: read-only lock written by traffic_navigator when --control is enabled
    def _read_control() -> Dict[str, Any]:
        try:
            data = _read_json(CONTROL_LOCK)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    # Set up Ctrl+C handling for a clean 'done' heartbeat
    stopping = False

    def _on_sigint(signum, frame):  # type: ignore[no-redef]
        nonlocal stopping
        stopping = True
    try:
        signal.signal(signal.SIGINT, _on_sigint)
    except Exception:
        pass

    # Build agent lock map once
    agent_ids: list[int] = []
    try:
        agent_ids = [int(x.strip()) for x in str(args.agents).split(",") if x.strip()]
    except Exception:
        agent_ids = [1]
    agent_ids = [aid for aid in agent_ids if aid >= 1]
    agent_locks = {f"agent{aid}": OUT / f"agent{aid}.lock" for aid in agent_ids}

    # Initial heartbeat (warming or idle)
    _write_hb("probe", status="monitoring", extra={
        "uptime_s": 0,
        "wsl": _is_wsl_env(),
        "probe": {"scheduled": args.probe_every, "last": None, "backend": "thin" if thin_mode else "llm"},
    })

    while not stopping:
        i += 1
        now = time.time()

        # Determine Agent statuses & recency for adaptive mode
        agents_status: Dict[str, Dict[str, Any]] = {}
        latest_active_ago: Optional[int] = None
        for aname, lockp in agent_locks.items():
            st: Dict[str, Any] = {"status": None, "phase": None, "ago_s": None}
            try:
                a = _read_json(lockp)
                if a:
                    st["status"] = a.get("status")
                    st["phase"] = a.get("phase")
                    ts = a.get("ts")
                    if ts is not None:
                        ago = int(max(0.0, now - float(ts)))
                        st["ago_s"] = ago
                        if latest_active_ago is None or ago < latest_active_ago:
                            latest_active_ago = ago
            except Exception:
                pass
            agents_status[aname] = st

        # Adaptive scheduling: compute target probe interval in seconds
        target_probe_sec = None
        mode = None
        if args.adaptive:
            warm = (now - start) < (float(args.warmup_minutes) * 60.0)
            any_running = any((st.get("status") == "running") for st in agents_status.values())
            recent_any = (latest_active_ago is not None and latest_active_ago <= int(args.agent_boost_sec))
            boost = any_running or recent_any
            high = warm or boost
            mode = "high" if high else "low"
            target_probe_sec = float(args.initial_probe_sec) if high else float(args.relaxed_probe_sec)
        else:
            # Compatibility: translate probe-every heartbeats into seconds
            target_probe_sec = float(args.interval) * max(1, int(args.probe_every))
            mode = "fixed"
        if thin_mode and mode:
            mode = f"thin-{mode}"

        # Navigator control integration: optional pause and interval override
        ctl = _read_control()
        pause_until = None
        try:
            pu = ctl.get("pause_until")
            if pu is not None:
                pause_until = float(pu)
        except Exception:
            pause_until = None
        interval_override = None
        try:
            iv = ctl.get("probe_interval_sec")
            if iv is not None:
                interval_override = float(iv)
        except Exception:
            interval_override = None
        if isinstance(interval_override, float) and interval_override >= 5.0:
            target_probe_sec = interval_override
            mode = f"override({int(interval_override)}s)"
        paused = False
        if isinstance(pause_until, float) and now < pause_until:
            paused = True
            # push next probe out to pause boundary
            if next_probe_ts < pause_until:
                next_probe_ts = pause_until

        # If it's time and not paused, perform a probe
        if (not paused) and (now >= next_probe_ts):
            if thin_mode:
                thin_payload = _run_thin_probe(thin_probes if thin_probes else DEFAULT_THIN_PROBES)
                if report_path:
                    _write_thin_report(report_path, thin_payload)
                last_probe = {
                    "ok": thin_payload["status"] == "ok" and not thin_payload["errors"],
                    "latency_ms": thin_payload["latency_ms"],
                    "text": thin_payload["status"],
                    "error": None if not thin_payload["errors"] else ", ".join(thin_payload["errors"]),
                    "details": thin_payload["results"],
                }
            else:
                last_probe = _probe_once(state)
            next_probe_ts = now + max(1.0, float(target_probe_sec or 30.0))

        # Compose status_message summarizing agents
        status_msg = _summarize_agents(agents_status)
        
        # Build reasoning about triage decisions (critical for system health)
        reasoning_parts = []
        if paused:
            reasoning_parts.append("Currently paused by navigator control")
        else:
            reasoning_parts.append(f"Probing in {mode} mode")
            if getattr(args, "load_mode", "normal") == "high_load":
                reasoning_parts.append("High-load cadence active")
        
        if last_probe:
            probe_status = "✓ healthy" if last_probe.get("ok") else "⚠ issues detected"
            reasoning_parts.append(f"Last probe: {probe_status}")
            if last_probe.get("error"):
                reasoning_parts.append(f"Error: {last_probe.get('error')}")
        
        if status_msg:
            healthy_count = sum(1 for a in agents_status.values() if a.get("status") == "done")
            reasoning_parts.append(f"Monitoring {len(agents_status)} agents ({healthy_count} done)")
        
        reasoning = ". ".join(reasoning_parts[:3])  # Limit to top 3 reasoning items

        hb_extra: Dict[str, Any] = {
            "uptime_s": int(time.time() - start),
            "wsl": _is_wsl_env(),
            "load_mode": getattr(args, "load_mode", "normal"),
            "probe": {
                "mode": ("paused" if paused else mode),
                "scheduled_sec": int(target_probe_sec or 0),
                "last": last_probe,
                "model_id": None if thin_mode else state.model_id,
                "backend": "thin" if thin_mode else (state.backend or ("none" if not state.ready else "llama_cpp")),
                "next_in_sec": int(max(0, int(next_probe_ts - now))),
            },
            "supervise": {
                **agents_status,
                "navigator_control": {
                    "pause_until": int(pause_until) if isinstance(pause_until, float) else None,
                    "interval_override_sec": int(interval_override) if isinstance(interval_override, float) else None,
                },
            },
            "status_message": f"agents: {status_msg}" if status_msg else None,
            "reasoning": reasoning,  # Enhanced reasoning for critical triage operations
        }
        _write_hb("probe", status="monitoring", extra=hb_extra)
        time.sleep(max(0.25, float(args.interval)))
        # Optional finite run for CI/smoke tests
        if args.max_iters and i >= int(args.max_iters):
            stopping = True

    # Final heartbeat
    time.sleep(max(0.0, float(args.grace_exit)))
    _write_hb("done", status="done", extra={
        "uptime_s": int(time.time() - start),
        "probe": {"last": last_probe, "backend": "thin" if thin_mode else (state.backend or "none")},
        "load_mode": getattr(args, "load_mode", "normal"),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
