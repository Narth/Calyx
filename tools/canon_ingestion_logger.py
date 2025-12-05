#!/usr/bin/env python3
"""
Canon Ingestion Logger

Appends ingestion events to logs/canon_ingestion_log.jsonl.
Intended for Quiet Maintain reflections only; no behavioral changes are applied.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "logs" / "canon_ingestion_log.jsonl"


def log_event(doc_path: Path, classification: str, notes: str = "") -> None:
    ts = datetime.now(timezone.utc).isoformat()
    entry: Dict[str, Any] = {
        "timestamp": ts,
        "document": str(doc_path),
        "classification": classification,
        "notes": notes,
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Append Canon ingestion event to log")
    ap.add_argument("document", type=str, help="Path to document ingested")
    ap.add_argument("--classification", type=str, required=True, help="Classification label for the document")
    ap.add_argument("--notes", type=str, default="", help="Optional notes/reflection")
    args = ap.parse_args(argv)

    doc = Path(args.document)
    log_event(doc, args.classification, args.notes)
    print(f"[OK] Logged ingestion for {doc} -> {LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
