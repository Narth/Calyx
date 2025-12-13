"""Helper for agents (or humans) to send control commands to the Calyx Agent Watcher.

Commands are file-based JSON messages placed under outgoing/watcher_cmds/.
Each command must include a token obtained from outgoing/watcher_token.lock.

Example:
    from tools.agent_control import post_command
    post_command("set_banner", {"text": "Hello from Agent1", "color": "#1f6feb"})

Safe commands implemented by the watcher:
- set_banner(text, color?)
- append_log(text)
- show_toast(text)
- open_path(path under repo only)
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
CMDS = OUT / "watcher_cmds"
TOKEN_LOCK = OUT / "watcher_token.lock"


def _read_token() -> Optional[str]:
    try:
        data = json.loads(TOKEN_LOCK.read_text(encoding="utf-8"))
        return str(data.get("token")) if isinstance(data, dict) else None
    except Exception:
        return None


def post_command(cmd: str, args: Optional[Dict[str, Any]] = None, sender: str = "agent1") -> Path:
    """Post a command to the watcher. Returns the path to the created file.

    Raises RuntimeError if token is missing.
    """
    token = _read_token()
    if not token:
        raise RuntimeError("Watcher token not found. Start the watcher to generate one.")
    CMDS.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": time.time(),
        "from": sender,
        "token": token,
        "cmd": str(cmd),
        "args": args or {},
        "id": uuid.uuid4().hex,
    }
    name = f"{int(time.time()*1000)}_{payload['id']}.json"
    path = CMDS / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    # Tiny manual test
    p = post_command("append_log", {"text": "Manual test: hello"}, sender="manual")
    print("Wrote:", p)
