"""
Assistance intake (reflection-only). Captures human intent into an envelope and audit log.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

AUDIT_PATH = Path("logs/governance/assist_requests.jsonl")
OUT_DIR = Path("outgoing/Architect")


def now_iso() -> str:
    from datetime import datetime, timezone

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.write("\n")


def prompt_assistance(boot_id: str) -> Dict[str, Any]:
    print("Assistance intake: What would you like assistance with?")
    intent = input("Intent: ").strip()
    ts = now_iso()
    ts_filename = ts.replace(":", "-")
    envelope = {
        "schema": "assist_request_v1",
        "created_at": ts,
        "boot_id": boot_id,
        "safe_mode": True,
        "deny_all": True,
        "user_intent_text": intent,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"assist_request_{ts_filename}.json"
    out_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    append_jsonl(
        AUDIT_PATH,
        {
            "timestamp": ts,
            "event": "assist_request",
            "boot_id": boot_id,
            "envelope_path": str(out_path),
        },
    )
    return {"intent": intent, "envelope_path": str(out_path)}
