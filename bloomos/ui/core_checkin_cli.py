"""
BloomOS Core Check-In CLI (Safe Mode, reflection-only).

Usage examples:
  python -m bloomos.ui.core_checkin_cli --dry-run
  python -m bloomos.ui.core_checkin_cli --core-name TEST --structural-id CORE:TEST
"""

from __future__ import annotations

import argparse
import json
from typing import Dict, Any

from bloomos.core.checkin import run_core_checkin


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BloomOS Core Check-In (Safe Mode)")
    parser.add_argument("--core-name", dest="core_name", help="Core name", default=None)
    parser.add_argument("--structural-id", dest="structural_id", help="Structural ID", default=None)
    parser.add_argument("--lineage-pointer", dest="lineage_pointer", help="Lineage pointer", default=None)
    parser.add_argument("--metadata", dest="metadata", help="Optional metadata JSON", default=None)
    parser.add_argument("--dry-run", action="store_true", help="No special behavior; retained for compatibility")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    envelope: Dict[str, Any] = {}
    if args.core_name:
        envelope["name"] = args.core_name
    if args.structural_id:
        envelope["structural_id"] = args.structural_id
    if args.lineage_pointer:
        envelope["lineage_pointer"] = args.lineage_pointer
    if args.metadata:
        try:
            envelope["metadata"] = json.loads(args.metadata)
        except Exception:
            envelope["metadata"] = {"raw": args.metadata}

    snapshot = run_core_checkin(envelope if envelope else None)
    print(json.dumps(snapshot, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
