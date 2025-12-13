"""Calyx Governance CLI v0.1 (reflection-only).

Builds governance_request_v0.1 objects, appends them to governance log,
and routes them through the governance orchestrator for a governance_decision
event. No execution/mutation is performed.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from tools.governance_orchestrator import run_governance_request


def now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def make_governance_request(scope: str, action: str, description: str, file_path: str) -> Dict[str, Any]:
    request_id = f"govreq-{now_iso()}-{uuid.uuid4().hex[:8]}"
    return {
        "schema_version": "governance_request_v0.1",
        "request_id": request_id,
        "timestamp": now_iso(),
        "channel": "governance_cli",
        "actor": {
            "role": "architect",
            "id": "architect-local",
            "auth_method": "local_cli",
        },
        "intent": {
            "scope": scope,
            "requested_action": action,
            "description": description,
            "target": {
                "kind": "file",
                "path": file_path,
            },
        },
        "safety_frame": {
            "execution_allowed": True,
            "max_side_effects": [
                "read_target_file",
                "write_canon_copy",
                "update_diagnostics_index",
            ],
            "forbidden_effects": [
                "change_execution_policy",
                "enable_network_access",
                "alter_autonomy_level",
            ],
            "dry_run": False,
        },
        "telemetry": {
            "source_cli": "bloomos.ui.calyx_governance_cli",
            "workstation_id": "station-local-001",
        },
    }


def append_governance_log(request: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        json.dump(request, handle, ensure_ascii=False)
        handle.write("\n")


def cmd_ingest(args: argparse.Namespace) -> None:
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"[governance_cli] ERROR: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    description = args.description or f"Ingest directive file {args.file} for scope {args.scope}."
    req = make_governance_request(
        scope=args.scope,
        action="ingest_directive",
        description=description,
        file_path=args.file,
    )

    append_governance_log(req, Path("logs") / "calyx" / "governance_requests.jsonl")

    decision = run_governance_request(req)

    outcome = decision.get("outcome", "unknown").upper()
    print(f"[governance_cli] Submitted governance request {req['request_id']}")
    print(f"Outcome: {outcome}")
    reason = decision.get("reason")
    if reason:
        print(f"Reason: {reason}")
    canon_path = decision.get("canonical_path")
    if canon_path:
        print(f"Canonical path: {canon_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="calyx_governance_cli",
        description="Calyx Governance CLI (reflection-only).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Ingest a governance directive into canon (reflection-only).")
    p_ingest.add_argument("--scope", required=True, help="Logical scope, e.g., kernel_diagnostics.")
    p_ingest.add_argument("--file", required=True, help="Path to the directive file.")
    p_ingest.add_argument(
        "--description",
        required=False,
        help="Human-readable description of the directive.",
    )
    p_ingest.set_defaults(func=cmd_ingest)

    return parser


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
