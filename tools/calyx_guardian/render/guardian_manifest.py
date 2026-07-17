#!/usr/bin/env python3
"""Generate manifest from evidence. Stub — governance plans reference this."""

import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="logs/calyx_guardian")
    ap.add_argument("--correlation-id", default="stub")
    args = ap.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {"correlation_id": args.correlation_id, "status": "stub"}
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Manifest written: {outdir / 'manifest.json'}")


if __name__ == "__main__":
    main()
