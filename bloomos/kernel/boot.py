"""
BloomOS kernel boot (Safe Mode, deny-all).

Validates minimal invariants and appends a boot record.
No schedulers, no external access, no policy mutation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

BOOT_LOG = Path("logs/bloomos/kernel_boot.jsonl")
CONFIG_PATH = Path("config/demo_safe_boot_contract_v1.md")  # optional; hash if present


def now_iso() -> str:
    from datetime import datetime, timezone

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def sha256_path(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.write("\n")


@dataclass
class KernelBootResult:
    boot_id: str
    safe_mode: bool
    deny_all: bool
    config_hash: str | None
    naming_rites_required: bool
    timestamp: str


def boot_kernel(profile: str = "demo_safe") -> KernelBootResult:
    ts = now_iso()
    boot_id = f"boot-{ts}"
    safe_mode = True
    deny_all = True
    config_hash = sha256_path(CONFIG_PATH)
    naming_rites_required = not Path("config/naming_rites_v1.json").exists()

    record = {
        "boot_id": boot_id,
        "timestamp": ts,
        "profile": profile,
        "safe_mode": safe_mode,
        "deny_all": deny_all,
        "config_hash": config_hash,
        "naming_rites_required": naming_rites_required,
    }
    append_jsonl(BOOT_LOG, record)

    return KernelBootResult(
        boot_id=boot_id,
        safe_mode=safe_mode,
        deny_all=deny_all,
        config_hash=config_hash,
        naming_rites_required=naming_rites_required,
        timestamp=ts,
    )
