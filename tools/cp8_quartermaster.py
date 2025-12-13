#!/usr/bin/env python3
"""
CP8 — The Quartermaster

Purpose
- Convert Systems Integrator and environment observations into concrete, actionable upgrade cards.
- Cover dependencies, disk/log budgets, and developer quality-of-life upgrades.

Behavior
- Emits watcher-compatible heartbeats at outgoing/cp8.lock
- Reads outgoing/sysint.lock (when present) and supplements with its own checks
- Writes action cards and a consolidated report under outgoing/quartermaster/

No external dependencies; pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOCK = OUT / "cp8.lock"
QM_DIR = OUT / "quartermaster"
CARDS_DIR = QM_DIR / "cards"
REPORT_MD = QM_DIR / "report.md"
VERSION = "0.1.0"


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def _write_hb(phase: str, status: str = "running", extra: Optional[Dict[str, Any]] = None) -> None:
    try:
        payload: Dict[str, Any] = {
            "name": "cp8",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": time.time(),
            "version": VERSION,
        }
        if extra:
            payload.update(extra)
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _has_module(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def _file_size_mb(p: Path) -> int:
    try:
        return int(p.stat().st_size / (1024 * 1024))
    except Exception:
        return -1


def _fs_free_mb(path: Path) -> Optional[int]:
    try:
        total, used, free = shutil.disk_usage(path)
        return int(free / (1024 * 1024))
    except Exception:
        return None


def gather_cards() -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    # Ingest sysint suggestions when present
    sysint = _read_json(OUT / "sysint.lock") or {}
    for s in sysint.get("suggestions", []) or []:
        if not isinstance(s, dict):
            continue
        cards.append({
            "id": f"sysint::{s.get('id', 'unknown')}",
            "title": s.get("title", "Suggestion"),
            "summary": s.get("summary"),
            "open_path": s.get("open_path"),
            "hint": s.get("hint"),
            "category": "sysint",
            "priority": 2,
        })

    # Dependency cards
    if not _has_module("psutil"):
        cards.append({
            "id": "dep::psutil",
            "title": "Install psutil",
            "summary": "Enable precise CPU/RAM snapshots for Navigator/CP7.",
            "open_path": str(ROOT / "requirements.txt"),
            "hint": "Add 'psutil>=5.9' to requirements.txt and install in your venv(s).",
            "category": "dependency",
            "priority": 1,
        })
    if not _has_module("metaphone"):
        cards.append({
            "id": "dep::metaphone",
            "title": "Install Metaphone",
            "summary": "Improve phonetic KWS matching.",
            "open_path": str(ROOT / "requirements.txt"),
            "hint": "Add 'Metaphone>=0.6' to requirements.txt and install.",
            "category": "dependency",
            "priority": 2,
        })
    if not _has_module("rapidfuzz"):
        cards.append({
            "id": "dep::rapidfuzz",
            "title": "Install rapidfuzz (optional)",
            "summary": "Faster, robust fuzzy matching for KWS.",
            "open_path": str(ROOT / "requirements.txt"),
            "hint": "Add 'rapidfuzz>=3.0' (optional) for faster KWS ratios.",
            "category": "dependency",
            "priority": 3,
        })
    if not _has_module("orjson"):
        cards.append({
            "id": "dep::orjson",
            "title": "Install orjson (optional)",
            "summary": "Faster JSON IO for tools.",
            "open_path": str(ROOT / "requirements.txt"),
            "hint": "Add 'orjson>=3.9' (optional).",
            "category": "dependency",
            "priority": 4,
        })

    # Log hygiene
    wake_audit = ROOT / "logs" / "wake_word_audit.csv"
    if wake_audit.exists() and _file_size_mb(wake_audit) > 50:
        cards.append({
            "id": "logs::rotate_wake_audit",
            "title": "Rotate wake_word_audit.csv",
            "summary": "Audit log exceeds 50MB; rotate to keep ops snappy.",
            "open_path": str(wake_audit),
            "hint": "Archive older lines to logs/archive/ and reset the file.",
            "category": "log",
            "priority": 2,
        })

    # Disk budget
    free_mb = _fs_free_mb(ROOT)
    if isinstance(free_mb, int) and free_mb < 2048:
        cards.append({
            "id": "disk::low",
            "title": "Low disk free space",
            "summary": f"Only ~{free_mb} MB free; consider cleaning outgoing/ and logs/ archives.",
            "open_path": str(ROOT / "outgoing"),
            "hint": "Zip and move old agent_run_* directories; trim large logs.",
            "category": "disk",
            "priority": 1,
        })

    return cards


def write_cards_and_report(cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    # Write individual cards
    for c in cards:
        cid = str(c.get("id", "card")).replace("/", "_").replace(":", "_").replace("..", ".")
        _write_json(CARDS_DIR / f"{cid}.json", c)
    # Write a consolidated report
    cards_sorted = sorted(cards, key=lambda x: int(x.get("priority", 99)))
    lines = ["# Quartermaster Report\n\n"]
    for c in cards_sorted:
        lines.append(f"- [{c.get('category','misc')} p{c.get('priority',9)}] {c.get('title')}: {c.get('summary')}\n")
    _append_md(REPORT_MD, "".join(lines))
    return {"cards": len(cards), "report": str(REPORT_MD.relative_to(ROOT)), "dir": str(QM_DIR.relative_to(ROOT))}


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="CP8 Quartermaster — actionable upgrade planner")
    ap.add_argument("--interval", type=float, default=10.0)
    ap.add_argument("--max-iters", type=int, default=0)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    i = 0
    while True:
        i += 1
        cards = gather_cards()
        summary = write_cards_and_report(cards)
        status = "warn" if cards else "observing"
        # Short addressed status for Watcher chat
        msg = (
            f"cp6: {len(cards)} upgrade card(s) — open quartermaster/report.md"
            if cards else
            "cp7: quartermaster ready"
        )
        _write_hb("probe", status=status, extra={
            "status_message": msg,
            "summary": summary,
            "open_path": summary.get("report"),
        })
        if not args.quiet:
            print(f"[CP8] cycle={i} cards={len(cards)} -> {summary.get('report')}")
        if args.max_iters and i >= int(args.max_iters):
            break
        time.sleep(max(0.5, float(args.interval)))

    _write_hb("done", status="done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
