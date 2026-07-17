"""Generate a bounded Hub Runner validation receipt for Code Factory CI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from calyx.execution.hub_runner import run_work_envelope
from calyx.kernel.envelope import WorkEnvelope


EXPECTED_REASON = "swarm_execution_not_enabled_phase2"


def probe_envelope(pr_number: int) -> WorkEnvelope:
    """Build a validate-only envelope that cannot execute mutation or network work."""

    suffix = f"pr-{pr_number}"
    return WorkEnvelope(
        envelope_id=f"ci-{suffix}-hub-runner-receipt",
        intent_id=f"ci-{suffix}-hub-runner-intent",
        task_type="doc_update",
        scope={
            "paths": ["calyx/kernel/**"],
            "swarm": {
                "swarm_run_id": f"ci-{suffix}-swarm-validation",
                "task_intent": "Generate a validate-only CI receipt",
                "file_scope": {
                    "read_paths": ["calyx/kernel/**", "tests/**"],
                    "write_paths": ["calyx/kernel/swarm_work_envelope.py"],
                },
                "tool_scope": ["read_files", "write_files"],
                "network_scope": {"mode": "deny", "allowlist": []},
                "success_criteria": ["Hub Runner validation receipt emitted"],
                "worker_plan": [
                    {
                        "worker_id": "ci-validation-worker",
                        "task_intent": "Validate the bounded envelope",
                        "ownership_scope": {
                            "read_paths": ["calyx/kernel/**"],
                            "write_paths": ["calyx/kernel/swarm_work_envelope.py"],
                            "deny_paths": ["runtime/**"],
                        },
                        "allowed_tool_classes": ["read_files", "write_files"],
                        "network_scope": {"mode": "deny", "allowlist": []},
                        "success_criteria": ["Validation receipt emitted without execution"],
                    }
                ],
            },
        },
        constraints={
            "timeout_seconds": 60,
            "swarm": {
                "ownership_policy": "exclusive_write_scope",
                "overlapping_write_scope_declared": False,
                "requires_receipt_bundle": True,
                "requires_trace_graph": True,
                "reconciliation_required": True,
            },
        },
        ts_utc="2026-07-16T00:00:00Z",
        source="cbo_core",
        requires_human_approval=False,
        approval_token=None,
    )


def generate_probe_receipt(pr_number: int, *, repo_root: Path, runtime_dir: Path) -> Path:
    """Run the validate-only probe and return its Hub Runner JSONL receipt."""

    if pr_number <= 0:
        raise ValueError("pr_number must be a positive integer")

    repo_root = repo_root.resolve()
    runtime_dir = runtime_dir.resolve()
    envelope = probe_envelope(pr_number)
    status_dir = runtime_dir / "cbo" / "intents" / envelope.intent_id
    status_dir.mkdir(parents=True, exist_ok=True)
    (status_dir / "status.json").write_text(
        json.dumps(
            {
                "status": "minted",
                "work_envelope_hash": envelope.deterministic_hash(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    previous_runtime = os.environ.get("CALYX_RUNTIME_DIR")
    os.environ["CALYX_RUNTIME_DIR"] = str(runtime_dir)
    try:
        ok, reason = run_work_envelope(envelope, repo_root=repo_root)
    finally:
        if previous_runtime is None:
            os.environ.pop("CALYX_RUNTIME_DIR", None)
        else:
            os.environ["CALYX_RUNTIME_DIR"] = previous_runtime

    if ok or reason != EXPECTED_REASON:
        raise RuntimeError(f"CI Hub Runner probe returned unexpected result: ok={ok}, reason={reason}")

    receipt_paths = sorted((runtime_dir / "receipts").glob("hub_runner__*.jsonl"))
    for path in reversed(receipt_paths):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if (
                record.get("envelope_id") == envelope.envelope_id
                and record.get("status") == "allowed"
                and record.get("reason") == "swarm_validate_only_phase2"
            ):
                return path
    raise RuntimeError("Hub Runner probe completed without its expected validation receipt")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--runtime-dir", type=Path)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    runtime_dir = (args.runtime_dir or (repo_root / "runtime")).resolve()
    try:
        receipt_path = generate_probe_receipt(
            args.pr_number,
            repo_root=repo_root,
            runtime_dir=runtime_dir,
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Hub Runner CI validation receipt: {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
