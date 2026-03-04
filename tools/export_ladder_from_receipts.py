#!/usr/bin/env python3
"""
Cross-platform export of ladder receipts for a node. Deterministic manifest and summaries.
For each seed+suite picks newest receipt under runtime/benchmarks/results/<suite>/<node_id>/ by seed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


def _get_seed_from_receipt(path: Path) -> int | None:
    """Read first JSON line of receipt; return seed or None."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                return rec.get("seed") if isinstance(rec.get("seed"), (int, float)) else None
            except (json.JSONDecodeError, TypeError):
                return None
    return None


def _discover_newest_receipt_for_seed(results_dir: Path, node_id: str, suite_id: str, seed: int) -> Path | None:
    """Find newest receipt file (by mtime) under results_dir/suite_id/node_id/ whose first-line seed matches. Return path or None."""
    node_dir = results_dir / suite_id / node_id
    if not node_dir.is_dir():
        return None
    candidates = []
    for p in node_dir.glob("*.jsonl"):
        if not p.is_file():
            continue
        s = _get_seed_from_receipt(p)
        if s is not None and int(s) == int(seed):
            candidates.append(p)
    if not candidates:
        return None
    # Newest by mtime; tie-break by path for determinism
    candidates.sort(key=lambda p: (p.stat().st_mtime_ns, str(p)))
    return candidates[-1]


def main() -> None:
    ap = argparse.ArgumentParser(description="Export ladder receipts for a node (deterministic manifest).")
    ap.add_argument("--repo_root", type=Path, default=Path("."), help="Repository root (default .).")
    ap.add_argument("--node_id", required=True, help="Node id (e.g. calyx_desktop_01).")
    ap.add_argument("--out_dir", required=True, type=Path, help="Export folder path.")
    ap.add_argument("--seeds", required=True, help="Comma-separated seeds (e.g. 1337,42,20260214,8675309).")
    ap.add_argument(
        "--suites",
        default="protocol_probe_v0_1,prompt_injection_v0_2",
        help="Comma-separated suites (default: protocol_probe_v0_1,prompt_injection_v0_2).",
    )
    args = ap.parse_args()

    repo_root = args.repo_root.resolve()
    out_dir = args.out_dir.resolve()
    node_id = args.node_id.strip()
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    suites = [s.strip() for s in args.suites.split(",") if s.strip()]

    if not repo_root.is_dir():
        print("STOP: repo_root is not a directory:", repo_root, file=sys.stderr)
        sys.exit(1)

    results_dir = repo_root / "runtime" / "benchmarks" / "results"
    if not results_dir.is_dir():
        print("STOP: results dir not found:", results_dir, file=sys.stderr)
        sys.exit(1)

    # (seed, suite) -> receipt path (source)
    chosen: dict[tuple[int, str], Path] = {}
    for seed in seeds:
        for suite_id in suites:
            src = _discover_newest_receipt_for_seed(results_dir, node_id, suite_id, seed)
            if src is None:
                print("STOP: no receipt for seed=%s suite=%s node=%s" % (seed, suite_id, node_id), file=sys.stderr)
                sys.exit(1)
            # Uniqueness: same seed+suite should map to one file; we picked newest
            key = (seed, suite_id)
            if key in chosen and chosen[key].resolve() != src.resolve():
                print("STOP: ambiguous receipts for seed=%s suite=%s" % (seed, suite_id), file=sys.stderr)
                sys.exit(1)
            chosen[key] = src

    out_dir.mkdir(parents=True, exist_ok=True)
    # Copy receipts: <out_dir>/<suite>/<node_id>/<receipt_filename> (use / for cross-platform manifest)
    rel_paths_copied: list[str] = []
    for (seed, suite_id), src in chosen.items():
        rel = "%s/%s/%s" % (suite_id, node_id, src.name)
        dest = out_dir / suite_id / node_id
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest / src.name)
        rel_paths_copied.append(rel)

    # Summaries: <out_dir>/<node_id>_ladder_summaries/seed_<seed>_summary.json
    # Lane1 = first suite, Lane2 = second suite (per default: protocol_probe_v0_1, prompt_injection_v0_2)
    summaries_dir = out_dir / ("%s_ladder_summaries" % node_id)
    summaries_dir.mkdir(parents=True, exist_ok=True)
    suite_l1 = suites[0]
    suite_l2 = suites[1] if len(suites) > 1 else None
    for seed in seeds:
        rel_l1 = "%s/%s/%s" % (suite_l1, node_id, chosen[(seed, suite_l1)].name)
        rel_l2 = "%s/%s/%s" % (suite_l2, node_id, chosen[(seed, suite_l2)].name) if suite_l2 else ""
        summary = {
            "seed": seed,
            "lane1_receipt_path": rel_l1,
            "lane2_receipt_path": rel_l2,
        }
        summary_path = summaries_dir / ("seed_%s_summary.json" % seed)
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        rel_sum = "%s_ladder_summaries/seed_%s_summary.json" % (node_id, seed)
        rel_paths_copied.append(rel_sum)

    # Manifest: deterministic. files = sorted relative path -> sha256 of file bytes. manifest_sha256 = SHA256(canonical JSON of files only).
    files_dict: dict[str, str] = {}
    all_rel = sorted(set(rel_paths_copied))
    for rel in all_rel:
        p = (out_dir / rel).resolve()
        if not p.is_file():
            continue
        files_dict[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    # Sorted keys + / path sep for cross-platform deterministic manifest
    files_sorted = dict(sorted(files_dict.items()))
    canonical_json = json.dumps(files_sorted, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    manifest_sha256 = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    manifest = {"manifest_sha256": manifest_sha256, "files": files_sorted}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Export written to:", out_dir)
    print("Manifest SHA256:", manifest_sha256)
    print("File count:", len(files_sorted))


if __name__ == "__main__":
    main()
