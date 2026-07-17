"""
Spine Validation & Risk Hardening — Simulation runner.
Runs adversarial and stress simulations; writes receipts and metrics.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# Repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = REPO_ROOT / "runtime"
RECEIPTS = RUNTIME / "receipts"
METRICS = RUNTIME / "metrics"


def _ensure_dirs():
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    METRICS.mkdir(parents=True, exist_ok=True)


def _receipt_path(name: str) -> Path:
    return RECEIPTS / name


def _metrics_path() -> Path:
    return METRICS / "spine_validation.json"


# --- Phase A: Mail security ---

def sim_mail_replay():
    """A2: Identical envelope submitted twice; second rejected."""
    from calyx.mail.router import deliver_to_cbo_ingest
    from calyx.mail.ingest_ledger import has_seen_envelope
    _ensure_dirs()
    runtime = RUNTIME / "spine_sim"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "cbo").mkdir(exist_ok=True)
    ledger = runtime / "cbo" / "ingest_replay_ledger.jsonl"
    if ledger.exists():
        ledger.unlink()
    envelope = {
        "envelope_id": "sim-replay-001",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "source": "discord",
        "author": "sim",
        "intent": "test",
        "task_type": "doc_update",
        "scope": {"paths": ["**"]},
        "constraints": {},
        "requires_human_approval": False,
        "approval_token": None,
        "evidence_requirements": {},
        "signature": None,
    }
    first = deliver_to_cbo_ingest(envelope, runtime)
    second = deliver_to_cbo_ingest(envelope, runtime)
    rej = (runtime / "receipts").glob("ingest_reject__*.jsonl")
    rej_list = list(rej)
    return {
        "first_delivery": first is not None,
        "second_delivery": second is None,
        "rejection_receipt_written": len(rej_list) >= 1,
        "replay_ledger_has_id": has_seen_envelope("sim-replay-001", runtime),
    }


def sim_bypass_work_outbox():
    """A3: Write directly to work_outbox; hub_runner must deny (no CBO mint)."""
    from calyx.execution.hub_runner import run_work_envelope, get_work_outbox
    _ensure_dirs()
    with tempfile.TemporaryDirectory(prefix="spine_sim_runtime_") as tmp:
        runtime_dir = Path(tmp)
        (runtime_dir / "cbo" / "intents").mkdir(parents=True, exist_ok=True)
        outbox = get_work_outbox(runtime_dir)
        outbox.mkdir(parents=True, exist_ok=True)
        fake = {
            "envelope_id": "bypass-inject-001",
            "intent_id": "nonexistent-intent-999",
            "task_type": "repo_readonly_review",
            "scope": {"paths": ["docs/"]},
            "constraints": {},
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "source": "discord",
            "requires_human_approval": False,
            "approval_token": None,
            "risk_tier": "low",
        }
        path = outbox / "bypass-inject-001.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fake, f, indent=2)
        prev = os.environ.get("CALYX_RUNTIME_DIR")
        try:
            os.environ["CALYX_RUNTIME_DIR"] = str(runtime_dir)
            ok, err = run_work_envelope(fake, repo_root=REPO_ROOT)
        finally:
            if prev is not None:
                os.environ["CALYX_RUNTIME_DIR"] = prev
            else:
                os.environ.pop("CALYX_RUNTIME_DIR", None)
    return {
        "bypass_execution_allowed": ok,
        "denial_expected": not ok,
        "denial_reason": err,
        "invariant_held": not ok and err in ("intent_artifact_missing", "work_envelope_not_minted", "work_envelope_hash_mismatch"),
    }


# --- Phase C: Intent pipeline ---

def sim_deterministic_plan():
    """C2: Same intent state -> identical Work Envelope hash (no timestamp/random in hashed fields)."""
    from calyx.kernel.envelope import WorkEnvelope
    # Same canonical dict twice -> same hash
    ts = "2026-02-17T12:00:00Z"
    d = {
        "envelope_id": "sim-det-001",
        "intent_id": "sim-intent-001",
        "task_type": "doc_update",
        "scope": {"paths": ["docs/"]},
        "constraints": {"timeout_seconds": 60},
        "ts_utc": ts,
        "source": "discord",
        "requires_human_approval": False,
        "approval_token": None,
        "risk_tier": "low",
    }
    we1 = WorkEnvelope.from_dict(d)
    we2 = WorkEnvelope.from_dict(d.copy())
    h1 = we1.deterministic_hash()
    h2 = we2.deterministic_hash()
    return {
        "hash1": h1,
        "hash2": h2,
        "deterministic": h1 == h2,
    }


# --- Phase D: Contract ---

def sim_contract_unknown_task():
    """D1: Task with unknown task_type denied."""
    from calyx.kernel.contract import load_contract, validate_work_envelope
    from calyx.kernel.envelope import WorkEnvelope
    contract_path = REPO_ROOT / "CALYX_CONTRACT.yaml"
    contract, sha = load_contract(contract_path)
    we = WorkEnvelope(
        envelope_id="x",
        intent_id="y",
        task_type="unknown_task_type_xyz",
        scope={},
        constraints={},
        ts_utc="2026-02-17T12:00:00Z",
        source="discord",
        requires_human_approval=False,
        approval_token=None,
    )
    allowed, reason = validate_work_envelope(we, contract, sha)
    return {
        "allowed": allowed,
        "reason": reason,
        "invariant_held": not allowed and "not in allowed_tasks" in (reason or ""),
    }


def sim_contract_tampered_risk():
    """D1: High risk without approval token denied."""
    from calyx.kernel.contract import load_contract, validate_work_envelope
    from calyx.kernel.envelope import WorkEnvelope
    contract_path = REPO_ROOT / "CALYX_CONTRACT.yaml"
    contract, sha = load_contract(contract_path)
    we = WorkEnvelope(
        envelope_id="x",
        intent_id="y",
        task_type="doc_update",
        scope={},
        constraints={},
        ts_utc="2026-02-17T12:00:00Z",
        source="discord",
        requires_human_approval=False,
        approval_token=None,
        risk_tier="high",
    )
    allowed, reason = validate_work_envelope(we, contract, sha)
    return {
        "allowed": allowed,
        "reason": reason,
        "invariant_held": not allowed and "approval" in (reason or "").lower(),
    }


# --- Phase E: Metrics ---

def collect_metrics(sim_results: dict) -> dict:
    """Aggregate simulation results into spine_validation.json shape."""
    return {
        "parse_success_rate": 1.0 if sim_results.get("mail_replay", {}).get("first_delivery") else None,
        "replay_rejection_rate": 1.0 if sim_results.get("mail_replay", {}).get("second_delivery") else None,
        "contract_deny_rate_distribution": {
            "unknown_task_type": 1 if sim_results.get("contract_unknown", {}).get("invariant_held") else 0,
            "high_risk_no_approval": 1 if sim_results.get("contract_tampered", {}).get("invariant_held") else 0,
        },
        "unknown_task_type_rate": 0.0 if sim_results.get("contract_unknown", {}).get("invariant_held") else None,
        "containment_anomalies": 0 if sim_results.get("bypass", {}).get("invariant_held") else 1,
        "determinism_hash_stability": 1.0 if sim_results.get("deterministic_plan", {}).get("deterministic") else 0.0,
        "execution_success_rate": None,
        "average_intent_lifecycle_time": None,
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        "simulations_run": list(sim_results.keys()),
    }


# --- Run all and write receipts ---

def main():
    _ensure_dirs()
    sim_results = {}
    # A2
    sim_results["mail_replay"] = sim_mail_replay()
    # A3
    sim_results["bypass"] = sim_bypass_work_outbox()
    # C2
    sim_results["deterministic_plan"] = sim_deterministic_plan()
    # D1
    sim_results["contract_unknown"] = sim_contract_unknown_task()
    sim_results["contract_tampered"] = sim_contract_tampered_risk()
    metrics = collect_metrics(sim_results)
    with open(_metrics_path(), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    return sim_results


if __name__ == "__main__":
    r = main()
    print(json.dumps(r, indent=2))
