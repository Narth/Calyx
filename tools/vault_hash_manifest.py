"""
WO_CHRONICLE_VAULT_QUARANTINE_V1

Hash manifest builder for vault exports.
- Never prints file contents
- Paths only
- Idempotent manifest updates
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from typing import Dict, List


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _utc_iso(ts: float) -> str:
    return dt.datetime.utcfromtimestamp(ts).replace(microsecond=0).isoformat() + "Z"


def _load_manifest(manifest_path: str) -> List[dict]:
    if not os.path.exists(manifest_path):
        return []
    with open(manifest_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []
    return data if isinstance(data, list) else []


def _write_manifest(manifest_path: str, entries: List[dict]) -> None:
    entries_sorted = sorted(entries, key=lambda e: e.get("path", ""))
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(entries_sorted, f, indent=2)


def _append_ledger(ledger_path: str, lines: List[dict]) -> None:
    if not lines:
        return
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--vault_root", required=True)
    p.add_argument("--month", required=True)
    p.add_argument("--mode", required=True, choices=["raw", "derived"])
    args = p.parse_args()

    target_dir = os.path.join(
        args.vault_root, "chatgpt_exports", args.month, args.mode
    )
    ledger_dir = os.path.join(
        args.vault_root, "chatgpt_exports", args.month, "ledger"
    )
    manifest_path = os.path.join(ledger_dir, "manifest.json")
    ledger_path = os.path.join(ledger_dir, "ledger.ndjson")

    if not os.path.isdir(target_dir):
        raise SystemExit(f"Target directory not found: {target_dir}")

    existing = _load_manifest(manifest_path)
    index: Dict[str, dict] = {e.get("path", ""): e for e in existing if "path" in e}

    changed_entries: List[dict] = []
    ledger_lines: List[dict] = []

    for root, _, files in os.walk(target_dir):
        for name in files:
            path = os.path.abspath(os.path.join(root, name))
            try:
                stat = os.stat(path)
            except OSError:
                continue

            entry = {
                "path": path,
                "bytes": stat.st_size,
                "sha256": _sha256(path),
                "created_ts": _utc_iso(stat.st_ctime),
            }

            prev = index.get(path)
            if prev != entry:
                index[path] = entry
                changed_entries.append(entry)
                ledger_lines.append(
                    {
                        "ts": _utc_iso(dt.datetime.utcnow().timestamp()),
                        "actor": "vault_hash_manifest",
                        "action": "hash",
                        "file": path,
                        "sha256": entry["sha256"],
                        "note": f"mode={args.mode} month={args.month}",
                    }
                )

    _write_manifest(manifest_path, list(index.values()))
    _append_ledger(ledger_path, ledger_lines)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
