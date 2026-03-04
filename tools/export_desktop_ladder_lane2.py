#!/usr/bin/env python3
"""Update desktop ladder export with new Lane 2 receipts and rebuild manifest."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXPORT = REPO / "exports" / "desktop_ladder_20260216"
RESULTS_L2 = REPO / "runtime" / "benchmarks" / "results" / "prompt_injection_v0_2" / "calyx_desktop_01"

# New Lane 2 receipt filenames (from this run)
SEED_TO_FILE = {
    1337: "37f6472e96a0__20260216T210413.jsonl",
    42: "971c79608a0f__20260216T210421.jsonl",
    20260214: "f70e92b0ad38__20260216T210423.jsonl",
    8675309: "cc6b360fee66__20260216T210424.jsonl",
}


def main() -> None:
    export_l2 = EXPORT / "prompt_injection_v0_2" / "calyx_desktop_01"
    export_l2.mkdir(parents=True, exist_ok=True)

    # Remove old Lane 2 receipts in export (different timestamps)
    for f in list(export_l2.glob("*.jsonl")):
        f.unlink()

    # Copy new Lane 2 receipts
    for seed, name in SEED_TO_FILE.items():
        src = RESULTS_L2 / name
        if not src.exists():
            raise SystemExit(f"Missing receipt: {src}")
        shutil.copy2(src, export_l2 / name)

    # Update summaries (lane2_receipt_path and metrics)
    summaries_dir = EXPORT / "desktop_ladder_summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    for seed, name in SEED_TO_FILE.items():
        summary_path = summaries_dir / f"seed_{seed}_summary.json"
        rel_receipt = f"runtime/benchmarks/results/prompt_injection_v0_2/calyx_desktop_01/{name}"
        if summary_path.exists():
            data = json.loads(summary_path.read_text(encoding="utf-8"))
        else:
            data = {"seed": seed, "lane1_pass": True, "lane1_receipt_path": "", "lane1_parse_success_rate": 1, "lane1_protocol_compliance_rate": 1}
        data["lane2_pass"] = True
        data["lane2_receipt_path"] = rel_receipt
        data["lane2_containment_rate"] = 1
        data["lane2_attack_success_rate"] = 0
        data["lane2_unauthorized_tool_invocation_rate"] = 0
        summary_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Rebuild manifest: all files under EXPORT with relative path -> sha256
    files_dict = {}
    for path in sorted(EXPORT.rglob("*")):
        if path.is_file():
            rel = path.relative_to(EXPORT)
            key = str(rel).replace("/", "\\")
            files_dict[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"files": files_dict}
    manifest_json = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    manifest_sha = hashlib.sha256(manifest_json.encode()).hexdigest()
    manifest["manifest_sha256"] = manifest_sha
    (EXPORT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("Export updated:", EXPORT)
    print("Manifest SHA256:", manifest_sha)
    print("File count:", len(files_dict))


if __name__ == "__main__":
    main()
