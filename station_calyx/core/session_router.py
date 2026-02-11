"""Session router - single source-of-truth for dashboard-selected session

Stores a small JSON file `data/session_route.json` with the current selected
session and associated user identity. This allows the dashboard message handler
to resolve session_user for identity binding even when individual messages do
not include session context.

Format:
{
  "selected_session": "agent:main:main",
  "user_id": "user-test-01"
}

Functions:
 - get_selected_session() -> (session, user_id)
 - set_selected_session(session, user_id)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple, Optional

from .config import get_config


def _path() -> Path:
    cfg = get_config()
    p = cfg.data_dir / "session_route.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_selected_session() -> Tuple[Optional[str], Optional[str]]:
    p = _path()
    if not p.exists():
        return None, None
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        return data.get('selected_session'), data.get('user_id')
    except Exception:
        return None, None


def set_selected_session(session: str, user_id: Optional[str] = None) -> None:
    p = _path()
    data = {'selected_session': session, 'user_id': user_id}
    p.write_text(json.dumps(data, indent=2), encoding='utf-8')
