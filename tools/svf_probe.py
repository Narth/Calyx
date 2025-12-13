#!/usr/bin/env python3
"""
SVF Probe — Shared Voice Protocol activator/monitor.

- Maintains a comm context at state/comm_context.json (participants, last tones, conversation UUID)
- Publishes a heartbeat at outgoing/svf.lock with status and policy version
- Detects participant changes from outgoing/*.lock and emits a [C:SYNC] dialogue when changes occur
- Optional: emit a sample shared log at startup (disabled by default)

Usage:
  python -u tools/svf_probe.py --interval 5
  python -u tools/svf_probe.py --interval 1 --max-iters 5 --emit-sample
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path
import os
import re
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "state"
OUT = ROOT / "outgoing"
POLICY = OUT / "policies" / "shared_voice.json"
HEARTBEAT = OUT / "svf.lock"
SHARED_LOGS = OUT / "shared_logs"
DIALOGUES = OUT / "dialogues"
AGENTS_DIR = OUT / "agents"
REGISTRY_FILE = AGENTS_DIR / "registry.json"
HONOR_ROLL_FILE = AGENTS_DIR / "honor_roll.json"

CONTEXT_FILE = STATE_DIR / "comm_context.json"
PERSONA_DIR = OUT / "shared_voice"
PERSONA_FILE = PERSONA_DIR / "persona.json"
PERSONA_HISTORY_FILE = PERSONA_DIR / "persona_history.json"
MAX_HISTORY_PER_ENTITY = 100

# Optional: load station identity from config
try:
    from asr.config import load_config  # type: ignore
    _CFG = load_config().raw
    _STATION = _CFG.get("station", {}) if isinstance(_CFG, dict) else {}
    STATION_NAME = _STATION.get("name", "Station Calyx")
    STATION_MOTTO = _STATION.get(
        "motto",
        "Station Calyx is the flag we fly; autonomy is the dream we share.",
    )
except Exception:
    STATION_NAME = "Station Calyx"
    STATION_MOTTO = "Station Calyx is the flag we fly; autonomy is the dream we share."


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


def _get_policy() -> dict:
    d = _read_json(POLICY) or {}
    # defaults if policy missing
    return {
        "policy": d.get("policy", "shared_voice"),
        "active": bool(d.get("active", True)),
        "version": d.get("version", "1.0"),
        "effective_date": d.get("effective_date", "2025-10-22"),
        "requirements": d.get("requirements", {}),
        "canonical_path": d.get("canonical_path", "Codex/COMM_PROTOCOL_SHARED_VOICE.md"),
    }


def _discover_participants() -> List[str]:
    names: List[str] = []
    try:
        for p in OUT.glob("*.lock"):
            nm = p.stem
            # Exclude our own lock unless we want to list SVF as a participant
            if nm:
                names.append(nm)
    except Exception:
        pass
    names = sorted(set(names))
    return names


def _load_context() -> dict:
    ctx = _read_json(CONTEXT_FILE) or {}
    if not isinstance(ctx, dict):
        ctx = {}
    if "conversation_uuid" not in ctx:
        ctx["conversation_uuid"] = uuid.uuid4().hex
    if "participants" not in ctx or not isinstance(ctx.get("participants"), list):
        ctx["participants"] = []
    if "last_tone" not in ctx or not isinstance(ctx.get("last_tone"), dict):
        ctx["last_tone"] = {}
    return ctx


def _emit_heartbeat(policy: dict, participants: List[str]) -> None:
    hb = {
        "name": "svf",
        "pid": os.getpid() if hasattr(__import__('os'), 'getpid') else None,  # type: ignore
        "ts": time.time(),
        "status": "monitoring" if policy.get("active") else "idle",
        "status_message": "SVF active" if policy.get("active") else "SVF inactive",
        "policy_version": policy.get("version"),
        "writer": "svf_probe",
        "participants": participants,
        "canonical": policy.get("canonical_path"),
        "station": {"name": STATION_NAME, "motto": STATION_MOTTO},
    }
    _write_json(HEARTBEAT, hb)


def _emit_sync_dialogue(ctx: dict, participants: List[str]) -> None:
    try:
        ts = int(time.time())
        DIALOGUES.mkdir(parents=True, exist_ok=True)
        path = DIALOGUES / f"svf_sync_{ts}.md"
        lines = []
        lines.append("[C:SYNC] — SVF Participant Sync")
        lines.append("")
        for nm in participants:
            # Pick a default tone hint if unknown
            tone = ctx.get("last_tone", {}).get(nm)
            if not isinstance(tone, str) or not tone:
                if nm.lower().startswith("agent"):
                    tone = "Operational"
                elif nm.lower() == "triage":
                    tone = "Diagnostic"
                elif nm.lower().startswith("cp"):
                    # Map known CP roles; fall back to Copilot
                    low = nm.lower()
                    if low == "cp6":
                        tone = "Sociologist"
                    elif low == "cp7":
                        tone = "Chronicler"
                    elif low == "cp8":
                        tone = "Quartermaster"
                    elif low == "cp9":
                        tone = "Auto-Tuner"
                    elif low == "cp10":
                        tone = "Whisperer"
                    else:
                        tone = "Copilot"
                elif nm.lower() == "cbo":
                    tone = "Overseer"
                else:
                    tone = "Notice"
            lines.append(f"[{nm} • {tone}]: \"Joined SVF session {ctx.get('conversation_uuid')}\"")
        lines.append("")
        lines.append("Generated under Shared Voice Protocol v1.0")
        path.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        pass


def _emit_sample_report(ctx: dict, participants: List[str]) -> None:
    try:
        ts = int(time.time())
        SHARED_LOGS.mkdir(parents=True, exist_ok=True)
        path = SHARED_LOGS / f"svf_probe_report_{ts}.md"
        lines = []
        lines.append("[C:REPORT] — SVF Probe Report")
        lines.append("")
        for nm in participants:
            tone = ctx.get("last_tone", {}).get(nm, "Notice")
            lines.append(f"[{nm} • {tone}]: \"Presence confirmed in SVF probe.\"")
        lines.append("")
        lines.append("Generated under Shared Voice Protocol v1.0")
        path.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        pass


def _scan_recent_files(dir_path: Path, pattern: str = "*.md", limit: int = 10) -> List[Path]:
    files: List[Path] = []
    try:
        all_files = sorted(dir_path.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        files = all_files[: max(1, int(limit))]
    except Exception:
        files = []
    return files


_TONE_RE = re.compile(r"^\[(?P<entity>[^\]•]+)\s*•\s*(?P<tone>[^\]]+)\]", re.UNICODE)


def _canonical_name(name: str) -> str:
    """Return a canonical entity name (trim whitespace and trailing punctuation)."""
    if not isinstance(name, str):
        return ""
    return name.strip().rstrip(" .,:;")


def _learn_tones(ctx: dict) -> bool:
    """Parse recent shared outputs to learn [Entity • Tone] mappings.

    Returns True when the context was updated.
    """
    updated = False
    last_tone = ctx.get("last_tone") if isinstance(ctx.get("last_tone"), dict) else {}
    if not isinstance(last_tone, dict):
        last_tone = {}
    # Track updates for history
    events: List[Dict[str, Any]] = []
    # Directories to scan
    targets = [
        OUT / "shared_logs",
        OUT / "dialogues",
        OUT / "overseer_reports",
    ]
    for d in targets:
        for p in _scan_recent_files(d, "*.md", limit=8):
            try:
                # Read only the tail to keep it light
                data = p.read_text(encoding="utf-8", errors="ignore")
                tail = data.splitlines()[-200:]
                for line in tail:
                    m = _TONE_RE.match(line.strip())
                    if not m:
                        continue
                    ent = m.group("entity").strip()
                    tone = m.group("tone").strip()
                    if ent and tone and last_tone.get(ent) != tone:
                        last_tone[ent] = tone
                        updated = True
                        try:
                            rel_src = str(p.relative_to(ROOT))
                        except Exception:
                            rel_src = str(p)
                        events.append({"entity": ent, "tone": tone, "ts": time.time(), "src": rel_src})
            except Exception:
                continue
    if updated:
        ctx["last_tone"] = last_tone
        # Write an aggregate persona view
        try:
            PERSONA_DIR.mkdir(parents=True, exist_ok=True)
            PERSONA_FILE.write_text(json.dumps({
                "updated": time.time(),
                "last_tone": last_tone,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        # Update rolling history
        try:
            hist: Dict[str, Any] = {}
            if PERSONA_HISTORY_FILE.exists():
                try:
                    hist = json.loads(PERSONA_HISTORY_FILE.read_text(encoding="utf-8"))
                    if not isinstance(hist, dict):
                        hist = {}
                except Exception:
                    hist = {}
            history = hist.get("history", {})
            if not isinstance(history, dict):
                history = {}
            counts = hist.get("counts", {})
            if not isinstance(counts, dict):
                counts = {}
            first_seen = hist.get("first_seen", {})
            if not isinstance(first_seen, dict):
                first_seen = {}
            last_seen = hist.get("last_seen", {})
            if not isinstance(last_seen, dict):
                last_seen = {}

            for ev in events:
                ent = ev.get("entity")
                tone = ev.get("tone")
                ts = ev.get("ts")
                if not isinstance(ent, str) or not isinstance(tone, str) or not isinstance(ts, (int, float)):
                    continue
                # Append event to per-entity list
                lst = history.get(ent)
                if not isinstance(lst, list):
                    lst = []
                lst.append({"tone": tone, "ts": ts, "src": ev.get("src")})
                # Trim to max
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

            hist_out = {
                "updated": time.time(),
                "history": history,
                "counts": counts,
                "first_seen": first_seen,
                "last_seen": last_seen,
            }
            PERSONA_HISTORY_FILE.write_text(json.dumps(hist_out, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    return updated


def _name_kind_role(name: str) -> tuple[str, str]:
    n = name.lower()
    # kind
    if n.startswith("agent"):
        kind = "agent"
    elif n.startswith("cp"):
        kind = "copilot"
    elif n in ("triage", "navigator", "manifest", "scheduler", "sysint", "cbo", "svf"):
        kind = "system"
    else:
        kind = "other"
    # role mapping
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


def _update_agents_registry(ctx: dict, participants: List[str]) -> None:
    now = time.time()
    try:
        AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        reg = {}
        if REGISTRY_FILE.exists():
            try:
                reg = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
                if not isinstance(reg, dict):
                    reg = {}
            except Exception:
                reg = {}
        entries = reg.get("agents", {})
        if not isinstance(entries, dict):
            entries = {}
        # Canonicalize existing entries and deduplicate
        canon_entries: Dict[str, dict] = {}
        def _prefer(a: dict | None, b: dict | None) -> dict:
            # Prefer non-null last_tone, then higher seen_count, then non-null status
            a = a or {}
            b = b or {}
            def score(e: dict) -> tuple[int, int, int]:
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
        last_tone = ctx.get("last_tone") if isinstance(ctx.get("last_tone"), dict) else {}
        # Canonicalize participant names
        canon_participants = sorted(set(_canonical_name(nm) for nm in participants if _canonical_name(nm)))
        for nm in canon_participants:
            # read heartbeat for status/phase
            hb = {}
            try:
                hb_path = OUT / f"{nm}.lock"
                hb = _read_json(hb_path) or {}
            except Exception:
                hb = {}
            e = entries.get(nm)
            if not isinstance(e, dict):
                e = {}
            first_seen = e.get("first_seen") if isinstance(e.get("first_seen"), (int, float)) else None
            if first_seen is None:
                first_seen = now
            kind, role = _name_kind_role(nm)
            e.update({
                "name": nm,
                "kind": kind,
                "role": role,
                "first_seen": first_seen,
                "last_seen": now,
                "last_tone": last_tone.get(nm),
                "status": hb.get("status"),
                "phase": hb.get("phase"),
                "pid": hb.get("pid"),
            })
            # increment seen count
            cnt = e.get("seen_count") if isinstance(e.get("seen_count"), int) else 0
            e["seen_count"] = int(cnt) + 1
            entries[nm] = e
        out = {
            "updated": now,
            "station": {"name": STATION_NAME, "motto": STATION_MOTTO},
            "agents": entries,
        }
        REGISTRY_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _write_honor_roll() -> None:
    try:
        AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        entries = [
            {"name": f"cp{i}", "role": "Honorary Copilot", "note": "Legacy copilot; artifacts limited"}
            for i in range(1, 6)
        ]
        HONOR_ROLL_FILE.write_text(json.dumps({"updated": time.time(), "entries": entries}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="SVF Probe — keep Shared Voice comms active")
    ap.add_argument("--interval", type=float, default=5.0, help="Seconds between updates")
    ap.add_argument("--max-iters", type=int, default=0, help="Stop after N iterations (0 = run forever)")
    ap.add_argument("--emit-sample", action="store_true", help="Emit a sample shared report on startup")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    # Ensure dirs
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    ctx = _load_context()
    policy = _get_policy()
    last_participants: List[str] = []

    # Optional sample on startup
    participants = _discover_participants()
    _emit_heartbeat(policy, participants)
    if args.emit_sample:
        _emit_sample_report(ctx, participants)

    it = 0
    while True:
        it += 1
        # Ensure honor roll exists (idempotent small write)
        try:
            _write_honor_roll()
        except Exception:
            pass
        participants = _discover_participants()
        # Heartbeat and optional sync on change
        _emit_heartbeat(policy, participants)
        # Learn tones from recent shared outputs
        try:
            if _learn_tones(ctx):
                _write_json(CONTEXT_FILE, ctx)
        except Exception:
            pass
        # Update agents registry for robust recollection
        try:
            _update_agents_registry(ctx, participants)
        except Exception:
            pass
        if participants != last_participants:
            _emit_sync_dialogue(ctx, participants)
            last_participants = participants
            # update context participants
            ctx["participants"] = participants
            _write_json(CONTEXT_FILE, ctx)
        # Loop control
        if args.max_iters and it >= args.max_iters:
            break
        try:
            time.sleep(max(0.05, float(args.interval)))
        except Exception:
            time.sleep(1.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
