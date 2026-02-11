#!/usr/bin/env python3
"""
Agent primitives and helpers for Station Calyx.

Provides small, reusable functions for gate checks, atomic writes and config helpers
so CLIs and daemons can share consistent behavior (gates, atomic file writes, processed
index helpers).
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
GATES_DIR = ROOT / 'outgoing' / 'gates'
LOG_DIR = ROOT / 'logs' / 'executor'


def check_gates(required: Iterable[str] | None = None) -> bool:
    """Return True if all required gate files exist under outgoing/gates."""
    if required is None:
        required = ('network.ok', 'llm.ok')
    try:
        for name in required:
            if not (GATES_DIR / name).exists():
                return False
        return True
    except Exception:
        return False


def read_config_enabled(config_file: Path) -> bool:
    """Lightweight check for `enabled: true` in a YAML-ish config file."""
    try:
        if not config_file.exists():
            return False
        txt = config_file.read_text(encoding='utf-8')
        for line in txt.splitlines():
            s = line.strip().lower()
            if s.startswith('enabled:'):
                val = s.split(':', 1)[1].strip()
                return val in ('true', '1', 'yes', 'on')
    except Exception:
        pass
    return False


def atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON to `path` atomically using a .tmp file and os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    try:
        os.replace(str(tmp), str(path))
    except Exception:
        # best-effort fallback
        tmp.rename(path)


def read_processed_index() -> Dict[str, Any]:
    """Read the processed_intents.json index under logs/executor if present."""
    out = {}
    try:
        p = LOG_DIR / 'processed_intents.json'
        if p.exists():
            out = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        out = {}
    return out


def update_processed_index(intent_id: str, value: Any) -> None:
    """Set intent_id -> value in processed_intents.json atomically."""
    try:
        p = LOG_DIR / 'processed_intents.json'
        proc = {}
        if p.exists():
            try:
                proc = json.loads(p.read_text(encoding='utf-8'))
            except Exception:
                proc = {}
        proc[intent_id] = value
        atomic_write_json(p, proc)
    except Exception:
        pass
