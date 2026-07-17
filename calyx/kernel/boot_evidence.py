"""Boot Evidence Pre-Network Gate utilities."""

from __future__ import annotations

import argparse
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .event_ledger import clear_system_phase, emit, set_system_phase
from .paths import resolve_repo_root, resolve_runtime_dir


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ts_tag(dt: datetime | None = None) -> str:
    return (dt or _utc_now()).strftime("%Y%m%d_%H%M%S")


def _marker_path(repo_root: Path) -> Path:
    return resolve_runtime_dir(repo_root) / "boot_evidence_marker.json"


def _audit_receipts_dir(repo_root: Path) -> Path:
    return resolve_runtime_dir(repo_root) / "receipts" / "audit"


@dataclass
class BootEvidenceStatus:
    ok: bool
    reason: str
    marker_path: str
    marker: dict


def commit_boot_evidence_bundle(
    repo_root: Path | None = None,
    *,
    source: str = "unknown",
    boot_session_id: str | None = None,
) -> dict:
    root = (repo_root or resolve_repo_root()).resolve()
    runtime_dir = resolve_runtime_dir(root)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    receipts_dir = _audit_receipts_dir(root)
    receipts_dir.mkdir(parents=True, exist_ok=True)

    now = _utc_now()
    session_id = (
        boot_session_id
        or os.environ.get("CALYX_BOOT_SESSION_ID")
        or f"boot-{uuid.uuid4()}"
    )
    receipt_name = f"boot_evidence_bundle__{_ts_tag(now)}.json"
    receipt_path = receipts_dir / receipt_name
    marker_path = _marker_path(root)

    payload = {
        "schema": "audit.boot_evidence_bundle.v1",
        "ts_utc": now.isoformat(),
        "boot_session_id": session_id,
        "source": source,
        "boot_evidence_bundle_committed": True,
        "marker_path": str(marker_path),
        "receipt_path": str(receipt_path),
    }
    receipt_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    marker = {
        "boot_evidence_bundle_committed": True,
        "boot_session_id": session_id,
        "ts_utc": now.isoformat(),
        "receipt_path": str(receipt_path),
        "source": source,
    }
    marker_path.write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8")

    set_system_phase("boot")
    try:
        emit(
            "INFO",
            "kernel",
            "boot.evidence.bundle.committed",
            "Boot evidence bundle committed before network activity",
            data={
                "boot_evidence_bundle_committed": True,
                "boot_session_id": session_id,
                "receipt_path": str(receipt_path),
                "marker_path": str(marker_path),
                "source": source,
            },
        )
    finally:
        clear_system_phase()

    return payload


def verify_boot_evidence(
    repo_root: Path | None = None,
    *,
    required_session_id: str | None = None,
) -> BootEvidenceStatus:
    root = (repo_root or resolve_repo_root()).resolve()
    marker_path = _marker_path(root)
    if not marker_path.exists():
        return BootEvidenceStatus(False, "marker_missing", str(marker_path), {})
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except Exception:
        return BootEvidenceStatus(False, "marker_invalid_json", str(marker_path), {})
    if marker.get("boot_evidence_bundle_committed") is not True:
        return BootEvidenceStatus(False, "marker_not_committed", str(marker_path), marker)
    if required_session_id and marker.get("boot_session_id") != required_session_id:
        return BootEvidenceStatus(False, "session_id_mismatch", str(marker_path), marker)
    return BootEvidenceStatus(True, "ok", str(marker_path), marker)


def assert_boot_evidence_or_fail(
    *,
    component: str,
    required_session_id: str | None = None,
    repo_root: Path | None = None,
) -> None:
    status = verify_boot_evidence(repo_root=repo_root, required_session_id=required_session_id)
    if status.ok:
        return
    set_system_phase("boot")
    try:
        emit(
            "ERROR",
            component,
            "governance.assertion.failed",
            "Boot evidence pre-network gate failed closed",
            data={
                "reason": "boot_evidence_missing",
                "boot_evidence_reason": status.reason,
                "marker_path": status.marker_path,
                "required_session_id": required_session_id or "",
            },
        )
    finally:
        clear_system_phase()
    raise RuntimeError(f"boot_evidence_missing: {status.reason}")


def _main() -> int:
    parser = argparse.ArgumentParser(description="Boot evidence pre-network gate utility")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_commit = sub.add_parser("commit", help="Write boot evidence bundle + marker")
    p_commit.add_argument("--source", default="cli")
    p_commit.add_argument("--boot-session-id", default="")

    p_verify = sub.add_parser("verify", help="Verify marker exists and committed")
    p_verify.add_argument("--required-session-id", default="")

    args = parser.parse_args()
    if args.cmd == "commit":
        out = commit_boot_evidence_bundle(
            source=args.source,
            boot_session_id=(args.boot_session_id or None),
        )
        print(json.dumps(out, ensure_ascii=False))
        return 0

    status = verify_boot_evidence(required_session_id=(args.required_session_id or None))
    print(json.dumps({"ok": status.ok, "reason": status.reason, "marker_path": status.marker_path, "marker": status.marker}, ensure_ascii=False))
    return 0 if status.ok else 2


if __name__ == "__main__":
    raise SystemExit(_main())
