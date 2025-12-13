#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify Evidence System - Test and verify evidence collection infrastructure.

[CBO Governance]: This verification suite validates all components of
Node Evidence Relay v0:
- Node identity persistence across restarts
- Sequence monotonicity (strict increment, no gaps)
- Evidence journal append-only behavior
- Hash chain integrity (prev_hash linkage)
- Export batch generation (only new envelopes)

Run this after deployment and periodically to ensure system integrity.

Usage:
    python -u tools/verify_evidence_system.py
    python -u tools/verify_evidence_system.py --quick
    python -u tools/verify_evidence_system.py --verbose
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from station_calyx.node import get_node_identity, SequenceManager
from station_calyx.evidence import EvidenceJournal, EvidenceType, append_evidence


def print_header(title: str) -> None:
    """Print test section header."""
    print(f"\n[TEST] {title}")
    print("-" * 60)


def verify_node_identity(verbose: bool = False) -> Tuple[bool, str]:
    """
    Verify node identity persistence.
    
    Tests:
    - Identity can be loaded
    - Identity persists (same node_id on repeated calls)
    - Required fields are present
    """
    print_header("Node Identity Persistence")
    
    try:
        # Get identity twice
        node1 = get_node_identity()
        node2 = get_node_identity()
        
        # Should be identical
        if node1.node_id != node2.node_id:
            return (False, f"Node IDs differ: {node1.node_id} vs {node2.node_id}")
        
        # Check required fields
        if not node1.node_id or not node1.fingerprint:
            return (False, "Missing required fields")
        
        print(f"  Node ID: {node1.node_id}")
        print(f"  Hostname: {node1.hostname}")
        print(f"  Station: {node1.station_name}")
        
        if verbose:
            print(f"  Platform: {node1.platform_info}")
            print(f"  Fingerprint: {node1.fingerprint}")
            print(f"  Created: {node1.created_at}")
        
        print("? PASS: Identity persists correctly")
        return (True, "")
        
    except Exception as e:
        return (False, str(e))


def verify_sequence_monotonic(verbose: bool = False) -> Tuple[bool, str]:
    """
    Verify sequence monotonicity and persistence.
    
    Tests:
    - Sequence increments by 1 each call
    - Sequence persists across SequenceManager instances
    - No gaps or decrements
    """
    print_header("Sequence Monotonicity")
    
    try:
        seq_mgr = SequenceManager()
        
        # Get current
        initial = seq_mgr.current()
        print(f"  Initial sequence: {initial}")
        
        # Increment 5 times
        seqs = []
        for _ in range(5):
            seq = seq_mgr.next()
            seqs.append(seq)
        
        if verbose:
            print(f"  Generated: {seqs}")
        
        # Verify monotonic (each is prev + 1)
        for i in range(1, len(seqs)):
            if seqs[i] != seqs[i - 1] + 1:
                return (False, f"Non-monotonic: {seqs[i-1]} ? {seqs[i]}")
        
        # Simulate restart (new instance)
        seq_mgr2 = SequenceManager()
        loaded = seq_mgr2.current()
        next_after_restart = seq_mgr2.next()
        
        if loaded != seqs[-1]:
            return (False, f"Not persisted: expected {seqs[-1]}, loaded {loaded}")
        
        if next_after_restart != seqs[-1] + 1:
            return (False, f"Post-restart: expected {seqs[-1] + 1}, got {next_after_restart}")
        
        print(f"  Sequence range: {initial} ? {next_after_restart}")
        print(f"? PASS: Monotonic and persisted")
        return (True, "")
        
    except Exception as e:
        return (False, str(e))


