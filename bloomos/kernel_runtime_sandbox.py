"""
BloomOS Kernel Seed v0.1 - Safe Mode Runtime Sandbox

Layering:
- L2 spec: bloomos/kernel_seed_v0.1.md
- L1 code: this file, ONLY if the Architect promotes it in the Reality Map.

Default assumption:
- Experimental, not wired into any scheduler.
- Run manually by the Architect, or not at all.

Safety guarantees:
- Read-only access to a small set of Station artifacts.
- Append-only logging to logs/bloomos/kernel_seed_observations.jsonl.
- No network, no subprocess, no dispatch, no scheduling, no gating.
"""

import json
import time
import pathlib
from typing import Optional, Dict, Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

POLICY_PATH = REPO_ROOT / "calyx" / "core" / "policy.yaml"
REGISTRY_PATH = REPO_ROOT / "calyx" / "core" / "registry.jsonl"
BRIDGE_PULSE_PATH = REPO_ROOT / "metrics" / "bridge_pulse.csv"
AGENT_METRICS_PATH = REPO_ROOT / "logs" / "agent_metrics.csv"
GATE_PATH = REPO_ROOT / "bloomos" / "bloom_gate_v0.1.json"

OUTPUT_PATH = REPO_ROOT / "logs" / "bloomos" / "kernel_seed_observations.jsonl"


def safe_stat(path: pathlib.Path) -> Optional[Dict[str, Any]]:
    """
    Return basic file metadata if it exists; otherwise None.
    No file contents are read here, only metadata.
    """
    if not path.exists():
        return None
    try:
        stat = path.stat()
        return {
            "path": str(path),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
        }
    except OSError:
        return None


def read_gate_status(path: pathlib.Path) -> Optional[Dict[str, Any]]:
    """
    Read the bloom gate status as raw JSON.
    If missing or invalid, return None. No interpretation or enforcement.
    """
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
        return json.loads(text)
    except Exception:
        return None


def collect_snapshot() -> Dict[str, Any]:
    """
    Collect a single Safe Mode snapshot of select Station artifacts.
    This function MUST remain side-effect free except for the final append to OUTPUT_PATH.
    """
    now = time.time()

    snapshot: Dict[str, Any] = {
        "schema": "bloomos.kernel_seed.observation.v0.1",
        "timestamp": now,
        "note": "Read-only Safe Mode snapshot; no dispatch, no gating, no autonomy.",
        "files": {
            "policy": safe_stat(POLICY_PATH),
            "registry": safe_stat(REGISTRY_PATH),
            "bridge_pulse": safe_stat(BRIDGE_PULSE_PATH),
            "agent_metrics": safe_stat(AGENT_METRICS_PATH),
        },
        "bloom_gate": read_gate_status(GATE_PATH),
    }

    return snapshot


def append_observation(snapshot: Dict[str, Any]) -> None:
    """
    Append a single observation as one JSONL line.
    This is the ONLY write this module performs.
    """
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(snapshot, sort_keys=True)
    with OUTPUT_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> None:
    """
    Manual entrypoint for the Architect.
    """
    print("[kernel_seed] REPO_ROOT:", REPO_ROOT)
    print("[kernel_seed] GATE_PATH:", GATE_PATH, "exists:", GATE_PATH.exists())

    snapshot = collect_snapshot()
    append_observation(snapshot)


if __name__ == "__main__":
    main()

