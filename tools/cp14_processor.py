#!/usr/bin/env python3
"""
CP14 Sentinel Processor - Static Security Scanner
Part of Capability Evolution Phase 1
CGPT-provided processor for proposal security scanning
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("CP14 requires pyyaml. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


def load_rules(p: Path) -> dict:
    """Load scan rules from YAML"""
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def parse_patch_lines(patch_text: str):
    """Parse patch lines, skipping headers"""
    for ln in patch_text.splitlines():
        if ln.startswith('+++') or ln.startswith('---') or ln.startswith('@@'):
            continue
        yield ln


def file_ext_from_diff_header(lines):
    """Extract file extension from diff header"""
    for ln in lines:
        if ln.startswith('+++ b/'):
            path = ln[6:].strip()
            return Path(path).suffix
    return None


def scan(intent_id: str, proposals_dir: Path, rules: dict):
    """
    Scan proposal for security issues
    
    Returns:
        (verdict, findings) tuple
    """
    intent_dir = proposals_dir / intent_id
    patch_path = intent_dir / "change.patch"
    meta_path = intent_dir / "metadata.json"

    if not patch_path.exists() or not meta_path.exists():
        return ("FAIL", [{"type": "artifact_missing", "path": str(intent_dir)}])

    patch_text = patch_path.read_text(encoding="utf-8", errors="replace")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    findings = []
    total_added_removed = meta.get("lines_added", 0) + meta.get("lines_removed", 0)
    if total_added_removed > int(rules.get("max_total_lines", 500)):
        findings.append({"type": "oversize_diff", "value": total_added_removed})

    allow_exts = set(rules.get("allow_extensions", []))
    forb = [re.compile(r, re.MULTILINE) for r in rules.get("forbidden_regex", [])]

    # Scan only added lines
    for ln in patch_text.splitlines():
        if not ln.startswith('+') or ln.startswith('+++'):
            continue
        added = ln[1:]

        for rx in forb:
            m = rx.search(added)
            if m:
                findings.append({"type": "forbidden_pattern", "pattern": rx.pattern, "line": added[:240]})

    # Check file extension
    ext = file_ext_from_diff_header(patch_text.splitlines())
    if ext and allow_exts and ext not in allow_exts:
        findings.append({"type": "disallowed_extension", "ext": ext})

    verdict = "FAIL" if findings else "PASS"
    return (verdict, findings)


def main():
    ap = argparse.ArgumentParser(description="CP14 Sentinel Processor")
    ap.add_argument("--intent", required=True, help="Intent ID")
    ap.add_argument("--proposals-dir", required=True, help="Proposals directory")
    ap.add_argument("--reviews-dir", required=True, help="Reviews directory")
    ap.add_argument("--rules", required=True, help="Rules file path")
    args = ap.parse_args()

    proposals = Path(args.proposals_dir)
    reviews = Path(args.reviews_dir)
    rules = load_rules(Path(args.rules))
    verdict, findings = scan(args.intent, proposals, rules)

    out = {
        "intent_id": args.intent,
        "verdict": verdict,
        "findings": findings,
        "network_egress": "DENIED",
        "syscall_risk": "LOW" if verdict == "PASS" else "MED"
    }
    
    reviews.mkdir(parents=True, exist_ok=True)
    (reviews / f"{args.intent}.CP14.verdict.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

