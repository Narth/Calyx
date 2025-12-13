#!/usr/bin/env python3
"""
Fix MODEL_MANIFEST.json filenames to point to local copies under tools/models using a WSL-friendly path.

When triage runs inside WSL, absolute Linux paths in the manifest may not match the actual location
of the GGUF files. This script maps each entry's filename to `/mnt/<drive>/.../tools/models/<basename>`
when a matching file exists locally.

Usage (Windows PowerShell):
  python -u tools\fix_manifest_paths.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAN = ROOT / "tools" / "models" / "MODEL_MANIFEST.json"
MODELS_DIR = ROOT / "tools" / "models"


def _to_wsl_path(win_path: Path) -> str:
    # Convert e.g., C:\Calyx_Terminal\tools\models\foo.gguf -> /mnt/c/Calyx_Terminal/tools/models/foo.gguf
    p = win_path.resolve()
    drive = p.anchor.replace("\\", "").replace(":", "").lower()  # 'C' -> 'c'
    tail = str(p).replace(p.anchor, "").replace("\\", "/")
    return f"/mnt/{drive}/{tail}"


def main() -> int:
    try:
        data = json.loads(MAN.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Failed to read manifest: {exc}")
        return 2
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        print("No models[] in manifest")
        return 3
    changed = 0
    for m in models:
        try:
            fname = m.get("filename")
            if not isinstance(fname, str) or not fname:
                continue
            base = os.path.basename(fname)
            local = MODELS_DIR / base
            if local.exists():
                new = _to_wsl_path(local)
                if fname != new:
                    m["filename"] = new
                    changed += 1
        except Exception:
            continue
    if changed:
        MAN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Updated {changed} filename(s) -> WSL paths")
    else:
        print("No changes needed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
