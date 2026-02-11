import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(outdir: Path, correlation_id: str, parent_correlation_id: str | None) -> dict:
    evidence = outdir / "evidence.jsonl"
    findings = outdir / "findings.json"
    report = outdir / "report.md"
    extra_files = [
        outdir / "post_state_verification_receipt_proposal_fw_context_preserve_enable_001_real.json",
        outdir / "post_state_verification_report_proposal_fw_context_preserve_enable_001_real.json",
        outdir / "elevation_receipt.json",
        outdir / "elevation_status.json",
        REPO_ROOT / "governance" / "approvals" / "architect_identity_activation_test.verification_receipt.json",
        REPO_ROOT / "governance" / "approvals" / "architect_identity_activation_test.phase2_closure.md",
    ]
    elevation_status = None
    elevation_path = outdir / "elevation_status.json"
    if elevation_path.exists():
        try:
            elevation_status = json.loads(elevation_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            elevation_status = None

    manifest = {
        "correlation_id": correlation_id,
        "parent_correlation_id": parent_correlation_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "elevation_status": elevation_status,
        "artifacts": {
            "evidence.jsonl": {
                "path": str(evidence),
                "sha256": sha256_file(evidence),
                "bytes": evidence.stat().st_size,
            },
            "findings.json": {
                "path": str(findings),
                "sha256": sha256_file(findings),
                "bytes": findings.stat().st_size,
            },
            "report.md": {
                "path": str(report),
                "sha256": sha256_file(report),
                "bytes": report.stat().st_size,
            },
        },
    }
    for f in extra_files:
        if f.exists():
            manifest["artifacts"][f.name] = {
                "path": str(f),
                "sha256": sha256_file(f),
                "bytes": f.stat().st_size,
            }
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Calyx Guardian manifest")
    parser.add_argument("--outdir", default="logs/calyx_guardian")
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--parent-correlation-id", required=False)
    args = parser.parse_args()

    outdir = Path(args.outdir)
    manifest = build_manifest(outdir, args.correlation_id, args.parent_correlation_id)
    manifest_path = outdir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
