#!/usr/bin/env python3
"""
CP18 Validator Processor - Dry Validation & Test Heuristics
Part of Capability Evolution Phase 1
CGPT-provided processor for proposal validation
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
    print("CP18 requires pyyaml. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


ADDED = re.compile(r'^\+(?!\+\+)')  # begin with '+' but not diff header


def load_rules(p: Path) -> dict:
    """Load validation rules from YAML"""
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def read_json(p: Path) -> dict:
    """Read JSON file"""
    return json.loads(p.read_text(encoding="utf-8"))


def scan_added_lines(patch_text: str, rules: dict):
    """Scan added lines for issues"""
    issues = []
    for ln in patch_text.splitlines():
        if not ADDED.match(ln):
            continue
        code = ln[1:]

        if rules.get("max_line_length") and len(code) > int(rules["max_line_length"]):
            issues.append({"type": "style_long_line", "length": len(code), "line": code[:200]})

        if rules.get("deny_new_prints") and re.search(r'\bprint\(', code):
            issues.append({"type": "style_print_usage", "line": code[:200]})

        if rules.get("deny_todos") and "TODO" in code:
            issues.append({"type": "style_todo_leftover", "line": code[:200]})

        if rules.get("flag_assert_false") and re.search(r'\bassert\s+False\b', code):
            issues.append({"type": "tests_breakage_pattern", "line": code[:200]})

        if rules.get("flag_skip_tests") and re.search(r'@pytest\.mark\.skip|@unittest\.skip', code):
            issues.append({"type": "tests_skipped_marker", "line": code[:200]})

        # Crude import error risk: adding 'from X import *'
        if re.search(r'from\s+\S+\s+import\s+\*', code):
            issues.append({"type": "quality_wildcard_import", "line": code[:200]})

    return issues


def validate_tests_reference(intent: dict, repo_root: Path | None):
    """Validate tests reference exists"""
    problems = []
    refs = intent.get("tests_reference") or []
    if not refs:
        problems.append({"type": "tests_missing_reference"})
        return problems

    # Optional: verify referenced files exist (read-only)
    if repo_root:
        for ref in refs:
            # accept "a/b.py::Class::test_case" or "a/b.py::test_fn"
            path = ref.split("::")[0]
            if not (repo_root / path).exists():
                problems.append({"type": "tests_reference_not_found", "ref": ref})
    return problems


def main():
    ap = argparse.ArgumentParser(description="CP18 Validator Processor")
    ap.add_argument("--intent", required=True, help="Intent ID")
    ap.add_argument("--proposals-dir", required=True, help="Proposals directory")
    ap.add_argument("--reviews-dir", required=True, help="Reviews directory")
    ap.add_argument("--rules", required=True, help="Rules file path")
    ap.add_argument("--repo-root", required=False, help="Repository root (optional)")
    args = ap.parse_args()

    proposals = Path(args.proposals_dir)
    reviews = Path(args.reviews_dir)
    rules = load_rules(Path(args.rules))
    repo_root = Path(args.repo_root) if args.repo_root else None

    intent_dir = proposals / args.intent
    patch_path = intent_dir / "change.patch"
    meta_path = intent_dir / "metadata.json"
    
    # Find per-intent json if present alongside artifacts
    per_intent = intent_dir / "intent.json"
    intent = {}
    if per_intent.exists():
        intent = read_json(per_intent)

    if not patch_path.exists() or not meta_path.exists():
        out = {"intent_id": args.intent, "verdict": "FAIL", "details": {"error": "missing_artifacts"}}
        reviews.mkdir(parents=True, exist_ok=True)
        (reviews / f"{args.intent}.CP18.verdict.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2))
        sys.exit(0)

    patch_text = patch_path.read_text(encoding="utf-8", errors="replace")
    meta = read_json(meta_path)

    issues = scan_added_lines(patch_text, rules)
    test_refs = validate_tests_reference(intent, repo_root)

    details = {
        "style_issues": [i for i in issues if i["type"].startswith("style")],
        "test_warnings": [i for i in issues if i["type"].startswith("tests_")] + test_refs,
        "metrics": {
            "files_changed": meta.get("files_changed", 0),
            "lines_added": meta.get("lines_added", 0),
            "lines_removed": meta.get("lines_removed", 0)
        }
    }

    # Verdict logic (dry): FAIL only on clear risk to test integrity or missing refs
    fail_reasons = []
    if any(i["type"] in ("tests_breakage_pattern",) for i in issues):
        fail_reasons.append("tests_breakage_pattern")
    if any(i["type"] == "tests_missing_reference" for i in test_refs):
        fail_reasons.append("tests_missing_reference")

    # Large change warning (not fail)
    warn_thresh = int(rules.get("warn_on_large_change_threshold", 400))
    if (meta.get("lines_added", 0) + meta.get("lines_removed", 0)) > warn_thresh:
        details["warning"] = f"large_diff_over_{warn_thresh}"

    verdict = "FAIL" if fail_reasons else "PASS"
    details["lints"] = "PASS" if not details["style_issues"] else "WARN"
    details["unit_tests"] = "N/A"  # Phase-1: no execution
    details["integration_tests"] = "N/A"
    details["coverage_delta"] = 0.0  # Phase-1: not measured

    out = {"intent_id": args.intent, "verdict": verdict, "details": details}
    reviews.mkdir(parents=True, exist_ok=True)
    (reviews / f"{args.intent}.CP18.verdict.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

