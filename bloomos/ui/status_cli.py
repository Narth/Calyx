"""
BloomOS read-only status CLI.

Safe Mode: ON. Prints a snapshot only. No interactivity beyond read-only output.
"""

from __future__ import annotations

import json

from bloomos.identity.registry import get_identity
from bloomos.policy.binding import get_policy_snapshot
from bloomos.telemetry.collectors import collect as collect_telemetry
from bloomos.lifecycle.controller import get_state


def build_status() -> dict:
    return {
        "safe_mode": True,
        "identity": get_identity(),
        "policy": get_policy_snapshot(),
        "telemetry": collect_telemetry(),
        "lifecycle_state": get_state(),
    }


def main() -> None:
    status = build_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
