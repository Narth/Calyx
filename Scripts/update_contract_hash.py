#!/usr/bin/env python3
"""Update contract_sha256 in CALYX_CONTRACT.yaml after legitimate edits.
WO_GOVERNANCE_CONTRACT_INTAKE_PARITY: Run this after modifying the contract.
Usage: python Scripts/update_contract_hash.py [--contract path]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from calyx.kernel.contract import _canonical_contract_hash, _load_yaml


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=None, help="Path to CALYX_CONTRACT.yaml")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    contract_path = Path(args.contract) if args.contract else repo_root / "CALYX_CONTRACT.yaml"
    if not contract_path.exists():
        print(f"Contract not found: {contract_path}", flush=True)
        return 1
    data = _load_yaml(contract_path)
    new_hash = _canonical_contract_hash(data)
    text = contract_path.read_text(encoding="utf-8")
    # Replace contract_sha256 line
    new_line = f'contract_sha256: "{new_hash}"  # Canonical hash (excludes this field)\n'
    if "contract_sha256:" in text:
        text = re.sub(r'contract_sha256:\s*[^\n]*\n', new_line, text, count=1)
    else:
        print("Could not find contract_sha256 line", flush=True)
        return 1
    contract_path.write_text(text, encoding="utf-8")
    print(f"Updated contract_sha256 to {new_hash[:16]}...", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
