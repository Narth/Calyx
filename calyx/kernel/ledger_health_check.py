"""
Ledger health check — validates ledger writability and staleness.
WO_STATION_EVENT_LEDGER_V1 optional stretch.
If ledger stops, emit ledger.stall.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def check_ledger_health(
    max_stale_seconds: float = 60.0,
    repo_root: Path | None = None,
) -> dict:
    """
    Validate: file writable, directory exists, last write < max_stale_seconds during heartbeat.
    Returns {ok: bool, reason: str, last_write_ts: float|None, path: str}.
    """
    try:
        from .paths import resolve_repo_root, resolve_ledger_dir
        root = repo_root or resolve_repo_root()
        ledger_dir = resolve_ledger_dir(root)
    except ImportError:
        ledger_dir = Path.cwd() / "runtime" / "ledger"

    result = {"ok": True, "reason": "", "last_write_ts": None, "path": ""}

    if not ledger_dir.exists():
        ledger_dir.mkdir(parents=True, exist_ok=True)

    path = ledger_dir / f"station_events__{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
    result["path"] = str(path)

    # Check writable
    try:
        with open(path, "a", encoding="utf-8") as f:
            pass
    except OSError as e:
        result["ok"] = False
        result["reason"] = f"not_writable:{e}"
        return result

    # Check last write age
    if path.exists():
        mtime = path.stat().st_mtime
        result["last_write_ts"] = mtime
        age = datetime.now(timezone.utc).timestamp() - mtime
        if age > max_stale_seconds:
            result["ok"] = False
            result["reason"] = f"stale:{age:.0f}s"
            try:
                from .event_ledger import emit
                emit("WARN", "kernel", "ledger.stall", f"Ledger stale {age:.0f}s", data={"path": str(path), "age_sec": age})
            except Exception:
                pass

    return result