def verify_evidence_journal(num_envelopes: int = 10, verbose: bool = False) -> Tuple[bool, str]:
    """
    Verify evidence journal append-only and hash chain.
    
    Tests:
    - Envelopes are appended (count increases)
    - Hash chain is valid (prev_hash links correctly)
    - Envelopes can be verified (hash matches content)
    """
    print_header(f"Evidence Journal ({num_envelopes} envelopes)")
    
    try:
        journal = EvidenceJournal()
        print(f"  Journal: {journal.journal_path}")
        
        # Record initial state
        initial_count = journal.count()
        print(f"  Initial count: {initial_count}")
        
        # Write test envelopes
        written: List = []
        for i in range(num_envelopes):
            envelope = journal.append(
                evidence_type=EvidenceType.METRIC_SAMPLE,
                payload={
                    "test_id": i,
                    "value": i * 100,
                    "timestamp": time.time(),
                    "verification_run": datetime.now().isoformat(),
                },
                tags=["verification", "test"],
                source="verify_evidence_system",
            )
            written.append(envelope)
            
            if verbose:
                print(f"    Written: seq={envelope.seq}")
        
        print(f"  Written: {len(written)} envelopes")
        print(f"  Sequence range: {written[0].seq} ? {written[-1].seq}")
        
        # Verify append-only (count increased)
        final_count = journal.count()
        if final_count != initial_count + num_envelopes:
            return (False, f"Count mismatch: expected {initial_count + num_envelopes}, got {final_count}")
        
        print(f"  Final count: {final_count}")
        print(f"? Append-only: count increased correctly")
        
        # Verify hash chain
        is_valid, error = journal.verify_chain()
        if not is_valid:
            return (False, f"Chain verification failed: {error}")
        
        print(f"? Hash chain: valid")
        
        # Verify prev_hash chaining in written batch
        for i in range(1, len(written)):
            if written[i].prev_hash != written[i - 1].envelope_hash:
                return (False, f"Written batch chain break at index {i}")
        
        print(f"? Written batch: correctly chained")
        
        return (True, "")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return (False, str(e))


def verify_export_batch(verbose: bool = False) -> Tuple[bool, str]:
    """
    Verify export batch generation.
    
    Tests:
    - Export creates bundle file
    - Bundle contains valid JSON lines
    - Export offset is tracked
    """
    print_header("Export Batch Generation")
    
    try:
        from tools.export_evidence_batch import export_batch, load_export_offset, EXPORT_DIR
        
        # Get initial offset
        initial_offset = load_export_offset()
        print(f"  Initial export offset: {initial_offset}")
        
        # Export batch
        count = export_batch(limit=None, dry_run=False)
        
        if count > 0:
            print(f"  Exported: {count} envelopes")
            
            # Find latest bundle
            bundles = list(EXPORT_DIR.glob("evidence_bundle_*.jsonl"))
            if not bundles:
                return (False, "No bundle files created")
            
            latest = max(bundles, key=lambda p: p.stat().st_mtime)
            print(f"  Bundle: {latest.name}")
            
            # Verify bundle format
            with open(latest, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            print(f"  Bundle size: {len(lines)} lines")
            
            # Verify first line is valid JSON with required fields
            if lines:
                first = json.loads(lines[0])
                required = ["node_id", "seq", "timestamp", "evidence_type", "payload", "envelope_hash"]
                for field in required:
                    if field not in first:
                        return (False, f"Missing field in envelope: {field}")
            
            # Verify offset updated
            new_offset = load_export_offset()
            if new_offset <= initial_offset:
                return (False, f"Offset not updated: {initial_offset} ? {new_offset}")
            
            print(f"  Export offset: {initial_offset} ? {new_offset}")
            print(f"? PASS: Bundle created and offset tracked")
        else:
            print(f"  No new envelopes to export")
            print(f"? PASS: Export handled correctly (nothing new)")
        
        return (True, "")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return (False, str(e))


def run_verification(quick: bool = False, verbose: bool = False) -> bool:
    """
    Run full verification suite.
    
    Args:
        quick: If True, use fewer test envelopes
        verbose: If True, show detailed output
    
    Returns:
        True if all tests pass
    """
    print("=" * 60)
    print("[CBO Governance] Node Evidence Relay v0 - Verification Suite")
    print("=" * 60)
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Mode: {'quick' if quick else 'full'}")
    
    num_envelopes = 5 if quick else 10
    
    results = {}
    
    # Run tests
    passed, error = verify_node_identity(verbose)
    results["Node Identity"] = (passed, error)
    
    passed, error = verify_sequence_monotonic(verbose)
    results["Sequence Monotonic"] = (passed, error)
    
    passed, error = verify_evidence_journal(num_envelopes, verbose)
    results["Evidence Journal"] = (passed, error)
    
    passed, error = verify_export_batch(verbose)
    results["Export Batch"] = (passed, error)
    
    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test, (passed, error) in results.items():
        status = "? PASS" if passed else "? FAIL"
        print(f"{status}: {test}")
        if not passed and error:
            print(f"       Error: {error}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] ALL TESTS PASSED - Evidence system operational")
    else:
        print("[FAIL] SOME TESTS FAILED - Review errors above")
    print("=" * 60)
    
    return all_passed


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify evidence collection infrastructure"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode (fewer test envelopes)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    
    args = parser.parse_args(argv)
    
    try:
        success = run_verification(quick=args.quick, verbose=args.verbose)
        return 0 if success else 1
    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
