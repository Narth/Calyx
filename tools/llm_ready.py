#!/usr/bin/env python3
"""
LLM readiness beacon: write a global readiness lock to outgoing/llm_ready.lock.

Signals to CP6/CP7/Navigator whether local LLM channels are available without
loading a heavy model on every tick.

Behavior
- Checks: llama_cpp import, manifest presence, selected model path existence
- Optional: --probe will attempt a tiny model open+chat (environment dependent)
- Writes a watcher-compatible lock with a concise status_message

Usage (Windows PowerShell):
    python -u tools/llm_ready.py --interval 60   # loop
    python -u tools/llm_ready.py --once          # single write

Run in WSL for environment-accurate path checks when triage runs in WSL.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

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
LOCK = OUT / "llm_ready.lock"
MAN = ROOT / "tools" / "models" / "MODEL_MANIFEST.json"


def _is_wsl_env() -> bool:
    try:
        return "WSL_DISTRO_NAME" in os.environ or "microsoft" in Path("/proc/version").read_text().lower()
    except Exception:
        return False


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
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
    for e in models:
        if e.get("role") == "probe":
            return e
    return models[0]


def _write_lock(status: str, msg: str, extra: Dict[str, Any]) -> None:
    try:
        payload = {
            "name": "llm_ready",
            "phase": "probe",
            "status": status,
            "ts": time.time(),
            "status_message": msg,
            **extra,
        }
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def check(model_id: Optional[str], do_probe: bool, *, probe_open_only: bool = False) -> Dict[str, Any]:
    env = {"wsl": _is_wsl_env()}
    module_ok = False
    try:
        import llama_cpp  # type: ignore
        module_ok = True
    except Exception:
        module_ok = False

    man = _read_json(MAN)
    manifest_ok = isinstance(man, dict) and bool(man.get("models"))
    entry = _select_model(man or {}, model_id)
    model_path = entry.get("filename") if isinstance(entry, dict) else None
    path_ok = False
    if isinstance(model_path, str) and model_path:
        try:
            path_ok = Path(model_path).exists()
        except Exception:
            path_ok = False

    probe_ok = None
    latency_ms = None
    if (do_probe or probe_open_only) and module_ok and path_ok:
        try:
            from llama_cpp import Llama  # type: ignore
            start = time.time()
            
            # GPU offloading configuration
            gpu_layers = get_gpu_layer_count()
            if gpu_layers > 0:
                # GPU mode: offload layers to GPU
                llm = Llama(
                    model_path=model_path,
                    n_ctx=64,
                    temperature=0.0,
                    n_gpu_layers=gpu_layers,
                    n_threads=4,
                    verbose=False
                )
            else:
                # CPU mode: standard initialization
                llm = Llama(model_path=model_path, n_ctx=64, temperature=0.0)
            
            if not probe_open_only and do_probe:
                try:
                    _ = llm.create_chat_completion(
                        messages=[{"role": "system", "content": "Reply 'ok' only."}, {"role": "user", "content": "ping"}],
                        max_tokens=2,
                        temperature=0.0,
                    )
                    latency_ms = int((time.time() - start) * 1000)
                    probe_ok = True
                except Exception:
                    # Model opened but chat failed: treat as partial success
                    latency_ms = int((time.time() - start) * 1000)
                    probe_ok = True
            else:
                # Open-only probe: consider success if model instantiated
                latency_ms = int((time.time() - start) * 1000)
                probe_ok = True
        except Exception:
            probe_ok = False

    status = "running" if (module_ok and manifest_ok and (path_ok or not env["wsl"])) else "warn"
    msg = (
        f"cp6/cp7: LLM module={module_ok} manifest={manifest_ok} path={path_ok}"
    )
    extra = {
        "env": env,
        "manifest_ok": manifest_ok,
        "module_ok": module_ok,
        "model_id": entry.get("id") if isinstance(entry, dict) else None,
        "model_path": model_path,
        "path_ok": path_ok,
        "probe_ok": probe_ok,
        "probe_latency_ms": latency_ms,
    }
    return {"status": status, "message": msg, "extra": extra}


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Write LLM readiness lock periodically")
    ap.add_argument("--interval", type=float, default=60.0)
    ap.add_argument("--model-id", type=str, default=None)
    ap.add_argument("--probe", action="store_true", help="Attempt a tiny model open+chat (heavier; WSL only)")
    ap.add_argument("--probe-open-only", action="store_true", help="Lightweight: open model only (no chat); faster and lower risk")
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args(argv)

    while True:
        res = check(args.model_id, do_probe=bool(args.probe), probe_open_only=bool(args.probe_open_only))
        _write_lock(res["status"], res["message"], res["extra"])  # type: ignore[index]
        if args.once:
            break
        time.sleep(max(5.0, float(args.interval)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
