"""Manifest Probe: Continuously validates the model manifest and reports status via a heartbeat.

- Writes outgoing/manifest.lock every --interval seconds
- Checks tools/models/MODEL_MANIFEST.json presence and basic structure
- Optionally verifies a specific model id is present
- Optional quick-run with --max-iters for smoke tests

The Calyx Agent Watcher auto-discovers *.lock files, so this will appear as a new row named 'manifest'.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOCK = OUT / "manifest.lock"
PROBE_VERSION = "0.1.0"


def _write_hb(phase: str, status: str = "running", extra: Optional[Dict[str, Any]] = None) -> None:
    try:
        payload: Dict[str, Any] = {
            "name": "manifest",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": time.time(),
            "probe_version": PROBE_VERSION,
        }
        if extra:
            payload.update(extra)
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass


def _load_manifest() -> Optional[Dict[str, Any]]:
    try:
        p = ROOT / "tools" / "models" / "MODEL_MANIFEST.json"
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _check_manifest(model_id: Optional[str] = None) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "ok": False,
        "error": None,
        "model_id": model_id,
        "models": 0,
    }
    man = _load_manifest()
    if not man:
        info["error"] = "manifest_missing"
        return info
    models = man.get("models")
    if not isinstance(models, list) or not models:
        info["error"] = "models_empty"
        return info
    info["models"] = len(models)
    if model_id:
        found = any((m.get("id") == model_id) for m in models if isinstance(m, dict))
        if not found:
            info["error"] = "model_not_found"
            return info
    info["ok"] = True
    return info


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Validate the model manifest and emit watcher-compatible heartbeats")
    ap.add_argument("--interval", type=float, default=5.0, help="Heartbeat interval in seconds (default 5.0)")
    ap.add_argument("--max-iters", type=int, default=0, help="Stop after N iterations (0 = run forever)")
    ap.add_argument("--model-id", type=str, default=None, help="Optional: ensure a specific model id exists in the manifest")
    args = ap.parse_args(argv)

    stopping = False

    def _on_sigint(signum, frame):  # type: ignore[no-redef]
        nonlocal stopping
        stopping = True
    try:
        signal.signal(signal.SIGINT, _on_sigint)
    except Exception:
        pass

    i = 0
    initial_check = _check_manifest(args.model_id)
    reasoning = f"Checking manifest for models (model_id={args.model_id or 'default'})"
    _write_hb("probe", status="monitoring", extra={"check": initial_check, "reasoning": reasoning})

    while not stopping:
        i += 1
        result = _check_manifest(args.model_id)
        
        # Build reasoning about manifest state
        model_count = len(result.get("models", []))
        if model_count > 0:
            reasoning = f"Manifest check: {model_count} models available"
            if result.get("default"):
                reasoning += f", default={result.get('default').get('name', 'unknown')}"
        else:
            reasoning = "Manifest check: No models found in manifest"
        
        _write_hb("probe", status="monitoring", extra={"check": result, "reasoning": reasoning})
        time.sleep(max(0.25, float(args.interval)))
        if args.max_iters and i >= int(args.max_iters):
            stopping = True

    time.sleep(0.5)
    _write_hb("done", status="done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
