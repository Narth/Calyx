#!/usr/bin/env python3
"""
Nightly Sanitizer — keep registry/persona records tidy and canonical.

- Canonicalizes entity names (trim whitespace and trailing punctuation)
- Deduplicates entries (prefers non-empty last_tone, then higher seen_count, then non-null status)
- Enforces MAX_HISTORY_PER_ENTITY in persona_history
- Optionally fills known kind/role for standard entities
- Writes a small JSON report under outgoing/chronicles/diagnostics/
- Creates timestamped backups before modifying files

Usage:
  python -u tools/sanitize_records.py            # fixes in-place with backups
  python -u tools/sanitize_records.py --dry-run  # no writes, only prints report

Conservative and stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
STATE = ROOT / "state"
DIAG = ROOT / "_diag"

# Inputs/Outputs we sanitize
AGENTS_DIR = OUT / "agents"
REGISTRY_FILE = AGENTS_DIR / "registry.json"
PERSONA_DIR = OUT / "shared_voice"
PERSONA_FILE = PERSONA_DIR / "persona.json"
PERSONA_HISTORY_FILE = PERSONA_DIR / "persona_history.json"
CONTEXT_FILE = STATE / "comm_context.json"

# Report
CHRON = OUT / "chronicles" / "diagnostics"

MAX_HISTORY_PER_ENTITY = 100


def _read_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _backup_dir() -> Path:
    ts = time.strftime("%Y%m%d_%H%M%S")
    b = DIAG / f"sanitize_backup_{ts}"
    b.mkdir(parents=True, exist_ok=True)
    return b


def _canonical_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    return name.strip().rstrip(" .,:;")


def _name_kind_role(name: str) -> Tuple[str, str]:
    n = name.lower()
    if n.startswith("agent"):
        kind = "agent"
    elif n.startswith("cp"):
        kind = "copilot"
    elif n in ("triage", "navigator", "manifest", "scheduler", "sysint", "cbo", "svf"):
        kind = "system"
    else:
        kind = "other"
    role = ""
    if n in ("cp1", "cp2", "cp3", "cp4", "cp5"):
        role = "Honorary Copilot"
    elif n == "cp6":
        role = "The Sociologist"
    elif n == "cp7":
        role = "The Chronicler"
    elif n == "cp8":
        role = "The Quartermaster"
    elif n == "cp9":
        role = "The Auto-Tuner"
    elif n == "cp10":
        role = "The Whisperer"
    elif n == "cbo":
        role = "Bridge Overseer"
    elif n == "sysint":
        role = "Systems Integrator"
    elif n == "navigator":
        role = "Traffic Navigator"
    elif n == "manifest":
        role = "Model Manifest"
    elif n == "scheduler":
        role = "Task Scheduler"
    elif n == "triage":
        role = "Triage Orchestrator"
    return kind, role


def _prefer(a: Dict[str, Any] | None, b: Dict[str, Any] | None) -> Dict[str, Any]:
    a = a or {}
    b = b or {}
    def score(e: Dict[str, Any]) -> tuple[int, int, int]:
        return (
            1 if isinstance(e.get("last_tone"), str) and e.get("last_tone") else 0,
            int(e.get("seen_count") or 0),
            1 if e.get("status") else 0,
        )
    return a if score(a) >= score(b) else b


def sanitize_registry(reg: dict) -> tuple[dict, dict]:
    """Return (sanitized_registry, report_delta)."""
    before_keys = set()
    if isinstance(reg, dict) and isinstance(reg.get("agents"), dict):
        before_keys = set(reg["agents"].keys())
    entries = reg.get("agents", {}) if isinstance(reg, dict) else {}
    if not isinstance(entries, dict):
        entries = {}
    canon_entries: Dict[str, Dict[str, Any]] = {}
    merged_from: Dict[str, List[str]] = {}
    for k, e in list(entries.items()):
        cn = _canonical_name(k)
        if not cn:
            continue
        if cn in canon_entries:
            merged_from.setdefault(cn, []).append(k)
            canon_entries[cn] = _prefer(canon_entries.get(cn), e)
        else:
            canon_entries[cn] = e
    # Fill name/kind/role; ensure name matches key
    for k, e in list(canon_entries.items()):
        e = dict(e or {})
        e["name"] = k
        kind, role = _name_kind_role(k)
        e["kind"] = kind
        if role:  # only set when we have a known mapping
            e["role"] = role
        canon_entries[k] = e
    out = {"updated": time.time(), "agents": canon_entries}
    after_keys = set(canon_entries.keys())
    removed = sorted(before_keys - after_keys)
    added = sorted(after_keys - before_keys)
    delta = {
        "before": len(before_keys),
        "after": len(after_keys),
        "removed": removed,
        "added": added,
        "merged_from": merged_from,
    }
    return out, delta


def sanitize_persona_snapshot(ps: dict) -> tuple[dict, dict]:
    lt = ps.get("last_tone") if isinstance(ps, dict) else None
    if not isinstance(lt, dict):
        lt = {}
    before = set(lt.keys())
    canon: Dict[str, str] = {}
    merged: Dict[str, List[str]] = {}
    for k, v in lt.items():
        cn = _canonical_name(k)
        if not cn:
            continue
        if cn in canon and canon[cn] != v:
            merged.setdefault(cn, []).append(k)
        # Prefer non-empty tone
        if isinstance(v, str) and v:
            canon[cn] = v
        else:
            canon.setdefault(cn, v)
    out = {"updated": time.time(), "last_tone": canon}
    after = set(canon.keys())
    return out, {
        "before": len(before),
        "after": len(after),
        "removed": sorted(before - after),
        "added": sorted(after - before),
        "merged_from": merged,
    }


def sanitize_persona_history(ph: dict, max_hist: int = MAX_HISTORY_PER_ENTITY) -> tuple[dict, dict]:
    history = ph.get("history") if isinstance(ph, dict) else None
    counts = ph.get("counts") if isinstance(ph, dict) else None
    first_seen = ph.get("first_seen") if isinstance(ph, dict) else None
    last_seen = ph.get("last_seen") if isinstance(ph, dict) else None
    if not isinstance(history, dict):
        history = {}
    if not isinstance(counts, dict):
        counts = {}
    if not isinstance(first_seen, dict):
        first_seen = {}
    if not isinstance(last_seen, dict):
        last_seen = {}

    before_keys = set(history.keys()) | set(counts.keys()) | set(first_seen.keys()) | set(last_seen.keys())

    canon_hist: Dict[str, List[Dict[str, Any]]] = {}
    canon_counts: Dict[str, Dict[str, int]] = {}
    canon_first: Dict[str, float] = {}
    canon_last: Dict[str, float] = {}

    def _merge_events(dst: List[Dict[str, Any]], src: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        all_ev = list(dst) + list(src)
        all_ev = [e for e in all_ev if isinstance(e, dict) and isinstance(e.get("tone"), str)]
        all_ev.sort(key=lambda e: float(e.get("ts", 0.0)))
        if len(all_ev) > max_hist:
            all_ev = all_ev[-max_hist:]
        return all_ev

    # Merge history
    for k, lst in history.items():
        cn = _canonical_name(k)
        if not cn:
            continue
        if isinstance(lst, list):
            canon_hist[cn] = _merge_events(canon_hist.get(cn, []), lst)

    # Merge counts
    for k, c in counts.items():
        cn = _canonical_name(k)
        if not cn:
            continue
        src = c if isinstance(c, dict) else {}
        dst = canon_counts.get(cn, {})
        for tone, n in src.items():
            try:
                dst[tone] = int(dst.get(tone, 0)) + int(n)
            except Exception:
                continue
        canon_counts[cn] = dst

    # Merge first/last seen
    for k, ts in first_seen.items():
        cn = _canonical_name(k)
        if not cn:
            continue
        try:
            t = float(ts)
        except Exception:
            continue
        canon_first[cn] = min(canon_first.get(cn, t), t) if cn in canon_first else t

    for k, ts in last_seen.items():
        cn = _canonical_name(k)
        if not cn:
            continue
        try:
            t = float(ts)
        except Exception:
            continue
        canon_last[cn] = max(canon_last.get(cn, t), t) if cn in canon_last else t

    after_keys = set(canon_hist.keys()) | set(canon_counts.keys()) | set(canon_first.keys()) | set(canon_last.keys())
    out = {
        "updated": time.time(),
        "history": canon_hist,
        "counts": canon_counts,
        "first_seen": canon_first,
        "last_seen": canon_last,
    }
    return out, {
        "before": len(before_keys),
        "after": len(after_keys),
        "removed_only": sorted(before_keys - after_keys),
        "added_only": sorted(after_keys - before_keys),
    }


def sanitize_context(ctx: dict, snapshot_last_tone: Dict[str, str]) -> tuple[dict, dict]:
    lt = ctx.get("last_tone") if isinstance(ctx, dict) else None
    if not isinstance(lt, dict):
        lt = {}
    before = set(lt.keys())
    canon: Dict[str, str] = {}
    for k, v in lt.items():
        cn = _canonical_name(k)
        if not cn:
            continue
        # prefer tone from snapshot if available and non-empty
        sv = snapshot_last_tone.get(cn)
        if isinstance(sv, str) and sv:
            canon[cn] = sv
        elif isinstance(v, str):
            canon[cn] = v
    ctx_out = dict(ctx or {})
    ctx_out["last_tone"] = canon
    after = set(canon.keys())
    return ctx_out, {"before": len(before), "after": len(after), "removed": sorted(before - after), "added": sorted(after - before)}


def run(dry_run: bool = False) -> int:
    report: Dict[str, Any] = {"ts": time.time(), "dry_run": bool(dry_run)}

    # Load all
    reg = _read_json(REGISTRY_FILE) or {}
    ps = _read_json(PERSONA_FILE) or {}
    ph = _read_json(PERSONA_HISTORY_FILE) or {}
    ctx = _read_json(CONTEXT_FILE) or {}

    # Sanitize
    reg_out, reg_delta = sanitize_registry(reg)
    ps_out, ps_delta = sanitize_persona_snapshot(ps)
    ph_out, ph_delta = sanitize_persona_history(ph, MAX_HISTORY_PER_ENTITY)
    ctx_out, ctx_delta = sanitize_context(ctx, ps_out.get("last_tone", {}))

    report["registry"] = reg_delta
    report["persona_snapshot"] = ps_delta
    report["persona_history"] = ph_delta
    report["context"] = ctx_delta

    # Backups
    backup_dir = None
    if not dry_run:
        backup_dir = _backup_dir()
        for p, label in (
            (REGISTRY_FILE, "registry.json"),
            (PERSONA_FILE, "persona.json"),
            (PERSONA_HISTORY_FILE, "persona_history.json"),
            (CONTEXT_FILE, "comm_context.json"),
        ):
            try:
                if p.exists():
                    shutil.copy2(p, backup_dir / label)
            except Exception:
                pass

    # Writes
    if not dry_run:
        try:
            _write_json(REGISTRY_FILE, reg_out)
            _write_json(PERSONA_FILE, ps_out)
            _write_json(PERSONA_HISTORY_FILE, ph_out)
            _write_json(CONTEXT_FILE, ctx_out)
        except Exception:
            pass

    # Report
    CHRON.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    rpt = CHRON / f"sanitize_report_{ts}.json"
    try:
        _write_json(rpt, report)
    except Exception:
        pass

    # Also print a compact line
    try:
        print(json.dumps({
            "registry": {"before": reg_delta.get("before"), "after": reg_delta.get("after"), "removed": len(reg_delta.get("removed", [])), "added": len(reg_delta.get("added", []))},
            "persona_snapshot": {"before": ps_delta.get("before"), "after": ps_delta.get("after")},
            "persona_history": {"before": ph_delta.get("before"), "after": ph_delta.get("after")},
        }, ensure_ascii=False))
    except Exception:
        pass

    return 0


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Nightly Sanitizer — canonicalize & dedupe SVF records")
    ap.add_argument("--dry-run", action="store_true", help="Do not write changes; only emit report")
    args = ap.parse_args(argv)
    return run(dry_run=bool(args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
