"""Intent artifact registry: paths and load/save for runtime/cbo/intents/<intent_id>/."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def get_intents_root(runtime_dir: Path) -> Path:
    """Canonical root for intent artifacts: runtime/cbo/intents/."""
    root = runtime_dir / "cbo" / "intents"
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_intent_dir(intent_id: str, runtime_dir: Path) -> Path:
    """Path for one intent artifact dir: runtime/cbo/intents/<intent_id>/."""
    root = get_intents_root(runtime_dir)
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in intent_id)
    path = root / safe_id
    path.mkdir(parents=True, exist_ok=True)
    (path / "receipts").mkdir(exist_ok=True)
    return path


def load_intent_artifact(intent_id: str, runtime_dir: Path) -> dict[str, Any] | None:
    """Load intent.json for intent_id. Returns None if missing."""
    d = get_intent_dir(intent_id, runtime_dir)
    path = d / "intent.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_intent_artifact(intent_id: str, runtime_dir: Path, data: dict[str, Any]) -> Path:
    """Write intent.json. Returns path."""
    d = get_intent_dir(intent_id, runtime_dir)
    path = d / "intent.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def load_status(intent_id: str, runtime_dir: Path) -> dict[str, Any] | None:
    """Load status.json."""
    d = get_intent_dir(intent_id, runtime_dir)
    path = d / "status.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_status(intent_id: str, runtime_dir: Path, data: dict[str, Any]) -> Path:
    d = get_intent_dir(intent_id, runtime_dir)
    path = d / "status.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def save_plan(intent_id: str, runtime_dir: Path, data: dict[str, Any]) -> Path:
    d = get_intent_dir(intent_id, runtime_dir)
    path = d / "plan.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def save_critique_checkpoint(intent_id: str, runtime_dir: Path, data: dict[str, Any]) -> Path:
    """Write critique_checkpoint.json for one intent."""
    d = get_intent_dir(intent_id, runtime_dir)
    path = d / "critique_checkpoint.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def append_clarification(intent_id: str, runtime_dir: Path, entry: dict[str, Any]) -> Path:
    """Append one line to clarifications.jsonl."""
    d = get_intent_dir(intent_id, runtime_dir)
    path = d / "clarifications.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path
