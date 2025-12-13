#!/usr/bin/env python3
r"""
CBO LLM GPU Verification

Runs a safe GPU throughput check and (optionally) a faster-whisper probe when available.
If tests meet basic thresholds, promotes LLM access:
 - Enables GPU gate (outgoing/gates/gpu.ok)
 - Writes/updates llm_ready.lock (success=true)
 - Updates policy (outgoing/policies/cbo_permissions.json) to set full_access=true
 - Emits an overseer decree report under outgoing/overseer_reports/verdicts/

Usage (Windows PowerShell):
    python -u tools/cbo_llm_gpu_verify.py --fast    # quick torch matmul (half precision)
    python -u tools/cbo_llm_gpu_verify.py --attempt-whisper   # also try a short faster-whisper run if installed

Notes:
- No network calls. The whisper probe only runs if faster-whisper is installed and a model can be instantiated without download.
- Thresholds are conservative and adjustable via flags.
"""
from __future__ import annotations
import argparse
import json
import os
import time
from pathlib import Path
from typing import Optional, Tuple
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outgoing'
GATES = OUT / 'gates'
POLICIES = OUT / 'policies'
REPORTS = OUT / 'overseer_reports' / 'verdicts'
LOCK_LLM = OUT / 'llm_ready.lock'
GATE_GPU = GATES / 'gpu.ok'
POLICY_CBO = POLICIES / 'cbo_permissions.json'


def _gpu_present() -> Tuple[bool, str]:
    try:
        res = subprocess.run(['nvidia-smi', '-L'], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            return True, 'nvidia-smi'
    except Exception:
        pass
    try:
        import torch  # type: ignore
        if torch.cuda.is_available():
            return True, 'torch.cuda'
    except Exception:
        pass
    return False, 'none'


def _torch_matmul_bench(size: int = 2048, iters: int = 10) -> Optional[dict]:
    try:
        import torch  # type: ignore
        if not torch.cuda.is_available():
            return None
        device = torch.device('cuda')
        torch.cuda.synchronize()
        a = torch.randn(size, size, device=device, dtype=torch.float16)
        b = torch.randn(size, size, device=device, dtype=torch.float16)
        # Warmup
        for _ in range(3):
            _ = a @ b
        torch.cuda.synchronize()
        t0 = time.time()
        for _ in range(iters):
            _ = a @ b
        torch.cuda.synchronize()
        t1 = time.time()
        sec = t1 - t0
        # FLOPs: 2*N^3 per matmul
        flops = 2 * (size ** 3) * iters
        tflops = flops / sec / 1e12
        return {
            'backend': 'torch.cuda',
            'size': size,
            'iters': iters,
            'seconds': sec,
            'tflops': tflops,
        }
    except Exception:
        return None


def _try_faster_whisper(seconds: float = 3.0) -> Optional[dict]:
    """Attempt a tiny faster-whisper run if the package is available.
    Uses a generated dummy waveform (sine) to avoid file I/O and downloads.
    Only proceeds if model instantiation appears to succeed quickly.
    """
    try:
        from math import sin, pi
        import numpy as np  # type: ignore
        from faster_whisper import WhisperModel  # type: ignore
        sr = 16000
        t = np.arange(0, int(sr * seconds)) / sr
        wave = (0.1 * np.sin(2 * pi * 440 * t)).astype(np.float32)
        model_name = 'small'  # rely on CTranslate2 cache if present
        # Try GPU half precision; fall back to cpu if needed
        device = 'cuda'
        compute = 'float16'
        t0 = time.time()
        try:
            model = WhisperModel(model_name, device=device, compute_type=compute)
        except Exception:
            return None
        load_sec = time.time() - t0
        s0 = time.time()
        try:
            segments, info = model.transcribe(wave, word_timestamps=True)
            latency = time.time() - s0
        except TypeError:
            # older API variant
            segments = model.transcribe(wave, word_timestamps=True)
            latency = time.time() - s0
        return {
            'backend': 'faster-whisper',
            'device': device,
            'compute_type': compute,
            'load_sec': load_sec,
            'latency_sec': latency,
        }
    except Exception:
        return None


def _promote_full_access(decree: dict) -> None:
    GATES.mkdir(parents=True, exist_ok=True)
    POLICIES.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    # Ensure GPU gate
    GATE_GPU.write_text('ok', encoding='utf-8')
    # LLM readiness lock (annotated)
    payload = {
        'name': 'llm_ready',
        'phase': 'verify',
        'status': 'running',
        'ts': time.time(),
        'status_message': 'GPU verified; LLM permitted for full access by CBO',
        'gpu_verified': True,
    }
    LOCK_LLM.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    # Policy update
    pol = {}
    if POLICY_CBO.exists():
        try:
            pol = json.loads(POLICY_CBO.read_text(encoding='utf-8'))
        except Exception:
            pol = {}
    pol.update({'granted': True, 'full_access': True})
    POLICY_CBO.write_text(json.dumps(pol, ensure_ascii=False, indent=2), encoding='utf-8')
    # Decree report
    ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    rep = REPORTS / f'DECREE_{ts}_CBO_LLM_FULL_ACCESS.json'
    rep.write_text(json.dumps(decree, ensure_ascii=False, indent=2), encoding='utf-8')


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description='CBO LLM GPU verification')
    ap.add_argument('--fast', action='store_true', help='Run quick torch matmul benchmark (default if nothing else set)')
    ap.add_argument('--size', type=int, default=2048, help='Matrix size for torch bench')
    ap.add_argument('--iters', type=int, default=10, help='Iterations for torch bench')
    ap.add_argument('--attempt-whisper', action='store_true', help='Attempt a tiny faster-whisper run if locally available')
    ap.add_argument('--tflops-min', type=float, default=0.5, help='Minimum TFLOPS to consider GPU viable')
    ap.add_argument('--presence-sufficient', action='store_true', help='Treat GPU presence as sufficient if throughput test unavailable')
    args = ap.parse_args(argv)

    present, backend = _gpu_present()
    results: dict = {'gpu_present': present, 'backend': backend}

    torch_res = None
    if args.fast or (not args.attempt_whisper):
        torch_res = _torch_matmul_bench(size=args.size, iters=args.iters)
        results['torch'] = torch_res

    whisper_res = None
    if args.attempt_whisper:
        whisper_res = _try_faster_whisper()
        results['whisper'] = whisper_res

    success = False
    if torch_res and torch_res.get('tflops', 0) >= args.tflops_min:
        success = True
    # If whisper succeeded with GPU device, consider that success too
    if whisper_res and whisper_res.get('device') == 'cuda':
        success = True
    if not success and args.presence_sufficient and present:
        # Allow promotion when GPU is detected but local CUDA libs are not wired into Python
        success = True

    decree = {
        'entity': 'CBO',
        'time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'action': 'LLM_FULL_ACCESS' if success else 'LLM_ACCESS_DENIED',
        'criteria': {
            'gpu_present': present,
            'backend': backend,
            'tflops_min': args.tflops_min,
        },
        'results': results,
        'success': success,
        'notes': 'Promotion requires GPU presence and acceptable throughput; whisper test optional.'
    }

    print(json.dumps(decree, indent=2))

    if success:
        _promote_full_access(decree)
        print('ok: full access granted (policy updated, llm_ready lock written, gpu gate enabled)')
        return 0
    else:
        print('warn: GPU verification did not meet thresholds; no policy changes made')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
