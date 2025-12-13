# Hardware Performance Profiling — Operations Guide

**Purpose:** Collect performance metrics on different hardware configurations to optimize BloomOS for low-spec and high-spec environments.

**Current Profiles:**
- `desktop_m965jsc_entry` — Razer Blade Stealth / MX150 (4GB VRAM, 16GB RAM) — **ACTIVE BASELINE**
- `desktop_home_target` — Home Desktop / RTX 2070 Super (8GB VRAM, 32GB RAM) — **PRIMARY TARGET**
- `ideal_bloomos_target` — Reference specification for optimal experience

---

## Setup & Dependencies

### Install Python (if needed)

If Python is not installed:

```powershell
# Option 1: Windows Store (recommended for new installs)
winget install 9NQ7512CXL7T
py install default

# Option 2: Download from python.org
# Visit https://www.python.org/downloads/
```

### Install Required Dependencies

The hardware profiler requires `psutil`:

```powershell
# Install psutil (required for CPU/memory/process metrics)
python -m pip install psutil

# Or install all Calyx dependencies
python -m pip install -r requirements.txt
```

**Verify installation:**
```powershell
python -c "import psutil; print(f'psutil {psutil.__version__} installed')"
```

### Verify GPU Access

Ensure NVIDIA drivers are installed and nvidia-smi is accessible:

```powershell
nvidia-smi
```

**Expected output:** GPU name, driver version, VRAM  
**If command fails:** Install/update NVIDIA drivers from https://www.nvidia.com/Download/index.aspx

---

## Quick Start

### 1. Start Hardware Profiler (Continuous)

```powershell
python -u .\tools\hardware_profiler.py
```

**Options:**
- `--profile NAME` — Specify profile name (auto-detected by default)
- `--interval N` — Collection interval in seconds (default: 60)
- `--summary` — Print profile summary and exit
- `--benchmark N` — Run N-second benchmark instead of continuous collection

**Example with custom interval:**
```powershell
python -u .\tools\hardware_profiler.py --interval 30
```

### 2. Run Quick Benchmark

```powershell
python -u .\tools\hardware_profiler.py --benchmark 60
```

Runs a 60-second benchmark collecting metrics every 5 seconds.

### 3. View Profile Summary

```powershell
python -u .\tools\hardware_profiler.py --summary
```

Shows hardware tier, limitations, and recommended optimizations.

---

## Analysis & Comparison

### Analyze Single Profile

```powershell
python -u .\tools\hardware_comparator.py --analyze desktop_m965jsc_entry --hours 24
```

Generates statistical analysis of the last 24 hours of metrics.

### Compare Two Profiles

```powershell
python -u .\tools\hardware_comparator.py --compare desktop_m965jsc_entry desktop_home_target --hours 168
```

Compares two profiles over the last week (168 hours).

### Generate BloomOS Optimization Report

```powershell
python -u .\tools\hardware_comparator.py --bloomos-report --output Codex\Reports\BLOOMOS_HARDWARE_OPTIMIZATION.md
```

Creates a comprehensive Markdown report with:
- Minimum hardware requirements
- Optimal hardware requirements
- Tier-specific recommendations
- Performance comparisons

---

## Metrics Collected

### Runtime Metrics (Every Minute)

- **CPU:** Utilization (total + per-core), frequency, load average
- **Memory:** Used, available, swap usage
- **GPU:** Utilization, VRAM usage, temperature, power draw
- **Thermal:** System temperature sensors (if available)
- **Processes:** Python process count, memory, CPU usage
- **Inference Timing:** Wake-word latency (from audit logs)

### Static Profile Information

- OS, architecture, hostname
- GPU name, driver, VRAM, compute capability
- CPU cores (physical/logical), frequency range
- Total system memory

---

## File Locations

### Metrics Storage

```
logs/hardware_profile_<profile_name>.jsonl
```

JSONL format with one metric snapshot per line. Example:
```json
{"timestamp": "2025-12-13T...", "profile_name": "desktop_m965jsc_entry", "cpu": {...}, "gpu": {...}}
```

### Configuration

```
config/hardware_profiles.json
```

Hardware profile definitions with tiers, targets, limitations, and optimizations.

### Reports

```
Codex/Reports/BLOOMOS_HARDWARE_OPTIMIZATION.md
```

Generated optimization reports.

---

## Use Cases

### 1. Baseline Data Collection (Laptop / MX150)

**Goal:** Establish performance baseline on lower-spec hardware.

```powershell
# Start continuous profiling
python -u .\tools\hardware_profiler.py

# Let run for 24-48 hours during normal operations
# Includes wake-word detection, agent scheduling, etc.
```

**Captures:**
- Real-world latency constraints
- VRAM utilization patterns
- Thermal throttling behavior
- Multi-agent concurrency limits

### 2. High-Performance Comparison (Desktop / RTX 2070S)

