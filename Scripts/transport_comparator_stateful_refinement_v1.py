from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from calyx.kernel.paths import resolve_repo_root
from calyx.kernel.transport_comparator import evaluate_transport_cycles, write_refinement_receipt


def main() -> int:
    repo_root = resolve_repo_root()
    cycles = evaluate_transport_cycles(repo_root, required_count=20)
    receipt_path = write_refinement_receipt(repo_root, cycles)
    newest = cycles[0] if cycles else None
    out = {
        "schema": "audit.transport_comparator_stateful_refinement_runner.v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "observe_mode": True,
        "policy_mutation": False,
        "receipt_path": str(receipt_path),
        "cycle_count": len(cycles),
        "latest_cycle_flags": (
            {
                "cycle_ref": newest.cycle_ref,
                "boot_session_id": newest.boot_session_id,
                "unexpected_new_remote": newest.unexpected_new_remote,
                "unexpected_new_emitter_authority": newest.unexpected_new_emitter_authority,
                "new_listener_unexpected": newest.new_listener_unexpected,
                "channel_widening": newest.channel_widening,
            }
            if newest
            else {}
        ),
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
