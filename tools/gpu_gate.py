#!/usr/bin/env python3
"""
GPU Gate Helper
- Enables/disables a conservative GPU permission gate for CBO-managed processes
- Detects basic GPU readiness (nvidia-smi or torch.cuda)

Usage:
  python -u tools/gpu_gate.py --enable
  python -u tools/gpu_gate.py --disable
  python -u tools/gpu_gate.py --status
"""
from __future__ import annotations
import argparse
import subprocess
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
GATES = ROOT / 'outgoing' / 'gates'
GATE_GPU = GATES / 'gpu.ok'


def _detect_gpu() -> dict:
    info = {'present': False, 'backend': None, 'devices': []}
    # nvidia-smi
    try:
        res = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            info['present'] = True
            info['backend'] = 'nvidia-smi'
            info['devices'] = [ln.strip() for ln in res.stdout.strip().splitlines() if ln.strip()]
            return info
    except Exception:
        pass
    # torch.cuda
    try:
        import torch  # type: ignore
        if torch.cuda.is_available():
            info['present'] = True
            info['backend'] = 'torch.cuda'
            info['devices'] = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
            return info
    except Exception:
        pass
    return info


def enable_gate() -> None:
    GATES.mkdir(parents=True, exist_ok=True)
    GATE_GPU.write_text('ok', encoding='utf-8')


def disable_gate() -> None:
    try:
        if GATE_GPU.exists():
            GATE_GPU.unlink()
    except Exception:
        pass


def status() -> dict:
    det = _detect_gpu()
    return {
        'gate': GATE_GPU.exists(),
        'gpu': det,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='GPU gate helper')
    ap.add_argument('--enable', action='store_true')
    ap.add_argument('--disable', action='store_true')
    ap.add_argument('--status', action='store_true')
    args = ap.parse_args(argv)
    if args.enable:
        enable_gate()
    elif args.disable:
        disable_gate()
    elif args.status:
        print(json.dumps(status(), indent=2))
        return 0
    else:
        ap.print_help()
        return 1
    print(json.dumps(status(), indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
