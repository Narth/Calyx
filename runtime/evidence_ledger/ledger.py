"""
Evidence ledger: append-only, hash-chained, schema-validated.
Deny-by-default on malformed. Stdlib only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

LEDGER_FILENAME = "ledger.jsonl"
SCHEMA_REQUIRED = frozenset({"ts_utc", "event_name", "severity", "prev_hash", "record_hash"})
APPEND_REQUIRED = frozenset({"ts_utc", "event_name", "severity"})
SEVERITY_VALUES = frozenset({"low", "medium", "high", "critical"})
HASH_FIELDS = frozenset({"ts_utc", "event_name", "severity", "wo_id", "context_tag", "payload_hash", "payload_summary", "prev_hash"})


def _canonical_dumps(obj: dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _compute_record_hash(record: dict[str, Any]) -> str:
    """Compute SHA256 of canonical JSON (all fields except record_hash)."""
    out = {k: v for k, v in record.items() if k != "record_hash"}
    return hashlib.sha256(_canonical_dumps(out).encode("utf-8")).hexdigest()


def _validate_schema(record: dict[str, Any]) -> tuple[bool, str]:
    """Validate record. Returns (ok, reason). Deny-by-default."""
    if not isinstance(record, dict):
        return False, "record must be dict"
    missing = SCHEMA_REQUIRED - set(record)
    if missing:
        return False, f"missing required fields: {missing}"
    if record.get("severity") not in SEVERITY_VALUES:
        return False, f"invalid severity: {record.get('severity')}"
    if not isinstance(record.get("prev_hash"), (str, type(None))):
        return False, "prev_hash must be string or null"
    if not isinstance(record.get("record_hash"), str) or len(record["record_hash"]) != 64:
        return False, "record_hash must be 64-char hex"
    return True, ""


def get_ledger_path(repo_root: Path | None = None) -> Path:
    """Ledger path: runtime/evidence_ledger/ledger.jsonl."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "runtime" / "evidence_ledger" / LEDGER_FILENAME


def _validate_append_record(record: dict[str, Any]) -> tuple[bool, str]:
    """Validate record for append (caller does not pass prev_hash/record_hash)."""
    if not isinstance(record, dict):
        return False, "record must be dict"
    missing = APPEND_REQUIRED - set(record)
    if missing:
        return False, f"missing required fields: {missing}"
    if record.get("severity") not in SEVERITY_VALUES:
        return False, f"invalid severity: {record.get('severity')}"
    return True, ""


def append(record: dict[str, Any], repo_root: Path | None = None) -> Path:
    """
    Append a record. Validates schema, computes record_hash, sets prev_hash.
    Returns path. Raises ValueError on malformed.
    """
    ledger_path = get_ledger_path(repo_root)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    ok, reason = _validate_append_record(record)
    if not ok:
        raise ValueError(f"deny_by_default: {reason}")

    last_hash = _get_last_hash(ledger_path)
    record["prev_hash"] = last_hash
    record["record_hash"] = _compute_record_hash(record)

    line = _canonical_dumps(record) + "\n"
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(line)
    return ledger_path


def _get_last_hash(ledger_path: Path) -> str | None:
    if not ledger_path.exists():
        return None
    last_hash = None
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                last_hash = rec.get("record_hash")
            except json.JSONDecodeError:
                pass
    return last_hash


def verify_chain(repo_root: Path | None = None) -> tuple[bool, str]:
    """
    Verify ledger chain. Returns (ok, reason).
    Fails on schema violation, hash mismatch, tamper, parse error.
    """
    ledger_path = get_ledger_path(repo_root)
    if not ledger_path.exists():
        return True, "empty ledger"

    prev_hash = None
    with open(ledger_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                return False, f"record {i+1}: parse error: {e}"

            ok, reason = _validate_schema(rec)
            if not ok:
                return False, f"record {i+1}: {reason}"

            if rec.get("prev_hash") != prev_hash:
                return False, f"record {i+1}: prev_hash chain broken"

            computed = _compute_record_hash(rec)
            if rec.get("record_hash") != computed:
                return False, f"record {i+1}: record_hash tamper detected"

            prev_hash = rec["record_hash"]

    return True, ""


def read_ledger(repo_root: Path | None = None) -> list[dict[str, Any]]:
    """Read all records (for tests)."""
    ledger_path = get_ledger_path(repo_root)
    if not ledger_path.exists():
        return []
    out = []
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out
