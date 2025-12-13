#!/usr/bin/env python3
"""
Intent Linker - Phase 1 Shadow Mode
Links artifacts to intents
Part of Capability Evolution Phase 1
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTENTS_DIR = ROOT / "outgoing" / "intents"
PROPOSALS_DIR = ROOT / "outgoing" / "proposals"
REPORTS_DIR = ROOT / "outgoing" / "reports"


def attach_artifacts(intent_path: str, proposals_dir: str = None, reports_dir: str = None):
    """
    Attach artifacts to intent
    
    Args:
        intent_path: Path to intent JSON file
        proposals_dir: Proposals directory (defaults to outgoing/proposals)
        reports_dir: Reports directory (defaults to outgoing/reports)
    """
    intent_file = Path(intent_path)
    if not intent_file.exists():
        raise FileNotFoundError(f"Intent file not found: {intent_path}")
    
    intent = json.loads(intent_file.read_text(encoding="utf-8"))
    iid = intent["intent_id"]
    
    # Set defaults
    proposals_dir = Path(proposals_dir) if proposals_dir else PROPOSALS_DIR
    reports_dir = Path(reports_dir) if reports_dir else REPORTS_DIR
    
    base = proposals_dir / iid
    reports_base = reports_dir / iid
    
    # Verify artifacts exist
    patch_file = base / "change.patch"
    reverse_patch_file = base / "change.reverse.patch"
    metadata_file = base / "metadata.json"
    
    if not patch_file.exists():
        raise FileNotFoundError(f"Patch file not found: {patch_file}")
    if not reverse_patch_file.exists():
        raise FileNotFoundError(f"Reverse patch file not found: {reverse_patch_file}")
    if not metadata_file.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_file}")
    
    # Create reports directory
    reports_base.mkdir(parents=True, exist_ok=True)
    
    # Attach artifacts
    intent["artifacts"] = {
        "diff": str(patch_file),
        "reverse_diff": str(reverse_patch_file),
        "metadata": str(metadata_file),
        "reports_dir": str(reports_base)
    }
    
    # Write updated intent
    intent_file.write_text(json.dumps(intent, indent=2), encoding="utf-8")
    
    return intent


def main():
    parser = argparse.ArgumentParser(description="Intent Linker - Phase 1")
    parser.add_argument("--intent-path", required=True, help="Path to intent JSON file")
    parser.add_argument("--proposals-dir", help="Proposals directory")
    parser.add_argument("--reports-dir", help="Reports directory")
    
    args = parser.parse_args()
    
    try:
        intent = attach_artifacts(args.intent_path, args.proposals_dir, args.reports_dir)
        print(json.dumps(intent, indent=2))
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

