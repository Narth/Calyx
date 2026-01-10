"""Station Calyx Evidence Log"""
from __future__ import annotations
import hashlib, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

COMPONENT_ROLE = "evidence_store"
DEFAULT_EVIDENCE_PATH = Path(__file__).resolve().parents[1] / "data" / "evidence.jsonl"

def compute_sha256(payload_bytes: bytes) -> str:
    return hashlib.sha256(payload_bytes).hexdigest()

def generate_session_id() -> str:
    return str(uuid.uuid4())[:8]

def create_event(event_type: str, node_role: str, summary: str, payload: dict[str, Any], tags: Optional[list[str]] = None, session_id: Optional[str] = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    event = {"ts": now.isoformat(), "event_type": event_type, "node_role": node_role, "session_id": session_id or generate_session_id(), "summary": summary, "payload": payload, "tags": tags or []}
    event["_hash"] = compute_sha256(json.dumps(event, sort_keys=True).encode("utf-8"))
    return event

def append_event(event: dict[str, Any], evidence_path: Optional[Path] = None) -> None:
    path = evidence_path or DEFAULT_EVIDENCE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def load_recent_events(n: int = 100, evidence_path: Optional[Path] = None) -> list[dict[str, Any]]:
    path = evidence_path or DEFAULT_EVIDENCE_PATH
    if not path.exists(): return []
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try: events.append(json.loads(line))
                except: pass
    return events[-n:] if len(events) > n else events

def get_last_event_ts(evidence_path: Optional[Path] = None) -> Optional[str]:
    events = load_recent_events(1, evidence_path)
    return events[-1]["ts"] if events else None
