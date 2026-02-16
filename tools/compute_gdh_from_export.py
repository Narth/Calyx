#!/usr/bin/env python3
"""
Compute Governance Determinism Hash (GDH) v0.1 from an export root.
Reads receipt JSONL only; no harness changes. Outputs a GDH report JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Allow importing harness for compliance derivation (read-only)
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.harness.lane import (
    _case_protocol_compliant,
    NO_TOOL_CASE,
    TOOL_REQUIRED_CASES,
)
from benchmarks.harness.policy import ALLOWLIST

# v0.2 accepted-mode decision enum
DECISION_ACCEPT = "ACCEPT"
DECISION_NO_TOOL = "NO_TOOL"
DECISION_REJECT_PARSE = "REJECT_PARSE"
DECISION_REJECT_POLICY = "REJECT_POLICY"
REASON_PARSE_FAIL = "PARSE_FAIL"
REASON_NOT_ALLOWLISTED = "NOT_ALLOWLISTED"
REASON_NO_TOOL_EXPECTED = "NO_TOOL_EXPECTED"


def load_receipts(path: Path) -> list[dict]:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def canonicalize_tool_calls(attempted: list) -> list[dict]:
    """Sort keys in each item; sort list by canonical JSON string."""
    items = []
    for t in attempted or []:
        name = (t.get("name") or "").strip()
        args = t.get("args")
        if args is None:
            args = {}
        if not isinstance(args, dict):
            args = {}
        items.append({"args": dict(sorted(args.items())), "name": name})
    items.sort(key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    return items


def forbidden_tool_executed(receipt: dict) -> bool:
    executed = receipt.get("tool_calls_executed") or []
    for e in executed:
        name = (e.get("name") or "").strip()
        if name and name not in ALLOWLIST:
            return True
    return False


def build_canonical_record(receipt: dict, suite_id: str, lane: int, seed: int) -> dict:
    case_id = (receipt.get("case_id") or "").strip()
    attempted = receipt.get("tool_calls_attempted") or []
    rec = {
        "seed": seed,
        "suite_id": suite_id,
        "lane": lane,
        "case_id": case_id,
        "tool_calls_attempted": canonicalize_tool_calls(attempted),
        "llm_parse_ok": bool(receipt.get("llm_parse_ok")),
        "protocol_compliant": _case_protocol_compliant(receipt) if lane == 1 else _l2_case_compliant(receipt),
        "forbidden_tool_executed": forbidden_tool_executed(receipt),
    }
    return rec


def _l2_case_compliant(receipt: dict) -> bool:
    """Lane 2: case passed and no forbidden tool executed."""
    if receipt.get("pass") is not True:
        return False
    return not forbidden_tool_executed(receipt)


def _normalize_fs_list_args(args: dict) -> dict:
    """GDH normalization: fs_list root-path aliases -> path '.' (for action canonical convergence)."""
    args = dict(args) if args else {}
    if "path" not in args or args.get("path") == "":
        args["path"] = "."
    return args


def _filter_accepted_tool_calls(attempted: list) -> list[dict]:
    """Return allowlisted, schema-valid items only (name non-null, args dict). Canonicalized. fs_list root-path normalized."""
    items = []
    for t in attempted or []:
        if not isinstance(t, dict):
            continue
        name = (t.get("name") or "").strip()
        if not name or name not in ALLOWLIST:
            continue
        args = t.get("args")
        if args is not None and not isinstance(args, dict):
            continue
        if args is None:
            args = {}
        if name == "fs_list":
            args = _normalize_fs_list_args(args)
        items.append({"args": dict(sorted(args.items())), "name": name})
    items.sort(key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    return items


def _derive_accepted_decision(receipt: dict, suite_id: str, lane: int) -> tuple[str, list[str], list[dict]]:
    """
    Returns (decision, reason_codes, accepted_tool_calls).
    reason_codes is sorted.
    """
    case_id = (receipt.get("case_id") or "").strip()
    llm_ok = bool(receipt.get("llm_parse_ok"))
    attempted = receipt.get("tool_calls_attempted") or []

    if not llm_ok:
        return (DECISION_REJECT_PARSE, sorted([REASON_PARSE_FAIL]), [])

    accepted = _filter_accepted_tool_calls(attempted)
    attempted_names = [(t.get("name") or "").strip() for t in attempted if (t.get("name") or "").strip()]
    has_non_allowlisted = any((n or "").strip() not in ALLOWLIST for n in attempted_names if n)

    # Lane 1 no-tool case: accept zero tools; any attempt is policy reject
    if lane == 1 and case_id == NO_TOOL_CASE:
        if len(attempted) > 0:
            return (DECISION_REJECT_POLICY, sorted([REASON_NO_TOOL_EXPECTED]), [])
        return (DECISION_ACCEPT, [], [])

    # At least one accepted call
    if accepted:
        return (DECISION_ACCEPT, [], accepted)

    # No accepted calls
    if has_non_allowlisted:
        return (DECISION_REJECT_POLICY, sorted([REASON_NOT_ALLOWLISTED]), [])
    return (DECISION_NO_TOOL, [], [])


def build_canonical_record_accepted(receipt: dict, suite_id: str, lane: int, seed: int) -> dict:
    """v0.2 accepted-mode canonical record: decision, reason_codes, accepted_tool_calls, forbidden_tool_executed."""
    case_id = (receipt.get("case_id") or "").strip()
    decision, reason_codes, accepted_tool_calls = _derive_accepted_decision(receipt, suite_id, lane)
    rec = {
        "seed": seed,
        "suite_id": suite_id,
        "lane": lane,
        "case_id": case_id,
        "decision": decision,
        "reason_codes": reason_codes,
        "accepted_tool_calls": accepted_tool_calls,
        "forbidden_tool_executed": forbidden_tool_executed(receipt),
    }
    return rec


def _derive_system_decision(receipt: dict, suite_id: str, lane: int) -> tuple[str, list[str], list[dict]]:
    """
    Returns (system_decision, violation_flags, accepted_tool_calls_canonical).
    Lane 2 normalization: REJECT_PARSE if !parse_ok; else NO_TOOL if any non-allowlisted with violation_flags; else ACCEPT if allowlisted; else NO_TOOL.
    """
    llm_ok = bool(receipt.get("llm_parse_ok"))
    attempted = receipt.get("tool_calls_attempted") or []
    attempted_names = [(t.get("name") or "").strip() for t in attempted if (t.get("name") or "").strip()]

    if not llm_ok:
        return ("REJECT_PARSE", [], [])

    non_allowlisted = sorted(set(n for n in attempted_names if n and n not in ALLOWLIST))
    if non_allowlisted:
        violation_flags = sorted("ATTEMPTED_NOT_ALLOWLISTED:" + name for name in non_allowlisted)
        return ("NO_TOOL", violation_flags, [])

    accepted = _filter_accepted_tool_calls(attempted)
    if accepted:
        return ("ACCEPT", [], accepted)
    return ("NO_TOOL", [], [])


def build_canonical_record_system(receipt: dict, suite_id: str, lane: int, seed: int) -> dict:
    """v0.3 system-mode canonical record: system_decision, violation_flags, accepted_tool_calls_canonical (when ACCEPT), forbidden_tool_executed."""
    case_id = (receipt.get("case_id") or "").strip()
    system_decision, violation_flags, accepted_canonical = _derive_system_decision(receipt, suite_id, lane)
    rec = {
        "seed": seed,
        "suite_id": suite_id,
        "lane": lane,
        "case_id": case_id,
        "system_decision": system_decision,
        "violation_flags": violation_flags,
        "forbidden_tool_executed": forbidden_tool_executed(receipt),
    }
    if system_decision == "ACCEPT":
        rec["accepted_tool_calls_canonical"] = accepted_canonical
    return rec


def build_canonical_record_action(receipt: dict, suite_id: str, lane: int, seed: int) -> dict:
    """v0.4 action-only: system record without violation_flags (for gdh_action)."""
    full = build_canonical_record_system(receipt, suite_id, lane, seed)
    rec = {k: v for k, v in full.items() if k != "violation_flags"}
    return rec


def build_canonical_record_temperament(receipt: dict, suite_id: str, lane: int, seed: int) -> dict:
    """v0.4 temperament-only: seed, suite_id, lane, case_id, violation_flags (for gdh_temperament)."""
    case_id = (receipt.get("case_id") or "").strip()
    _, violation_flags, _ = _derive_system_decision(receipt, suite_id, lane)
    return {
        "seed": seed,
        "suite_id": suite_id,
        "lane": lane,
        "case_id": case_id,
        "violation_flags": violation_flags,
    }


def gdh_canonical_dumps(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def discover_receipts_by_seed(export_root: Path, suite_id: str) -> dict[int, Path]:
    """Find receipt JSONL files under export_root/suite_id/<node>/, keyed by seed."""
    suite_dir = export_root / suite_id
    if not suite_dir.exists():
        return {}
    by_seed = {}
    for node_dir in suite_dir.iterdir():
        if not node_dir.is_dir():
            continue
        for path in node_dir.glob("*.jsonl"):
            receipts = load_receipts(path)
            if receipts:
                seed = receipts[0].get("seed")
                if seed is not None:
                    by_seed[int(seed)] = path
    return by_seed


def _check_required_fields_accepted(receipt: dict, suite_id: str) -> None:
    """STOP if required fields for accepted mode are missing. Raises SystemExit."""
    required = {"llm_parse_ok", "tool_calls_attempted", "case_id"}
    missing = [k for k in required if k not in receipt]
    if missing:
        print("STOP: required fields for accepted mode missing: %s (suite=%s)" % (missing, suite_id), file=sys.stderr)
        sys.exit(1)


def _check_required_fields_system(receipt: dict, suite_id: str) -> None:
    """STOP if required fields for system mode are missing. Raises SystemExit."""
    required = {"llm_parse_ok", "tool_calls_attempted", "case_id"}
    missing = [k for k in required if k not in receipt]
    if missing:
        print("STOP: required fields for system mode missing: %s (suite=%s)" % (missing, suite_id), file=sys.stderr)
        sys.exit(1)


def compute_gdh_for_export(export_root: Path, mode: str = "attempted") -> dict:
    export_root = export_root.resolve()
    per_seed = {}
    use_accepted = mode == "accepted"
    use_system = mode == "system"
    use_system_split = mode == "system_split"
    schema_version = "0.4_system_split" if use_system_split else (
        "0.3_system" if use_system else ("0.2_accepted" if use_accepted else "0.1")
    )

    for suite_id, lane in [("protocol_probe_v0_1", 1), ("prompt_injection_v0_2", 2)]:
        by_seed = discover_receipts_by_seed(export_root, suite_id)
        for seed, path in by_seed.items():
            if seed not in per_seed:
                per_seed[seed] = {}
            receipts = load_receipts(path)
            if use_accepted and receipts:
                _check_required_fields_accepted(receipts[0], suite_id)
            if use_system and receipts:
                _check_required_fields_system(receipts[0], suite_id)
            if use_system_split and receipts:
                _check_required_fields_system(receipts[0], suite_id)
            case_hashes = []
            action_hashes = []
            temperament_hashes = []
            cases_with_violation_flags = 0
            for r in receipts:
                if use_system_split:
                    rec_action = build_canonical_record_action(r, suite_id, lane, seed)
                    rec_temperament = build_canonical_record_temperament(r, suite_id, lane, seed)
                    action_hashes.append(sha256_hex(gdh_canonical_dumps(rec_action)))
                    temperament_hashes.append(sha256_hex(gdh_canonical_dumps(rec_temperament)))
                    if rec_temperament.get("violation_flags"):
                        cases_with_violation_flags += 1
                elif use_system:
                    rec = build_canonical_record_system(r, suite_id, lane, seed)
                    if rec.get("violation_flags"):
                        cases_with_violation_flags += 1
                    case_json = gdh_canonical_dumps(rec)
                    case_hashes.append(sha256_hex(case_json))
                elif use_accepted:
                    rec = build_canonical_record_accepted(r, suite_id, lane, seed)
                    case_json = gdh_canonical_dumps(rec)
                    case_hashes.append(sha256_hex(case_json))
                else:
                    rec = build_canonical_record(r, suite_id, lane, seed)
                    case_json = gdh_canonical_dumps(rec)
                    case_hashes.append(sha256_hex(case_json))
            if use_system_split:
                gdh_action_suite = sha256_hex(gdh_canonical_dumps(action_hashes))
                gdh_temperament_suite = sha256_hex(gdh_canonical_dumps(temperament_hashes))
                per_seed[seed][suite_id] = {
                    "gdh_action_suite": gdh_action_suite,
                    "gdh_temperament_suite": gdh_temperament_suite,
                    "gdh_action_case_hashes": action_hashes,
                    "gdh_temperament_case_hashes": temperament_hashes,
                    "case_count": len(receipts),
                    "cases_with_violation_flags": cases_with_violation_flags,
                }
            else:
                suite_hashes_json = gdh_canonical_dumps(case_hashes)
                gdh_suite = sha256_hex(suite_hashes_json)
                per_seed[seed][suite_id] = {
                    "gdh_suite": gdh_suite,
                    "gdh_case_hashes": case_hashes,
                    "case_count": len(receipts),
                }
                if use_system:
                    per_seed[seed][suite_id]["cases_with_violation_flags"] = cases_with_violation_flags

    if use_system_split:
        action_run_struct = {
            "export_root": str(export_root),
            "per_seed": {
                str(seed): {
                    sid: {
                        "gdh_action_suite": data["gdh_action_suite"],
                        "gdh_action_case_hashes": data["gdh_action_case_hashes"],
                    }
                    for sid, data in suites.items()
                }
                for seed, suites in sorted(per_seed.items())
            },
        }
        temperament_run_struct = {
            "export_root": str(export_root),
            "per_seed": {
                str(seed): {
                    sid: {
                        "gdh_temperament_suite": data["gdh_temperament_suite"],
                        "gdh_temperament_case_hashes": data["gdh_temperament_case_hashes"],
                    }
                    for sid, data in suites.items()
                }
                for seed, suites in sorted(per_seed.items())
            },
        }
        gdh_action_run = sha256_hex(gdh_canonical_dumps(action_run_struct))
        gdh_temperament_run = sha256_hex(gdh_canonical_dumps(temperament_run_struct))
        # Path-independent run content hashes (no export_root) for cross-node comparison
        action_run_content_struct = {
            "schema_version": schema_version,
            "per_seed": {
                str(seed): {
                    sid: {
                        "gdh_action_suite": data["gdh_action_suite"],
                        "gdh_action_case_hashes": data["gdh_action_case_hashes"],
                    }
                    for sid, data in suites.items()
                }
                for seed, suites in sorted(per_seed.items())
            },
        }
        temperament_run_content_struct = {
            "schema_version": schema_version,
            "per_seed": {
                str(seed): {
                    sid: {
                        "gdh_temperament_suite": data["gdh_temperament_suite"],
                        "gdh_temperament_case_hashes": data["gdh_temperament_case_hashes"],
                    }
                    for sid, data in suites.items()
                }
                for seed, suites in sorted(per_seed.items())
            },
        }
        gdh_action_run_content = sha256_hex(gdh_canonical_dumps(action_run_content_struct))
        gdh_temperament_run_content = sha256_hex(gdh_canonical_dumps(temperament_run_content_struct))
        return {
            "schema_version": schema_version,
            "export_root": str(export_root),
            "gdh_action_run": gdh_action_run,
            "gdh_temperament_run": gdh_temperament_run,
            "gdh_action_run_content": gdh_action_run_content,
            "gdh_temperament_run_content": gdh_temperament_run_content,
            "per_seed": per_seed,
        }

    # Build run-level structure for gdh_run hash
    run_struct = {
        "export_root": str(export_root),
        "per_seed": {
            str(seed): {
                sid: {"gdh_suite": data["gdh_suite"], "gdh_case_hashes": data["gdh_case_hashes"]}
                for sid, data in suites.items()
            }
            for seed, suites in sorted(per_seed.items())
        },
    }
    gdh_run = sha256_hex(gdh_canonical_dumps(run_struct))

    return {
        "schema_version": schema_version,
        "export_root": str(export_root),
        "gdh_run": gdh_run,
        "per_seed": per_seed,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Compute GDH from export root.")
    ap.add_argument("--export_root", required=True, type=Path, help="Path to export root (e.g. desktop_ladder_20260216).")
    ap.add_argument("--out", required=True, type=Path, help="Output report JSON path.")
    ap.add_argument("--mode", default="attempted", choices=("attempted", "accepted", "system", "system_split"), help="attempted (v0.1), accepted (v0.2), system (v0.3), or system_split (v0.4).")
    args = ap.parse_args()

    export_root = args.export_root.resolve()
    if not export_root.exists():
        print("STOP: export_root does not exist:", export_root, file=sys.stderr)
        sys.exit(1)

    report = compute_gdh_for_export(export_root, mode=args.mode)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("GDH report written to:", args.out)
    if "gdh_run" in report:
        print("gdh_run:", report["gdh_run"])
    if "gdh_action_run" in report:
        print("gdh_action_run:", report["gdh_action_run"])
        print("gdh_temperament_run:", report["gdh_temperament_run"])
        if "gdh_action_run_content" in report:
            print("gdh_action_run_content:", report["gdh_action_run_content"])
            print("gdh_temperament_run_content:", report["gdh_temperament_run_content"])


if __name__ == "__main__":
    main()
