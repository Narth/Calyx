#!/usr/bin/env python3
"""
GPU Utilities — Helper functions for GPU detection and configuration.

Provides:
- GPU availability checking
- GPU offloading configuration for llama_cpp
- GPU resource monitoring
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
GATE_GPU = ROOT / "outgoing" / "gates" / "gpu.ok"


def is_gpu_available() -> bool:
    """Check if GPU is available for llama_cpp.
    
    Checks:
    1. GPU gate file exists
    2. nvidia-smi is available
    
    Returns:
        True if GPU is available and ready to use
    """
    if not GATE_GPU.exists():
        return False
    
    try:
        rc = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=2
        ).returncode
        return rc == 0
    except Exception:
        return False


def get_gpu_layer_count() -> int:
    """Return number of GPU layers to offload for llama_cpp.
    
    Returns:
        -1 to offload all layers to GPU if available
        0 to use CPU only
    """
    if is_gpu_available():
        return -1  # Offload all layers to GPU
    return 0  # CPU only


def get_gpu_info() -> Optional[Dict]:
    """Get GPU information from CBO heartbeat.
    
    Returns:
        GPU info dict or None if not available
    """
    try:
        cbo_lock = ROOT / "outgoing" / "cbo.lock"
        if not cbo_lock.exists():
            return None
        
        import json
        cbo_data = json.loads(cbo_lock.read_text(encoding="utf-8"))
        gpu_info = cbo_data.get("metrics", {}).get("gpu")
        return gpu_info if isinstance(gpu_info, dict) else None
    except Exception:
        return None


def get_gpu_utilization() -> Optional[float]:
    """Get current GPU utilization percentage.
    
    Returns:
        GPU utilization (0-100) or None if not available
    """
    gpu_info = get_gpu_info()
    if not gpu_info:
        return None
    
    try:
        gpus = gpu_info.get("gpus", [])
        if gpus and len(gpus) > 0:
            util = gpus[0].get("util_pct")
            return float(util) if util is not None else None
    except Exception:
        pass
    
    return None


def should_use_gpu_for_llm() -> bool:
    """Determine if GPU should be used for LLM inference.
    
    Considers:
    - GPU availability
    - GPU utilization (use if < 80%)
    
    Returns:
        True if GPU should be used for LLM
    """
    if not is_gpu_available():
        return False
    
    util = get_gpu_utilization()
    if util is None:
        return True  # Use GPU if we can't determine utilization
    
    return util < 80.0  # Use GPU if utilization is below 80%

