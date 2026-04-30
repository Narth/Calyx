"""
WO_CALYX_SIGN_INGRESS_AUTH_V4 — Nonce ledger for replay protection.
Location: runtime/receipts/security/nonce_ledger.jsonl
Pruning: last 24h or 10000 entries.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

NONCE_LEDGER_MAX_AGE_HOURS = 24
NONCE_LEDGER_MAX_ENTRIES = 10000


def _resolve_nonce_ledger_path() -> Path:
    env_root = os.environ.get("CALYX_REPO_ROOT")
    root = Path(env_root).resolve() if env_root else Path(__file__).resolve().parents[2]
    return root / "runtime" / "receipts" / "security" / "nonce_ledger.jsonl"


def _prune_if_needed(path: Path) -> None:
    """Keep last N entries and entries within 24h."""
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        if len(lines) <= NONCE_LEDGER_MAX_ENTRIES:
            return
        cutoff = datetime.now(timezone.utc) - timedelta(hours=NONCE_LEDGER_MAX_AGE_HOURS)
        kept: list[str] = []
        for line in reversed(lines[-NONCE_LEDGER_MAX_ENTRIES:]):
            try:
                rec = json.loads(line)
                ts_str = rec.get("ts", "")
                if ts_str:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if ts >= cutoff:
                        kept.append(line)
            except Exception:
                pass
        path.write_text("\n".join(reversed(kept)) + ("\n" if kept else ""), encoding="utf-8")
    except Exception:
        pass


def nonce_seen(nonce: str, key_id: str) -> bool:
    """Check if nonce was already used. If not, record it. Returns True if replay."""
    path = _resolve_nonce_ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _prune_if_needed(path)
    ts = datetime.now(timezone.utc).isoformat()
    entry = {"nonce": nonce, "key_id": key_id, "ts": ts}
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    try:
        content = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        for ln in content.strip().splitlines():
            if not ln:
                continue
            try:
                rec = json.loads(ln)
                if rec.get("nonce") == nonce:
                    return True  # replay
            except Exception:
                pass
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    return False
