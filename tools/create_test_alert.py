#!/usr/bin/env python3
"""Create a one-off test alert and exercise notifier/cleanup paths.

This script creates an alert JSON under outgoing/alerts/ and updates latest_alert.json
and appends a dialog line to outgoing/bridge/dialog.log. It also triggers the
notify_toast helper so you can visually verify the Windows notification.
"""
from __future__ import annotations
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    alerts_dir = root / "outgoing" / "alerts"
    alerts_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    ts = now.isoformat()
    name_ts = now.isoformat().replace(":", "-")
    alert = {
        "ts": ts,
        "source": "test",
        "entry": {"test": True, "note": "Synthetic test alert created by create_test_alert.py"}
    }
    path = alerts_dir / f"alert_test_{name_ts}.json"
    path.write_text(json.dumps(alert, ensure_ascii=False, indent=2), encoding="utf-8")

    latest = alerts_dir / "latest_alert.json"
    latest.write_text(json.dumps({"latest": path.name, "ts": ts}, ensure_ascii=False, indent=2), encoding="utf-8")

    # Append operator-facing line
    bridge = root / "outgoing" / "bridge"
    bridge.mkdir(parents=True, exist_ok=True)
    dialog = bridge / "dialog.log"
    with dialog.open("a", encoding="utf-8") as fh:
        fh.write(f"{ts} ALERT> test alert created file={path}\n")

    # Call notifier
    try:
        subprocess.run([sys.executable, "tools/notify_toast.py", "--title", "Calyx Alert (test)", "--msg", "Synthetic test alert created"], check=False)
    except Exception:
        pass

    print("test alert created:", path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
