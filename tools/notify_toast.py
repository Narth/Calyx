#!/usr/bin/env python3
"""Show a Windows notification (balloon tip fallback).

This script attempts to show a Windows notification using System.Windows.Forms
balloon tip which works on standard Windows PowerShell environments. It is a
lightweight fallback for modern toasts and does not require extra modules.

Usage:
  python -u tools\notify_toast.py --title "Title" --msg "Message"
"""
from __future__ import annotations
import argparse
import shlex
import subprocess
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--msg", required=True)
    args = parser.parse_args(argv)

    # Build PowerShell script to display a balloon tip via System.Windows.Forms
    # This is compatible with Windows PowerShell and does not require external modules.
    ps_script = r"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$ni = New-Object System.Windows.Forms.NotifyIcon
$ni.Icon = [System.Drawing.SystemIcons]::Information
$ni.BalloonTipTitle = {title}
$ni.BalloonTipText = {msg}
$ni.Visible = $true
$ni.ShowBalloonTip(10000)
Start-Sleep -Seconds 6
$ni.Dispose()
""".strip()

    # Escape title and message for PowerShell string literal
    def ps_quote(s: str) -> str:
        # Use single quotes and escape single quotes by doubling
        return "'" + s.replace("'", "''") + "'"

    ps_script = ps_script.format(title=ps_quote(args.title), msg=ps_quote(args.msg))

    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        ps_script
    ]

    try:
        # Run and wait briefly; this should return quickly
        subprocess.run(cmd, check=False)
        return 0
    except Exception as e:
        print("notify_toast failed:", e, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
