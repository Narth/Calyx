#!/usr/bin/env python3
"""
Discord Gateway Preflight — WO_GATEWAY_DENY_BY_DEFAULT_HARDEN_V1.

Validates gateway config before startup: deny-by-default semantics, allowlist resolution.
Exit 0 = config valid; 1 = config invalid; 2 = governance required but allowlists empty.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add repo root for imports
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _resolve_repo_root() -> Path:
    env_root = os.environ.get("CALYX_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return REPO_ROOT


def _parse_discord_ids_md(root: Path) -> tuple[list[str], list[str]]:
    """Parse DISCORD_IDS.md for channel and user IDs."""
    import re
    path = root / "DISCORD_IDS.md"
    channels: list[str] = []
    users: list[str] = []
    if not path.exists():
        return channels, users
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if "Station Health Channel ID" in line or ("channel" in line.lower() and "ID" in line):
                m = re.search(r"(\d{17,20})", line)
                if m and m.group(1) not in channels:
                    channels.append(m.group(1))
            if "Authorized User ID" in line or "User ID" in line:
                m = re.search(r"(\d{17,20})", line)
                if m and m.group(1) not in users:
                    users.append(m.group(1))
    except Exception:
        pass
    return channels, users


def _resolve_config(cli_channels: list[str] | None, cli_users: list[str] | None) -> tuple[list[str], list[str]]:
    """Resolve config: CLI > env > DISCORD_IDS.md."""
    root = _resolve_repo_root()
    channels = list(cli_channels) if cli_channels else []
    users = list(cli_users) if cli_users else []
    if not channels:
        env = os.environ.get("DISCORD_CHANNEL_ALLOWLIST", "").strip()
        if env:
            channels = [x.strip() for x in env.replace(",", " ").split() if x.strip()]
    if not users:
        env = os.environ.get("DISCORD_AUTHORIZED_USERS", "").strip()
        if env:
            users = [x.strip() for x in env.replace(",", " ").split() if x.strip()]
    if not channels or not users:
        ids_channels, ids_users = _parse_discord_ids_md(root)
        if not channels:
            channels = ids_channels
        if not users:
            users = ids_users
    return channels, users


def main() -> int:
    governance = os.environ.get("CALYX_GOVERNANCE_REQUIRED", "true").lower() not in ("false", "0", "no")
    channels, users = _resolve_config(None, None)

    print(f"Governance required: {governance}")
    print(f"Channel allowlist: {channels or '(empty - deny all guild channels)'}")
    print(f"Authorized users: {users or '(empty - deny all DMs)'}")

    if governance and (not channels and not users):
        print("FAIL: governance_required but allowlists empty. Set DISCORD_CHANNEL_ALLOWLIST and/or DISCORD_AUTHORIZED_USERS.", file=sys.stderr)
        return 2

    if not channels and not users:
        print("WARN: Both allowlists empty. Gateway will deny all messages (deny-by-default).", file=sys.stderr)

    print("PASS: Config valid for deny-by-default.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
