#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Evidence Batch - Generate export bundle for manual/automated transfer.

[CBO Governance]: This tool exports evidence envelopes that have not yet
been transferred to other Station Calyx nodes. It:
- Reads evidence journal
- Filters to envelopes after last exported sequence
- Writes timestamped JSONL bundle to exports/
- Updates export offset (append-only index file)

No network transmission occurs. Export bundles are for manual transfer
or later automated relay when network gate is opened.

Usage:
    python -u tools/export_evidence_batch.py
    python -u tools/export_evidence_batch.py --limit 100
    python -u tools/export_evidence_batch.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from station_calyx.evidence import EvidenceJournal, EvidenceEnvelopeV1
from station_calyx.node import get_node_identity

EXPORT_DIR = ROOT / "exports"
EXPORT_INDEX = ROOT / "outgoing" / "node" / "export_index.json"


def load_export_offset() -> int:
    """
    Load last exported sequence number.
    
    Returns:
        Last exported sequence (0 if never exported)
    """
    if not EXPORT_INDEX.exists():
        return 0
    
    try:
        data = json.loads(EXPORT_INDEX.read_text(encoding="utf-8"))
        return int(data.get("last_exported_seq", 0))
    except Exception as e:
        print(f"[WARN] Failed to load export index: {e}")
        return 0


def save_export_offset(seq: int, bundle_path: str) -> None:
    """
    Persist last exported sequence number (append-only semantics).

    [CBO Governance]: Export offset is tracked to ensure envelopes
    are only exported once. The index file maintains history.
    """
    EXPORT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing history
    history: List[dict] = []
    if EXPORT_INDEX.exists():
        try:
            data = json.loads(EXPORT_INDEX.read_text(encoding="utf-8"))
            history = data.get("history", [])
        except Exception:
            pass
    
    # Append new export record
    history.append({
        "seq": seq,
        "bundle": str(bundle_path),
        "exported_at": datetime.now().isoformat(),
    })
    
    # Write updated index
    data = {
        "last_exported_seq": seq,
        "updated_at": datetime.now().isoformat(),
        "history": history[-50:],  # Keep last 50 exports
    }
    
    # Atomic write
    temp_path = EXPORT_INDEX.with_suffix(".tmp")
    temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp_path.replace(EXPORT_INDEX)


def export_batch(limit: Optional[int] = None, dry_run: bool = False) -> int:
    """
    Export evidence batch to file.

    [CBO Governance]: Export creates a portable bundle of evidence
    for transfer to other Station Calyx nodes. The bundle:
    - Contains only envelopes not yet exported
    - Preserves hash chain (can be verified by receiver)
    - Is named with node_id and timestamp for traceability
    
    Args:
        limit: Maximum number of envelopes to export (None = all new)
        dry_run: If True, show what would be exported without writing
    
    Returns:
        Number of envelopes exported (or would be exported in dry-run)
    """
    # Get node identity
    node = get_node_identity()
    
    # Load journal
    journal = EvidenceJournal(node_id=node.node_id)
    print(f"[INFO] Journal: {journal.journal_path}")
    print(f"[INFO] Node: {node.node_id}")
    
    # Read all envelopes
    all_envelopes = journal.read_all()
    if not all_envelopes:
        print("[INFO] No envelopes in journal")
        return 0
    
    print(f"[INFO] Total envelopes in journal: {len(all_envelopes)}")
    
    # Filter by export offset
    last_exported = load_export_offset()
    new_envelopes = [e for e in all_envelopes if e.seq > last_exported]
    
    if not new_envelopes:
        print(f"[INFO] No new envelopes since last export (offset: {last_exported})")
        return 0
    
    print(f"[INFO] New envelopes: {len(new_envelopes)} (after seq {last_exported})")
    
    # Apply limit if specified
    if limit and limit > 0 and len(new_envelopes) > limit:
        export_envelopes = new_envelopes[:limit]
        print(f"[INFO] Limiting export to {len(export_envelopes)} envelopes")
    else:
        export_envelopes = new_envelopes
    
    # Dry-run output
    if dry_run:
        print("\n[DRY-RUN] Would export:")
        for env in export_envelopes[:10]:
            print(f"  seq={env.seq}, type={env.evidence_type}, ts={env.timestamp[:19]}")
        if len(export_envelopes) > 10:
            print(f"  ... and {len(export_envelopes) - 10} more")
        print(f"\n[DRY-RUN] Would update export offset: {last_exported} ? {export_envelopes[-1].seq}")
        return len(export_envelopes)
    
    # Create export bundle
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_name = f"evidence_bundle_{node.node_id}_{timestamp}.jsonl"
    bundle_path = EXPORT_DIR / bundle_name
    
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write bundle
    with open(bundle_path, "w", encoding="utf-8") as f:
        for envelope in export_envelopes:
            f.write(envelope.to_json() + "\n")
    
    # Update export offset
    last_seq = export_envelopes[-1].seq
    save_export_offset(last_seq, str(bundle_path))
    
    print(f"\n[SUCCESS] Exported {len(export_envelopes)} envelopes")
    print(f"  Bundle: {bundle_path}")
    print(f"  Sequence range: {export_envelopes[0].seq} ? {last_seq}")
    print(f"  Export offset: {last_exported} ? {last_seq}")
    
    return len(export_envelopes)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export evidence batch for manual/automated transfer"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of envelopes to export (default: all new)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be exported without writing",
    )
    
    args = parser.parse_args(argv)
    
    try:
        count = export_batch(limit=args.limit, dry_run=args.dry_run)
        return 0 if count >= 0 else 1
    except Exception as e:
        print(f"[ERROR] Export failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
