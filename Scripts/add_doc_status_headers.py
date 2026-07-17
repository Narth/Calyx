#!/usr/bin/env python3
"""Add status headers to docs/operations and docs/planning. WO_DOC_HYGIENE_DEPRECATION_GATES_V1."""
from pathlib import Path

HEADER_ACTIVE = """---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

"""

def main():
    repo = Path(__file__).resolve().parents[1]
    for sub in ("docs/operations", "docs/planning"):
        d = repo / sub
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            content = p.read_text(encoding="utf-8", errors="replace")
            if content.strip().startswith("---"):
                continue
            p.write_text(HEADER_ACTIVE + content, encoding="utf-8")
            print("Added header to", p.relative_to(repo))

if __name__ == "__main__":
    main()
