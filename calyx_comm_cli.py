#!/usr/bin/env python3
"""
calyx_comm_cli.py

Architect-facing CLI for text communication with Station Calyx / CBO
via file-based chat messages.

Governance alignment:
- No execution of Station code.
- No subprocesses.
- No network.
- Purely writes/reads structured message files.
- Human-run only (Architect starts the CLI manually).
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


CANONICAL_POLICY_HASH = "4E4924361545468CB42387F38C946A3C3E802BD1494868C378FBE7DBB5FFD6D7"
WIZARD_VERSION = "wizard_v0.1"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def append_cli_audit(station_root: Path, event: Dict) -> None:
    """
    Best-effort local audit trail for console decisions.
    Stores only hashes/previews (not full message bodies).
    """
    try:
        ts = utc_now_iso()
        date = ts[:10].replace("-", "")
        log_dir = station_root / "logs" / "cli_comm"
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"calyx_comm_cli_audit_{date}.jsonl"
        event = dict(event)
        event.setdefault("ts", ts)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        return


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def make_message_id() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # YYYYMMDD_HHMMSS_mmm


def resolve_station_root(args_root: Optional[str]) -> Path:
    if args_root:
        root = Path(args_root).expanduser().resolve()
    else:
        env_root = os.environ.get("CALYX_STATION_ROOT")
        if env_root:
            root = Path(env_root).expanduser().resolve()
        else:
            # Usability default: infer station root from the script location.
            root = Path(__file__).resolve().parent
            print(f"[Calyx CLI] Note: CALYX_STATION_ROOT not set; defaulting to script directory: {root}")

    if not root.exists():
        print(f"[Calyx CLI] Error: Station root does not exist: {root}")
        sys.exit(1)
    return root


def get_chat_paths(station_root: Path) -> Tuple[Path, Path]:
    """Return (incoming_architect_chat_dir, outgoing_cbo_chat_dir)."""
    incoming_architect = station_root / "incoming" / "Architect" / "chat"
    outgoing_cbo = station_root / "outgoing" / "CBO" / "chat"

    incoming_architect.mkdir(parents=True, exist_ok=True)
    outgoing_cbo.mkdir(parents=True, exist_ok=True)

    return incoming_architect, outgoing_cbo


def write_message(
    incoming_dir: Path,
    session_id: str,
    text: str,
    role: str = "architect",
    metadata_extra: Optional[Dict] = None,
) -> Path:
    msg_id = make_message_id()
    ts = utc_now_iso()
    msg = {
        "session_id": session_id,
        "message_id": msg_id,
        "role": role,
        "timestamp": ts,
        "text": text,
        "metadata": {
            "channel": "cli",
            "origin": "calyx_comm_cli",
            "canonical_policy_hash": CANONICAL_POLICY_HASH,
        },
    }
    if metadata_extra:
        msg["metadata"].update(metadata_extra)

    filename = f"{ts.replace(':', '').replace('-', '').replace('.', '')}_{role}_{msg_id}.json"
    path = incoming_dir / filename
    path.write_text(json.dumps(msg, indent=2, ensure_ascii=False), encoding="utf-8")

    return path


def classify_intent_from_text(text: str) -> Tuple[str, float, List[str]]:
    """
    Heuristic intent classifier for the console wizard.
    Returns (label, confidence, reasons).

    Labels: reflect | advise | propose | review
    """
    t = (text or "").strip().lower()
    if not t:
        return ("advise", 0.2, ["empty_text"])

    reasons: list[str] = []
    scores = {"reflect": 0.0, "advise": 0.0, "propose": 0.0, "review": 0.0}

    def bump(label: str, amt: float, reason: str) -> None:
        scores[label] += amt
        reasons.append(reason)

    if any(k in t for k in ["i feel", "i'm feeling", "im feeling", "reflect", "reflection", "processing", "journal"]):
        bump("reflect", 0.8, "reflect_keywords")

    if any(k in t for k in ["should i", "what should", "recommend", "advice", "advise", "how do i", "help me", "suggest"]):
        bump("advise", 0.7, "advice_keywords")

    if any(k in t for k in ["patch", "diff", "implement", "refactor", "fix", "change", "add", "remove", "update", "deploy"]):
        bump("propose", 0.7, "change_keywords")

    if any(k in t for k in ["review", "verdict", "cp14", "cp18", "approve", "rejected", "under_review", "inbox"]):
        bump("review", 0.7, "review_keywords")

    if t.startswith(("review ", "check ", "inbox ")):
        bump("review", 0.6, "leading_review_verb")
    if t.startswith(("propose ", "implement ", "change ", "deploy ", "patch ")):
        bump("propose", 0.6, "leading_change_verb")

    label, score = max(scores.items(), key=lambda kv: kv[1])
    confidence = min(0.99, 0.35 + score)
    return (label, confidence, reasons[:6])


def prompt_wizard_action(default_action: str, confidence: float) -> Optional[str]:
    """
    Return chosen action or None to cancel.
    """
    prompt = (
        f"[Wizard] Detected: {default_action.upper()} (confidence {confidence:.2f}). "
        "Enter=accept, r=reflect, a=advise, p=propose, v=review, q=cancel: "
    )
    try:
        resp = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return None

    if resp in ("", "y", "yes"):
        return default_action
    if resp in ("q", "quit", "cancel", "c"):
        return None

    mapping = {"r": "reflect", "a": "advise", "p": "propose", "v": "review"}
    return mapping.get(resp)


def try_extract_intent_id(text: str) -> Optional[str]:
    t = (text or "").strip()
    if not t:
        return None

    for token in t.replace(",", " ").split():
        if token.upper().startswith("INT-") and len(token) >= 6:
            return token

    import re as _re
    m = _re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", t)
    return m.group(0) if m else None


def run_local_review(intent_id_or_path: str) -> Tuple[bool, str]:
    """
    Run the local Phase-1 review orchestrator for an intent JSON file.
    Returns (ok, status_or_error).
    """
    p = Path(intent_id_or_path)
    if not p.suffix:
        candidate = Path("outgoing") / "proposals" / intent_id_or_path / "intent.json"
        if candidate.exists():
            p = candidate
    if not p.exists():
        return (False, f"intent file not found: {p}")

    try:
        from tools.review_orchestrator import route_for_review

        status = route_for_review(str(p))
        return (True, status)
    except Exception as e:
        return (False, f"{e}")


def load_messages_from_dir(
    dir_path: Path,
    since_ts: Optional[float] = None,
    *,
    session_id: Optional[str] = None,
) -> List[Tuple[float, Path, Dict]]:
    """
    Load JSON messages from dir_path.
    Returns list of (mtime, path, json_data), optionally filtered by mtime > since_ts.
    """
    messages: List[Tuple[float, Path, Dict]] = []
    if not dir_path.exists():
        return messages

    for p in sorted(dir_path.glob("*.json")):
        try:
            mtime = p.stat().st_mtime
            if since_ts is not None and mtime <= since_ts:
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
            if session_id and data.get("session_id") != session_id:
                continue
            messages.append((mtime, p, data))
        except Exception as e:
            print(f"[Calyx CLI] Warning: Failed to read message {p.name}: {e}", file=sys.stderr)
            continue

    return messages


def print_cbo_messages(messages: List[Tuple[float, Path, Dict]]) -> None:
    if not messages:
        print("[Calyx CLI] No new messages from CBO.")
        return

    print("\n[Calyx CLI] --- New messages from CBO ---")
    for _, path, data in messages:
        ts = data.get("timestamp", "?")
        session_id = data.get("session_id", "?")
        role = data.get("role", "cbo")
        text = data.get("text", "")
        print(f"\n[{ts}] ({session_id}) {role.upper()} said via {path.name}:")
        print(text)
    print("[Calyx CLI] --- End of messages ---\n")


def cmd_send(args: argparse.Namespace) -> None:
    station_root = resolve_station_root(args.root)
    incoming_architect, _ = get_chat_paths(station_root)

    session_id = args.session or f"{utc_now_iso()}_oneshot"
    if getattr(args, "file", None):
        text = Path(args.file).read_text(encoding="utf-8")
    else:
        text = " ".join(args.message) if args.message else ""
    if not text:
        print("[Calyx CLI] Error: No message text provided.")
        sys.exit(1)

    path = write_message(incoming_architect, session_id, text)
    print(f"[Calyx CLI] Sent message to Station at {path}")


def cmd_inbox(args: argparse.Namespace) -> None:
    station_root = resolve_station_root(args.root)
    _, outgoing_cbo = get_chat_paths(station_root)

    messages = load_messages_from_dir(outgoing_cbo, session_id=args.session)
    print_cbo_messages(messages)


def cmd_smoke(args: argparse.Namespace) -> None:
    """
    Non-interactive sanity check:
    - Resolve station root
    - Ensure chat directories exist
    - Write one Architect message file
    """
    station_root = resolve_station_root(args.root)
    incoming_architect, _ = get_chat_paths(station_root)

    session_id = args.session or f"{utc_now_iso()}_smoke"
    if getattr(args, "file", None):
        text = Path(args.file).read_text(encoding="utf-8")
    else:
        text = args.message or "Calyx CLI smoke test"

    metadata_extra = {
        "wizard_version": WIZARD_VERSION,
        "wizard_action": getattr(args, "action", None) or "advise",
        "smoke_test": True,
    }
    path = write_message(incoming_architect, session_id, text, metadata_extra=metadata_extra)
    print(f"[Calyx CLI] Smoke OK: wrote {path}")
    append_cli_audit(
        station_root,
        {
            "event": "smoke",
            "session_id": session_id,
            "message_path": str(path),
            "text_sha256": sha256_text(text),
            "text_preview": text[:200],
            "text_len": len(text),
        },
    )


def cmd_chat(args: argparse.Namespace) -> None:
    station_root = resolve_station_root(args.root)
    incoming_architect, outgoing_cbo = get_chat_paths(station_root)

    session_id = args.session
    if not session_id:
        session_id = f"{utc_now_iso()}_chat"
        if sys.stdin.isatty():
            try:
                entered = input(f"[Calyx CLI] Session id [{session_id}]: ").strip()
                if entered:
                    session_id = entered
            except (EOFError, KeyboardInterrupt):
                pass
    wizard_enabled = not getattr(args, "raw", False)
    default_mode = getattr(args, "mode", None) or "auto"

    print("[Calyx CLI] Calyx Console")
    print(f"[Calyx CLI] Station root: {station_root}")
    print(f"[Calyx CLI] Session id: {session_id}")
    print("[Calyx CLI] Type your message and press Enter.")
    print("[Calyx CLI] Commands: /quit, /inbox, /help, /mode auto|reflect|advise|propose|review, /review <intent_id|path>")
    if wizard_enabled:
        print("[Calyx CLI] Wizard: enabled (suggests reflect/advise/propose/review per message).")
    else:
        print("[Calyx CLI] Wizard: disabled (raw chat).")
    print("")

    last_seen_mtime: Optional[float] = None

    while True:
        try:
            line = input("Architect> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Calyx CLI] Exiting chat.")
            break

        if not line:
            continue

        if line.lower() in ("/quit", "/exit"):
            print("[Calyx CLI] Exiting chat.")
            break

        if line.lower() in ("/help", "/h", "?"):
            print("[Calyx CLI] /quit - exit")
            print("[Calyx CLI] /inbox - show replies for this session")
            print("[Calyx CLI] /mode auto|reflect|advise|propose|review - set default routing")
            print("[Calyx CLI] /review <intent_id|path> - run local Phase-1 review orchestrator")
            continue

        if line.lower() in ("/inbox", "/check"):
            messages = load_messages_from_dir(outgoing_cbo, since_ts=last_seen_mtime, session_id=session_id)
            if messages:
                last_seen_mtime = max(m[0] for m in messages)
            print_cbo_messages(messages)
            continue

        if line.lower().startswith("/mode "):
            mode = line.split(None, 1)[1].strip().lower()
            if mode not in ("auto", "reflect", "advise", "propose", "review"):
                print("[Calyx CLI] Invalid mode. Use: auto|reflect|advise|propose|review")
                continue
            default_mode = mode
            print(f"[Calyx CLI] Mode set to: {default_mode}")
            continue

        if line.lower().startswith("/review"):
            arg = line.split(None, 1)[1].strip() if len(line.split(None, 1)) > 1 else ""
            if not arg:
                print("[Calyx CLI] Usage: /review <intent_id|path>")
                continue
            ok, status = run_local_review(arg)
            print(f"[Calyx CLI] Local review: {'OK' if ok else 'ERROR'} - {status}")
            append_cli_audit(
                station_root,
                {"event": "local_review", "session_id": session_id, "target": arg, "ok": ok, "status": status},
            )
            continue

        chosen_action = "advise"
        confidence = 0.0
        reasons: list[str] = []
        if wizard_enabled:
            if default_mode == "auto":
                chosen_action, confidence, reasons = classify_intent_from_text(line)
            else:
                chosen_action = default_mode
                confidence = 0.9
                reasons = ["manual_mode"]

            action = prompt_wizard_action(chosen_action, confidence)
            if action is None:
                append_cli_audit(
                    station_root,
                    {
                        "event": "wizard_cancel",
                        "session_id": session_id,
                        "default_action": chosen_action,
                        "confidence": confidence,
                        "reasons": reasons,
                        "text_sha256": sha256_text(line),
                        "text_preview": line[:200],
                    },
                )
                continue
            chosen_action = action

        if chosen_action == "review" and wizard_enabled:
            intent_id = try_extract_intent_id(line)
            if intent_id:
                ok, status = run_local_review(intent_id)
                print(f"[Calyx CLI] Local review: {'OK' if ok else 'ERROR'} - {status}")
                append_cli_audit(
                    station_root,
                    {
                        "event": "wizard_local_review",
                        "session_id": session_id,
                        "intent_id": intent_id,
                        "ok": ok,
                        "status": status,
                        "confidence": confidence,
                        "reasons": reasons,
                        "text_sha256": sha256_text(line),
                    },
                )
                continue

            messages = load_messages_from_dir(outgoing_cbo, since_ts=last_seen_mtime, session_id=session_id)
            if messages:
                last_seen_mtime = max(m[0] for m in messages)
            print_cbo_messages(messages)
            append_cli_audit(
                station_root,
                {
                    "event": "wizard_inbox",
                    "session_id": session_id,
                    "confidence": confidence,
                    "reasons": reasons,
                    "text_sha256": sha256_text(line),
                },
            )
            continue

        metadata_extra = {
            "wizard_version": WIZARD_VERSION if wizard_enabled else None,
            "wizard_action": chosen_action if wizard_enabled else None,
            "wizard_confidence": confidence if wizard_enabled else None,
            "wizard_reasons": reasons if wizard_enabled else None,
        }
        metadata_extra = {k: v for k, v in metadata_extra.items() if v is not None}
        path = write_message(incoming_architect, session_id, line, metadata_extra=metadata_extra)
        print(f"[Calyx CLI] Sent ({chosen_action}): {path.name}")
        append_cli_audit(
            station_root,
            {
                "event": "send_message",
                "session_id": session_id,
                "message_path": str(path),
                "wizard_enabled": wizard_enabled,
                "wizard_action": chosen_action if wizard_enabled else None,
                "wizard_confidence": confidence if wizard_enabled else None,
                "wizard_reasons": reasons if wizard_enabled else None,
                "text_sha256": sha256_text(line),
                "text_preview": line[:200],
                "text_len": len(line),
            },
        )

        time.sleep(0.2)
        messages = load_messages_from_dir(outgoing_cbo, since_ts=last_seen_mtime, session_id=session_id)
        if messages:
            last_seen_mtime = max(m[0] for m in messages)
            print_cbo_messages(messages)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Calyx Communication CLI (Architect → Station text bridge, file-based)."
    )
    p.add_argument(
        "--root",
        help="Path to Station Calyx root. If omitted, uses CALYX_STATION_ROOT env var.",
    )

    sub = p.add_subparsers(dest="command")

    p_send = sub.add_parser("send", help="Send a single message to Station and exit.")
    p_send.add_argument("message", nargs=argparse.REMAINDER, help="Message text to send.")
    p_send.add_argument("--file", help="Read message text from a file path.")
    p_send.add_argument("--session", help="Optional session id; default is timestamp-based.")
    p_send.set_defaults(func=cmd_send)

    p_inbox = sub.add_parser("inbox", help="Show messages from CBO.")
    p_inbox.add_argument("--session", help="Optional session id to filter replies.")
    p_inbox.set_defaults(func=cmd_inbox)

    p_smoke = sub.add_parser("smoke", help="Non-interactive smoke test (writes one message file).")
    p_smoke.add_argument("--session", help="Optional session id; default is timestamp-based.")
    p_smoke.add_argument("--message", help="Message text for the smoke test.")
    p_smoke.add_argument("--file", help="Read smoke message text from a file path.")
    p_smoke.add_argument(
        "--action",
        choices=["reflect", "advise", "propose", "review"],
        default="advise",
        help="Wizard action label to stamp into metadata.",
    )
    p_smoke.set_defaults(func=cmd_smoke)

    p_chat = sub.add_parser("chat", help="Interactive console with Station (wizard-enabled by default).")
    p_chat.add_argument("--session", help="Optional session id; default is timestamp-based.")
    p_chat.add_argument("--raw", action="store_true", help="Disable wizard and send raw chat messages.")
    p_chat.add_argument(
        "--mode",
        choices=["auto", "reflect", "advise", "propose", "review"],
        default="auto",
        help="Wizard routing mode.",
    )
    p_chat.set_defaults(func=cmd_chat)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "command", None) is None:
        args.session = None
        args.raw = False
        args.mode = "auto"
        cmd_chat(args)
        return
    args.func(args)


if __name__ == "__main__":
    main()
