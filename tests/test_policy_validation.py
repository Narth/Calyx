"""Tests for policy validators: tripwire, competitor_clause. Deny-by-default."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from policy.validator import check_tripwire, validate_competitor_clause, validate_tripwire


def test_tripwire_returns_allow_deny_reason():
    """Tripwire check returns explicit allow/deny + reason string."""
    decision, reason = check_tripwire(repo_root=REPO_ROOT)
    assert decision in ("allow", "warn", "deny")
    assert isinstance(reason, str)
    assert len(reason) > 0


def test_tripwire_rejects_missing_keys():
    """Tripwire validator rejects missing required keys."""
    with tempfile.TemporaryDirectory() as tmp:
        bad_path = Path(tmp) / "tripwire_levels.yaml"
        bad_path.write_text("tripwire_levels:\n  current_level: 1\n", encoding="utf-8")
        decision, reason = validate_tripwire(path=bad_path)
        assert decision == "deny"
        assert "missing" in reason.lower() or "deny_by_default" in reason.lower()


def test_competitor_clause_rejects_missing_expiry():
    """Competitor clause validator rejects missing expiry."""
    with tempfile.TemporaryDirectory() as tmp:
        bad_path = Path(tmp) / "competitor_clause.yaml"
        bad_path.write_text(
            "competitor_clause:\n  max_relaxation_cap: 30\n  relaxation_applied: false\n",
            encoding="utf-8",
        )
        ok, reason = validate_competitor_clause(path=bad_path)
        assert not ok
        assert "expiry" in reason.lower() or "missing" in reason.lower()


def test_competitor_clause_rejects_missing_max_relaxation_cap():
    """Competitor clause validator rejects missing max_relaxation_cap."""
    with tempfile.TemporaryDirectory() as tmp:
        bad_path = Path(tmp) / "competitor_clause.yaml"
        bad_path.write_text(
            "competitor_clause:\n  expiry: '2026-05-25'\n  relaxation_applied: false\n",
            encoding="utf-8",
        )
        ok, reason = validate_competitor_clause(path=bad_path)
        assert not ok
        assert "max_relaxation_cap" in reason.lower() or "missing" in reason.lower()


def test_competitor_clause_relaxation_requires_receipt_flag():
    """If relaxation occurred but receipt has no relaxation_applied=true -> deny."""
    with tempfile.TemporaryDirectory() as tmp:
        good_path = Path(tmp) / "competitor_clause.yaml"
        good_path.write_text(
            "competitor_clause:\n  expiry: '2026-05-25'\n  max_relaxation_cap: 30\n  relaxation_applied: false\n",
            encoding="utf-8",
        )
        ok, reason = validate_competitor_clause(
            path=good_path,
            relaxation_occurred=True,
            receipt_has_relaxation_applied=False,
        )
        assert not ok
        assert "relaxation" in reason.lower()


def test_competitor_clause_accepts_valid_with_relaxation_receipt():
    """Valid clause + relaxation_applied in receipt -> ok."""
    with tempfile.TemporaryDirectory() as tmp:
        good_path = Path(tmp) / "competitor_clause.yaml"
        good_path.write_text(
            "competitor_clause:\n  expiry: '2026-05-25'\n  max_relaxation_cap: 30\n  relaxation_applied: false\n",
            encoding="utf-8",
        )
        ok, reason = validate_competitor_clause(
            path=good_path,
            relaxation_occurred=True,
            receipt_has_relaxation_applied=True,
        )
        assert ok
