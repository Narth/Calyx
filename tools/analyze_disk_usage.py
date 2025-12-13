#!/usr/bin/env python3
"""Analyze disk usage in outgoing directory."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTGOING = ROOT / "outgoing"

def get_size(path: Path) -> int:
    """Get total size of directory."""
    total = 0
    if path.is_file():
        return path.stat().st_size
    try:
        for item in path.rglob('*'):
            if item.is_file():
                total += item.stat().st_size
    except Exception:
        pass
    return total

# Analyze top directories
results = []
for item in OUTGOING.iterdir():
    if item.is_dir():
        size = get_size(item)
        results.append((item.name, size))

results.sort(key=lambda x: x[1], reverse=True)

print("Top 20 directories by size:")
for name, size in results[:20]:
    print(f"{name:40} {size / 1024 / 1024:8.2f} MB")