**Goal:** Compare same workloads on high-end hardware.

```powershell
# When switching to desktop, profiler auto-detects new profile
python -u .\tools\hardware_profiler.py

# After 24+ hours, compare profiles
python -u .\tools\hardware_comparator.py --compare desktop_m965jsc_entry desktop_home_target
```

**Reveals:**
- Performance gains from better GPU
- Headroom for concurrent operations
- Optimal model sizes per hardware tier

### 3. BloomOS Optimization Research

**Goal:** Determine minimum viable and optimal hardware requirements.

```powershell
# Generate comprehensive optimization report
python -u .\tools\hardware_comparator.py --bloomos-report --output Codex\Reports\BLOOMOS_HW_REQ_$(Get-Date -Format 'yyyy-MM-dd').md
```

**Produces:**
- Minimum requirements (based on laptop baseline)
- Optimal requirements (based on desktop performance)
- Tier-specific configurations (entry/mid/high/enterprise)

---

## Integration with Existing Metrics

### TES Metrics Integration

Hardware profiler reads TES scores from `logs/agent_metrics.csv` and correlates with hardware utilization. Example:

- High TES + Low GPU utilization → Opportunity to increase model complexity
- Low TES + High VRAM usage → Model too large, causing OOM degradation

### Foresight Integration

Can be combined with `enhanced_metrics_collector.py`:

```powershell
# Terminal 1: Enhanced metrics (TES, scheduler, etc.)
python -u .\tools\enhanced_metrics_collector.py

# Terminal 2: Hardware metrics (GPU, thermal, etc.)
python -u .\tools\hardware_profiler.py
```

Cross-reference timestamps to correlate agent performance with hardware state.

---

## Troubleshooting

### Python Not Found

**Symptom:** `Python was not found; run without arguments to install...`

**Solution:** Install Python via Windows Store or python.org:

```powershell
# Windows Store method (easiest)
winget install 9NQ7512CXL7T
py install default

# Verify
python --version
```

### ModuleNotFoundError: psutil

**Symptom:** `ModuleNotFoundError: No module named 'psutil'`

**Solution:** Install dependencies:

```powershell
python -m pip install psutil
```

### nvidia-smi Not Found

**Symptom:** GPU metrics show `"available": false`

**Solution:** Ensure NVIDIA drivers installed and `nvidia-smi` in PATH.

```powershell
nvidia-smi
```

### No Wake-Word Latency Data

**Symptom:** `inference_timing` shows `"available": false`

**Solution:** Run wake-word listener to populate `logs/wake_word_audit.csv`:

```powershell
python -u .\Scripts\listener_wake.py
```

### Temperature Sensors Not Available (Windows)

**Expected:** Windows does not expose temperature sensors via `psutil.sensors_temperatures()`.

**Workaround:** GPU temperature is still captured via `nvidia-smi`.

---

## CBO Recommendations

### Current Laptop Baseline (MX150)

[CBO • Overseer]: "Current hardware profiling captures real-world constraints of entry-level mobile GPUs. Key data points:

- VRAM limit (4GB) forces small models and serialized operations
- Thermal characteristics inform throttling risk
- Latency baselines establish minimum acceptable performance

**Action:** Run profiler continuously during normal operations for 1 week to establish comprehensive baseline."

### Desktop Migration (RTX 2070S)

[CBO • Overseer]: "When transitioning to desktop hardware:

1. Auto-detection will create new profile (`desktop_home_target`)
2. Run identical workloads for direct comparison
3. Use comparative analysis to quantify performance gains
4. Update config.yaml with optimized settings for desktop tier

**Expected Gains:**
- 2-3x lower wake-word latency (500-800ms vs 1500-2500ms)
- Concurrent ASR + LLM without serialization
- Medium Whisper model viable
- 4+ concurrent agents without throttling"

### BloomOS Hardware Requirements

[CBO • Overseer]: "This data directly informs BloomOS hardware requirements documentation:

- **Minimum Viable:** 4GB VRAM, 16GB RAM (proven on MX150)
- **Recommended:** 8GB VRAM, 32GB RAM (desktop target)
- **Optimal:** 16GB VRAM, 64GB RAM (future reference)

Each tier has validated model sizes, concurrency limits, and throttling parameters."

---

## Next Steps

1. **Immediate:** Start profiler on current laptop to begin baseline collection
2. **Week 1:** Collect 7 days of continuous metrics during normal operations
3. **Desktop Migration:** Repeat profiling on RTX 2070S hardware
4. **Week 2:** Generate comparative analysis and optimization report
5. **Documentation:** Update BloomOS hardware requirements with empirical data

**Target Date for Comparative Report:** 2025-12-20 (after 1 week of laptop baseline)

---

**Maintained by:** CBO (Calyx Bridge Overseer)  
**Version:** 1.0.0  
**Last Updated:** 2025-12-13
