"""
Run-level envelope metadata writer.
Atomic, crash-safe writing of run summary metadata.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def compute_sha256(data: bytes) -> str:
    """Compute SHA256 hex digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def compute_file_sha256(path: Path) -> str:
    """Compute SHA256 hex digest of file contents."""
    try:
        with open(path, "rb") as f:
            return compute_sha256(f.read())
    except OSError:
        return ""


def write_run_envelope_tmp(path: Path, data: dict) -> None:
    """
    Write run envelope to temporary file (.tmp).
    Atomic write: fsync + close before rename.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".run.json.tmp")
    
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        # Ensure data is written to disk
        import os
        if hasattr(f, "fileno"):
            os.fsync(f.fileno())
    
    return tmp_path


def finalize_run_envelope(tmp_path: Path, final_path: Path) -> None:
    """
    Atomically rename temporary envelope file to final path.
    Removes .tmp suffix on success.
    """
    tmp_path = Path(tmp_path)
    final_path = Path(final_path)
    
    if not tmp_path.exists():
        raise FileNotFoundError(f"Temporary envelope not found: {tmp_path}")
    
    # Atomic rename (POSIX: rename is atomic; Windows: may require different approach)
    try:
        tmp_path.replace(final_path)
    except OSError as e:
        # On Windows, if file exists, replace may fail
        if final_path.exists():
            final_path.unlink()
            tmp_path.replace(final_path)
        else:
            raise
