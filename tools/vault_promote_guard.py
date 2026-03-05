"""
WO_CHRONICLE_VAULT_QUARANTINE_V1

Promotion guard for raw -> derived vault content.
- Validates ARCHIVE_CONSENT receipt
- Verifies sha256 against raw file
- Logs to ledger
- Dry-run by default
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
from typing import Any, Dict


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _utc_iso(ts: float) -> str:
    return dt.datetime.utcfromtimestamp(ts).replace(microsecond=0).isoformat() + "Z"


def _load_receipt(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _validate_receipt(r: Dict[str, Any]) -> None:
    if r.get("receipt_type") != "ARCHIVE_CONSENT":
        raise SystemExit("Invalid receipt_type; expected ARCHIVE_CONSENT")
    for key in ("ts", "actor", "source", "allowed_actions"):
        if key not in r:
            raise SystemExit(f"Missing required field: {key}")
    source = r.get("source", {})
    if "vault_path" not in source or "sha256" not in source:
        raise SystemExit("Receipt.source missing vault_path or sha256")
    allowed = r.get("allowed_actions", [])
    if "raw_to_derived" not in allowed:
        raise SystemExit("Receipt does not allow raw_to_derived")


def _append_ledger(ledger_path: str, line: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--vault_root", required=True)
    p.add_argument("--month", required=True)
    p.add_argument("--receipt", required=True)
    p.add_argument("--perform", action="store_true")
    args = p.parse_args()

    receipt = _load_receipt(args.receipt)
    _validate_receipt(receipt)

    source = receipt["source"]
    raw_path = os.path.abspath(source["vault_path"])
    expected_root = os.path.abspath(
        os.path.join(args.vault_root, "chatgpt_exports", args.month, "raw")
    )

    if not raw_path.startswith(expected_root + os.sep):
        raise SystemExit("Receipt vault_path is not under the expected raw/ folder")
    if not os.path.isfile(raw_path):
        raise SystemExit("Raw file not found")

    actual_sha = _sha256(raw_path)
    if actual_sha != source["sha256"]:
        raise SystemExit("sha256 mismatch between receipt and raw file")

    derived_dir = os.path.join(
        args.vault_root, "chatgpt_exports", args.month, "derived"
    )
    os.makedirs(derived_dir, exist_ok=True)
    derived_path = os.path.join(derived_dir, os.path.basename(raw_path))

    if args.perform:
        shutil.copy2(raw_path, derived_path)

    ledger_path = os.path.join(
        args.vault_root, "chatgpt_exports", args.month, "ledger", "ledger.ndjson"
    )
    _append_ledger(
        ledger_path,
        {
            "ts": _utc_iso(dt.datetime.utcnow().timestamp()),
            "actor": receipt.get("actor", "unknown"),
            "action": "promote",
            "file": raw_path,
            "sha256": actual_sha,
            "note": receipt.get("note", "raw_to_derived"),
        },
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
