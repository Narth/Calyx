#!/usr/bin/env python3
"""
Diff Generator - Phase 1 Shadow Mode
Generates unified diffs, reverse patches, and metadata
Part of Capability Evolution Phase 1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import difflib
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]
PROPOSALS_DIR = ROOT / "outgoing" / "proposals"


def sha256_bytes(b: bytes) -> str:
    """Calculate SHA256 hash"""
    return hashlib.sha256(b).hexdigest()


def unified_diff(old: str, new: str, path: str) -> str:
    """Generate unified diff between old and new content"""
    return "".join(difflib.unified_diff(
        old.splitlines(True), new.splitlines(True),
        fromfile=f"a/{path}", tofile=f"b/{path}", n=3))


def generate_diff(intent_id: str, file_pairs: List[Tuple[str, str, str]], outdir: str, 
                  max_lines: int = 500, max_bytes: int = 5242880) -> dict:
    """
    Generate diff with reverse patch and metadata
    
    Args:
        intent_id: Intent ID
        file_pairs: List of (path, old_content, new_content)
        outdir: Output directory
        max_lines: Maximum lines allowed (enforced)
        max_bytes: Maximum bytes allowed (enforced)
        
    Returns:
        Dictionary with results and paths
    """
    out = Path(outdir) / intent_id
    out.mkdir(parents=True, exist_ok=True)
    
    patch_lines, rev_lines = [], []
    added, removed, changed = 0, 0, 0
    total_bytes = 0
    
    for path, old, new in file_pairs:
        d = unified_diff(old, new, path)
        if not d:
            continue
            
        patch_lines.append(d)
        rd = unified_diff(new, old, path)
        rev_lines.append(rd)
        
        if old != new:
            changed += 1
            added += sum(1 for ln in d.splitlines() if ln.startswith('+') and not ln.startswith('+++'))
            removed += sum(1 for ln in d.splitlines() if ln.startswith('-') and not ln.startswith('---'))
            total_bytes += len(d.encode('utf-8'))
    
    # Enforce constraints
    total_lines = added + removed
    if total_lines > max_lines:
        raise ValueError(f"Diff exceeds line limit: {total_lines} > {max_lines}")
    
    if total_bytes > max_bytes:
        raise ValueError(f"Diff exceeds byte limit: {total_bytes} > {max_bytes}")
    
    # Write patch and reverse patch
    patch_content = "".join(patch_lines)
    rev_content = "".join(rev_lines)
    
    (out / "change.patch").write_text(patch_content, encoding="utf-8")
    (out / "change.reverse.patch").write_text(rev_content, encoding="utf-8")
    
    # Generate metadata
    meta = {
        "intent_id": intent_id,
        "files_changed": changed,
        "lines_added": added,
        "lines_removed": removed,
        "total_lines": total_lines,
        "total_bytes": total_bytes,
        "sha_patch": sha256_bytes(patch_content.encode()),
        "sha_reverse": sha256_bytes(rev_content.encode()),
        "patch_path": str(out / "change.patch"),
        "reverse_patch_path": str(out / "change.reverse.patch")
    }
    
    (out / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    
    return {
        "success": True,
        "output_dir": str(out),
        "metadata": meta
    }


def main():
    parser = argparse.ArgumentParser(description="Diff Generator - Phase 1")
    parser.add_argument("--intent-id", required=True, help="Intent ID")
    parser.add_argument("--file", nargs=3, action="append", metavar=("PATH", "OLD", "NEW"),
                       help="File pair: path old_content new_content")
    parser.add_argument("--max-lines", type=int, default=500, help="Maximum lines")
    parser.add_argument("--max-bytes", type=int, default=5242880, help="Maximum bytes")
    parser.add_argument("--outdir", default=str(PROPOSALS_DIR), help="Output directory")
    
    args = parser.parse_args()
    
    if not args.file:
        parser.error("At least one --file is required")
    
    try:
        result = generate_diff(
            args.intent_id,
            args.file,
            args.outdir,
            args.max_lines,
            args.max_bytes
        )
        print(json.dumps(result, indent=2))
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

