"""Tests for evidence ledger: append-only, hash-chained, schema-validated."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

# Ensure repo root on path for runtime.evidence_ledger
import sys
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.evidence_ledger import append, get_ledger_path, read_ledger, verify_chain


def test_append_and_verify_chain():
    """verify_chain passes after appends."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        r1 = append({"ts_utc": "2026-02-25T12:00:00Z", "event_name": "wo_start", "severity": "low"}, repo_root=root)
        r2 = append({"ts_utc": "2026-02-25T12:01:00Z", "event_name": "wo_end", "severity": "low"}, repo_root=root)
        assert r1 == r2
        ok, reason = verify_chain(repo_root=root)
        assert ok, reason
        records = read_ledger(repo_root=root)
        assert len(records) == 2
        assert records[0]["prev_hash"] is None
        assert records[1]["prev_hash"] == records[0]["record_hash"]


def test_verify_chain_fails_on_tamper():
    """verify_chain fails when ledger is tampered."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        append({"ts_utc": "2026-02-25T12:00:00Z", "event_name": "wo_start", "severity": "low"}, repo_root=root)
        ledger_path = get_ledger_path(root)
        lines = ledger_path.read_text(encoding="utf-8").strip().split("\n")
        rec = json.loads(lines[0])
        rec["event_name"] = "tampered"
        lines[0] = json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        ok, reason = verify_chain(repo_root=root)
        assert not ok
        assert "tamper" in reason.lower() or "record_hash" in reason.lower()


def test_append_rejects_malformed():
    """Malformed entry => deny-by-default (raises ValueError)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        with pytest.raises(ValueError, match="deny_by_default"):
            append({"ts_utc": "2026-02-25T12:00:00Z"}, repo_root=root)
        with pytest.raises(ValueError, match="deny_by_default"):
            append({"event_name": "x", "severity": "low"}, repo_root=root)
        with pytest.raises(ValueError, match="deny_by_default"):
            append({"ts_utc": "2026-02-25T12:00:00Z", "event_name": "x", "severity": "invalid"}, repo_root=root)


def test_empty_ledger_verify_passes():
    """Empty ledger verifies as ok."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ok, reason = verify_chain(repo_root=root)
        assert ok
        assert "empty" in reason.lower()
