#!/usr/bin/env python3
"""
SVF Backfill — populate agents registry and persona history from existing artifacts.

Scans lightweight, local sources to reconstruct:
- outgoing/agents/registry.json (first/last seen, seen_count, role/kind, last_tone, status/phase/pid)
- outgoing/shared_voice/persona_history.json (rolling events per entity with counts)
- outgoing/shared_voice/persona.json (latest tones snapshot)
- state/comm_context.json (last_tone)

Sources (read-only):
- outgoing/*.lock (current statuses)
- outgoing/shared_logs/*.md, outgoing/dialogues/*.md, outgoing/overseer_reports/**/*.md (tone lines)
- logs/EVOLUTION.md (roles observed)
- outgoing/evolution/*.txt (optional hints)

Usage:
  python -u tools/svf_backfill.py --max-files 200
  python -u tools/svf_backfill.py --dry-run

This is conservative and stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOGS = ROOT / "logs"
STATE = ROOT / "state"

# Inputs
DIALOGUES = OUT / "dialogues"
SHARED_LOGS = OUT / "shared_logs"
OVERSEER = OUT / "overseer_reports"
EVOLUTION_IDX = LOGS / "EVOLUTION.md"
EVOLUTION_DIR = OUT / "evolution"

# Outputs
AGENTS_DIR = OUT / "agents"
REGISTRY_FILE = AGENTS_DIR / "registry.json"
PERSONA_DIR = OUT / "shared_voice"
PERSONA_FILE = PERSONA_DIR / "persona.json"
PERSONA_HISTORY_FILE = PERSONA_DIR / "persona_history.json"
CONTEXT_FILE = STATE / "comm_context.json"

# Limits
MAX_HISTORY_PER_ENTITY = 100

_TONE_RE = re.compile(r"^\[(?P<entity>[^\]•]+)\s*•\s*(?P<tone>[^\]]+)\]", re.UNICODE)


def _canonical_name(name: str) -> str:
    """Return a canonical entity name (trim whitespace and trailing punctuation)."""
    if not isinstance(name, str):
        return ""
    return name.strip().rstrip(" .,:;")


def _read_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(p: Path, data: dict) -> None:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


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


def _scan_md_files(paths: Iterable[Path], max_files: int) -> List[Tuple[Path, float, List[str]]]:
    results: List[Tuple[Path, float, List[str]]] = []
    files: List[Path] = []
    for p in paths:
        try:
            for f in p.rglob("*.md") if p.is_dir() else [p]:
                files.append(f)
        except Exception:
            continue
    # Sort by mtime desc and cap
    try:
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    except Exception:
        pass
    files = files[: max(1, int(max_files))]
    for f in files:
        try:
            data = f.read_text(encoding="utf-8", errors="ignore").splitlines()
            results.append((f, f.stat().st_mtime, data))
        except Exception:
            continue
    return results


def _collect_tone_events(max_files: int = 200) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    sources = [DIALOGUES, SHARED_LOGS, OVERSEER]
    for f, mtime, lines in _scan_md_files(sources, max_files=max_files):
        for line in lines[-500:]:  # tail to reduce noise
            m = _TONE_RE.match(line.strip())
            if not m:
                continue
            ent = m.group("entity").strip()
            tone = m.group("tone").strip()
            if not ent or not tone:
                continue
            try:
                rel = str(f.relative_to(ROOT))
            except Exception:
                rel = str(f)
            events.append({"entity": ent, "tone": tone, "ts": float(mtime), "src": rel})
    return events


def _discover_locks() -> Dict[str, Dict[str, Any]]:
    locks: Dict[str, Dict[str, Any]] = {}
    if not OUT.exists():
        return locks
    for p in OUT.glob("*.lock"):
        try:
            d = _read_json(p) or {}
            nm = d.get("name") or p.stem
            nm = _canonical_name(nm)
            locks[nm] = {**d, "_path": str(p.relative_to(ROOT))}
        except Exception:
            continue
    return locks


def _parse_evolution_roles() -> Dict[str, List[str]]:
    roles: Dict[str, List[str]] = {}
    if not EVOLUTION_IDX.exists():
        return roles
    try:
        data = EVOLUTION_IDX.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return roles
    cur_date: Optional[str] = None
    for line in data:
        if line.strip().startswith("- 20") and "—" in line:
            cur_date = line.strip().split(" ")[1] if line.strip().startswith("-") else None
            continue
        if line.strip().lower().startswith("- roles observed:"):
            try:
                # Extract comma-separated items after ':'
                part = line.split(":", 1)[1]
                items = [x.strip() for x in part.split(",")]
                tokens: List[str] = []
                for it in items:
                    tok = it.split("(")[0].strip()  # drop parentheses suffixes
                    tok = tok.lower().replace(" ", "_")
                    tok = tok.replace("bridge (cbo)", "cbo").replace("bridge", "cbo") if "bridge" in tok else tok
                    # normalize cp tokens like cp6
                    tokens.append(tok)
                if cur_date:
                    roles[cur_date] = tokens
            except Exception:
                continue
    return roles


def _merge_persona(events: List[Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, Any]]:
    last_tone: Dict[str, str] = {}
    history: Dict[str, List[Dict[str, Any]]] = {}
    counts: Dict[str, Dict[str, int]] = {}
    first_seen: Dict[str, float] = {}
    last_seen: Dict[str, float] = {}

    # Load existing history to avoid clobber
    existing = _read_json(PERSONA_HISTORY_FILE) or {}
    if isinstance(existing, dict):
        history = existing.get("history", {}) if isinstance(existing.get("history"), dict) else {}
        counts = existing.get("counts", {}) if isinstance(existing.get("counts"), dict) else {}
        first_seen = existing.get("first_seen", {}) if isinstance(existing.get("first_seen"), dict) else {}
        last_seen = existing.get("last_seen", {}) if isinstance(existing.get("last_seen"), dict) else {}

    for ev in sorted(events, key=lambda e: e.get("ts", 0.0)):
        ent = str(ev.get("entity", "")).strip()
        tone = str(ev.get("tone", "")).strip()
        ts = float(ev.get("ts", 0.0))
        src = ev.get("src")
        if not ent or not tone or ts <= 0:
            continue
        # Update last_tone snapshot
        last_tone[ent] = tone
        # Append to history with cap
        lst = history.get(ent)
        if not isinstance(lst, list):
            lst = []
        lst.append({"tone": tone, "ts": ts, "src": src})
        if len(lst) > MAX_HISTORY_PER_ENTITY:
            lst = lst[-MAX_HISTORY_PER_ENTITY:]
        history[ent] = lst
        # Update counts
        c = counts.get(ent)
        if not isinstance(c, dict):
            c = {}
        c[tone] = int(c.get(tone, 0)) + 1
        counts[ent] = c
        # Update first/last seen
        if ent not in first_seen:
            first_seen[ent] = ts
        last_seen[ent] = ts

    return last_tone, {
        "updated": time.time(),
        "history": history,
        "counts": counts,
        "first_seen": first_seen,
        "last_seen": last_seen,
    }


def _update_registry(locks: Dict[str, Dict[str, Any]], persona_snapshot: Dict[str, str], roles_idx: Dict[str, List[str]]) -> Dict[str, Any]:
    now = time.time()
    registry = _read_json(REGISTRY_FILE) or {}
    if not isinstance(registry, dict):
        registry = {}
    entries = registry.get("agents", {}) if isinstance(registry.get("agents"), dict) else {}

    # Canonicalize existing entries and dedupe
    canon_entries: Dict[str, Dict[str, Any]] = {}
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
    for k, e in list(entries.items()):
        cn = _canonical_name(k)
        if not cn:
            continue
        canon_entries[cn] = _prefer(canon_entries.get(cn), e)
    entries = canon_entries

    # Compose a candidate set of entities
    # Canonicalize locks and snapshot keys
    locks = { _canonical_name(k): v for k, v in (locks or {}).items() if _canonical_name(k) }
    persona_snapshot = { _canonical_name(k): v for k, v in (persona_snapshot or {}).items() if _canonical_name(k) }
    candidates = set(entries.keys()) | set(locks.keys()) | set(persona_snapshot.keys())
    # Add entities mentioned in roles_idx tokens (flatten)
    for _, toks in (roles_idx or {}).items():
        for t in toks:
            # strip extra descriptors
            nm = _canonical_name(t)
            # normalize known names
            nm = nm.replace("bridge (cbo)", "cbo").replace("bridge", "cbo").replace("watcher_toke", "watcher_token")
            candidates.add(nm)

    for nm in sorted(candidates):
        if not nm:
            continue
        e = entries.get(nm)
        if not isinstance(e, dict):
            e = {}
        first_seen = e.get("first_seen") if isinstance(e.get("first_seen"), (int, float)) else None
        if first_seen is None:
            # try to seed from persona history first_seen
            hist = _read_json(PERSONA_HISTORY_FILE) or {}
            try:
                fs = (hist.get("first_seen") or {}).get(nm)
            except Exception:
                fs = None
            if isinstance(fs, (int, float)):
                first_seen = fs
            else:
                first_seen = now
        kind, role = _name_kind_role(nm)
        hb = locks.get(nm) or {}
        e.update({
            "name": nm,
            "kind": kind,
            "role": role,
            "first_seen": first_seen,
            "last_seen": now,
            "seen_count": int(e.get("seen_count", 0)) + 1,
            "last_tone": persona_snapshot.get(nm),
            "status": hb.get("status"),
            "phase": hb.get("phase"),
            "pid": hb.get("pid"),
        })
        entries[nm] = e

    return {"updated": now, "agents": entries}


def run_backfill(max_files: int, dry_run: bool) -> int:
    # Gather tone events
    events = _collect_tone_events(max_files=max_files)
    # Merge into persona
    last_tone, p_hist = _merge_persona(events)
    # Write persona outputs (unless dry-run)
    if not dry_run:
        _write_json(PERSONA_HISTORY_FILE, p_hist)
        _write_json(PERSONA_FILE, {"updated": time.time(), "last_tone": last_tone})
        # Update comm_context for live users
        ctx = _read_json(CONTEXT_FILE) or {}
        if not isinstance(ctx, dict):
            ctx = {}
        ctx["last_tone"] = last_tone
        _write_json(CONTEXT_FILE, ctx)

    # Locks + roles for registry
    locks = _discover_locks()
    roles_idx = _parse_evolution_roles()
    registry = _update_registry(locks, last_tone, roles_idx)
    if not dry_run:
        _write_json(REGISTRY_FILE, registry)

    # Done
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="SVF Backfill — rebuild registry/persona from existing artifacts")
    ap.add_argument("--max-files", type=int, default=200, help="Max markdown files to scan across sources (default 200)")
    ap.add_argument("--dry-run", action="store_true", help="Do not write outputs; only compute")
    args = ap.parse_args(argv)
    return run_backfill(max_files=max(1, args.max_files), dry_run=bool(args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
