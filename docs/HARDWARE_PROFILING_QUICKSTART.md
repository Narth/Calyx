# Hardware Profiling — Quick Start Guide

**Status:** ✅ Operational  
**Last Verified:** 2025-12-13  
**System:** Desktop-M965JSC (Razer Blade Stealth / MX150)

---

## Setup (First Time Only)

### 1. Install Python (if needed)

```powershell
# Install Python via Windows Store
winget install 9NQ7512CXL7T

# Install default Python runtime
py install default

# Verify installation
python --version
# Expected: Python 3.14.2 or newer
```

### 2. Install Dependencies

```powershell
# Install psutil (required for hardware metrics)
python -m pip install psutil

# Verify installation
python -c "import psutil; print(f'psutil {psutil.__version__} installed')"
# Expected: psutil 7.1.3 installed
```

### 3. Verify GPU Access

```powershell
# Check NVIDIA GPU detection
nvidia-smi

# Expected output:
# +-----------------------------------------------------------------------------+
# | NVIDIA-SMI 457.51       Driver Version: 457.51       CUDA Version: 11.1     |
# |-------------------------------+----------------------+----------------------+
# | GPU  Name            TCC/WDDM | Bus-Id        Disp.A | Volatile Uncorr. ECC |
# | Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
# |===============================+======================+======================|
# |   0  GeForce MX150      WDDM  | 00000000:01:00.0 Off |                  N/A |
# | N/A   43C    P8    N/A /  N/A |     68MiB /  4096MiB |      0%      Default |
# +-------------------------------+----------------------+----------------------+
```

---

## Run Hardware Profiler

### Check Profile Summary

```powershell
python -u .\tools\hardware_profiler.py --summary
```

**Expected Output:**
```json
{
  "profile_name": "desktop_m965jsc",
  "tier": "entry_level",
  "capability_summary": "Can run small models, heavy throttling, serial operations",
  "hardware": {
    "gpu": "GeForce MX150",
    "gpu_memory_gb": 4.0,
    "cpu_cores": 4,
    "system_memory_gb": 15.9
  },
  "limitations": [...],
  "recommended_optimizations": [...]
}
```

### Run Quick Benchmark

```powershell
# 30-second benchmark
python -u .\tools\hardware_profiler.py --benchmark 30
```

Samples metrics every 5 seconds and displays:
- CPU utilization
- GPU utilization
- VRAM usage

### Start Continuous Collection

```powershell
# Collect metrics every 60 seconds
python -u .\tools\hardware_profiler.py

# Or with custom interval (e.g., every 30 seconds)
python -u .\tools\hardware_profiler.py --interval 30
```

**Metrics saved to:** `logs/hardware_profile_desktop_m965jsc.jsonl`

**To stop:** Press `Ctrl+C`

---

## Verify Data Collection

### Check Metrics File

```powershell
# View last 5 lines of metrics
Get-Content .\logs\hardware_profile_desktop_m965jsc.jsonl -Tail 5
```

Each line is a JSON object with:
- `timestamp` — ISO 8601 timestamp
- `cpu` — CPU utilization, frequency, load
- `memory` — RAM usage
- `gpu` — GPU utilization, VRAM, temperature, power
- `processes` — Python/Whisper process metrics
- `inference_timing` — Wake-word latency (if available)

---

## Troubleshooting

### "Python was not found"

**Solution:** Install Python:
```powershell
winget install 9NQ7512CXL7T
py install default
```

### "No module named 'psutil'"

**Solution:** Install dependency:
```powershell
python -m pip install psutil
```

### GPU shows "available": false

**Causes:**
1. NVIDIA drivers not installed
2. nvidia-smi not in PATH
3. Non-NVIDIA GPU

**Solution:** Install NVIDIA drivers from https://www.nvidia.com/Download/index.aspx

### Profiler shows "tier": "cpu_only"

**Cause:** GPU not detected (see above)

**Verify:**
```powershell
nvidia-smi --query-gpu=name,memory.total --format=csv
```

Should output:
```
name, memory.total [MiB]
GeForce MX150, 4096
```

---

## Next Steps

Once profiler is running:

1. **Let collect for 1 week** during normal operations
2. **Run wake-word listener** to capture inference timing:
   ```powershell
   python -u .\Scripts\listener_wake.py
   ```
3. **Run agent scheduler** to capture multi-agent metrics:
   ```powershell
   python -u .\tools\agent_scheduler.py --interval 480
   ```

After 1 week, analyze data:
```powershell
# Generate statistical analysis
python -u .\tools\hardware_comparator.py --analyze desktop_m965jsc --hours 168
```

---

## Known Issues (Resolved)

### ✅ nvidia-smi "compute_cap" field invalid

**Issue:** Original profiler queried `compute_cap` field which doesn't exist  
**Fixed:** Removed unsupported field from query  
**Commit:** 2025-12-13 (infrastructure deployment)

### ✅ Power metrics "Not Supported" on MX150

**Issue:** MX150 doesn't report power draw  
**Fixed:** Graceful handling of N/A values  
**Workaround:** Power draw shows 0 (expected for mobile GPUs)

---

**Status:** ✅ Ready for baseline data collection  
**Verified:** 2025-12-13  
**System:** Desktop-M965JSC / GeForce MX150 / 16GB RAM
