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
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


CANONICAL_POLICY_HASH = "4E4924361545468CB42387F38C946A3C3E802BD1494868C378FBE7DBB5FFD6D7"


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
        if not env_root:
            print("[Calyx CLI] Error: Station root not provided. Use --root or set CALYX_STATION_ROOT.")
            sys.exit(1)
        root = Path(env_root).expanduser().resolve()

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


def load_messages_from_dir(dir_path: Path, since_ts: Optional[float] = None) -> List[Tuple[float, Path, Dict]]:
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
    text = " ".join(args.message) if args.message else ""
    if not text:
        print("[Calyx CLI] Error: No message text provided.")
        sys.exit(1)

    path = write_message(incoming_architect, session_id, text)
    print(f"[Calyx CLI] Sent message to Station at {path}")


def cmd_inbox(args: argparse.Namespace) -> None:
    station_root = resolve_station_root(args.root)
    _, outgoing_cbo = get_chat_paths(station_root)

    messages = load_messages_from_dir(outgoing_cbo)
    print_cbo_messages(messages)


def cmd_chat(args: argparse.Namespace) -> None:
    station_root = resolve_station_root(args.root)
    incoming_architect, outgoing_cbo = get_chat_paths(station_root)

    session_id = args.session or f"{utc_now_iso()}_chat"
    print("[Calyx CLI] Calyx Communication Console")
    print(f"[Calyx CLI] Station root: {station_root}")
    print(f"[Calyx CLI] Session id: {session_id}")
    print("[Calyx CLI] Type your message and press Enter. Type /quit to exit, /inbox to check replies.\n")

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

        if line.lower() in ("/inbox", "/check"):
            messages = load_messages_from_dir(outgoing_cbo, since_ts=last_seen_mtime)
            if messages:
                last_seen_mtime = max(m[0] for m in messages)
            print_cbo_messages(messages)
            continue

        path = write_message(incoming_architect, session_id, line)
        print(f"[Calyx CLI] Sent: {path.name}")

        time.sleep(0.2)
        messages = load_messages_from_dir(outgoing_cbo, since_ts=last_seen_mtime)
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

    sub = p.add_subparsers(dest="command", required=True)

    p_send = sub.add_parser("send", help="Send a single message to Station and exit.")
    p_send.add_argument("message", nargs=argparse.REMAINDER, help="Message text to send.")
    p_send.add_argument("--session", help="Optional session id; default is timestamp-based.")
    p_send.set_defaults(func=cmd_send)

    p_inbox = sub.add_parser("inbox", help="Show messages from CBO.")
    p_inbox.set_defaults(func=cmd_inbox)

    p_chat = sub.add_parser("chat", help="Interactive chat session with Station.")
    p_chat.add_argument("--session", help="Optional session id; default is timestamp-based.")
    p_chat.set_defaults(func=cmd_chat)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
