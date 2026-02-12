# BitNet Integration — Station Calyx Phase 2

**Status**: Operational (WSL2 Runtime)  
**Created**: 2026-01-05  
**Architect Authority**: Phase 2 Integration Approved

---

## Overview

BitNet integration provides Station Calyx with **local 1.58-bit LLM reasoning capability** via WSL2 Ubuntu runtime. This eliminates cloud dependency for language model inference while maintaining low resource footprint.

### Key Features

- **1.58-bit Quantization**: BitNet-b1.58-2B model at 3.91 BPW (1.2GB)
- **Local-First**: No network calls, runs entirely on local CPU
- **WSL2 Bridge**: Python agent wraps WSL2 execution for Windows interop
- **SVF Compliant**: Heartbeat emission, gate enforcement, config-driven
- **Low Footprint**: 22 tokens/sec on CPU, ~1.4GB RAM total

---

## Architecture

```
Windows (Station Calyx)
    ? config.yaml ? bitnet section
    ? Scripts/agent_bitnet.py (Python)
    ? subprocess ? wsl --distribution Ubuntu
        ? ~/bitnet_build/BitNet/build/bin/llama-cli
        ? models/BitNet-2B-official/ggml-model-i2_s.gguf
        ? BitNet kernels (ggml-bitnet-lut, ggml-bitnet-mad)
    ? stdout ? parse output
    ? emit heartbeat ? outgoing/agent_bitnet.lock
```

---

## Installation

### Prerequisites

1. **WSL2 Ubuntu** installed and functional:
   ```powershell
   wsl --list --verbose
   # Should show Ubuntu with VERSION 2
   ```

2. **BitNet compiled** in WSL2 (from Phase 1):
   ```bash
   # Inside WSL2
   cd ~/bitnet_build/BitNet
   ls build/bin/llama-cli  # Should exist
   ls models/BitNet-2B-official/ggml-model-i2_s.gguf  # Should exist
   ```

3. **Python dependencies** (already in Station Calyx):
   - PyYAML (for config.yaml parsing)
   - subprocess (built-in)

### Configuration

Edit `config.yaml`:

```yaml
bitnet:
  enabled: false  # Set to true to enable
  wsl_distribution: "Ubuntu"
  model_path: "~/bitnet_build/BitNet/models/BitNet-2B-official/ggml-model-i2_s.gguf"
  binary_path: "~/bitnet_build/BitNet/build/bin/llama-cli"
  default_threads: 4
  default_ctx_size: 4096
  default_n_predict: 50
  temperature: 0.8
  heartbeat_interval: 30
  timeout_sec: 120
```

### Gate Authorization

Edit `outgoing/gates/bitnet.ok`:

```json
{
  "enabled": true,
  "authorized_by": "Architect",
  "notes": ["Authorization granted for reasoning integration"]
}
```

---

## Usage

### Basic Inference

```powershell
# Simple prompt
python -u Scripts\agent_bitnet.py --prompt "Explain BitNet quantization"

# Custom parameters
python -u Scripts\agent_bitnet.py `
  --prompt "What is Station Calyx?" `
  --n-predict 100 `
  --temperature 0.5 `
  --threads 4
```

### Dry Run (Configuration Test)

```powershell
python -u Scripts\agent_bitnet.py --prompt "test" --dry-run
```

### Output Format

```
[Agent_BitNet • Reasoning]: Initializing...
[Agent_BitNet • Operational]: Gate OK
[Agent_BitNet • Inference]: Processing prompt...

======================================================================
[Agent_BitNet • Output]:
======================================================================
BitNet quantization is a 1.58-bit weight representation technique that...
(generated text continues)
======================================================================
```

---

## Performance Metrics

**Model**: BitNet-b1.58-2B (2.41B parameters)  
**Hardware**: WSL2 x86_64, AVX2, 4 threads  
**Metrics**:
- Prompt processing: 66.83 tokens/sec
- Generation: 22.08 tokens/sec
- Load time: 760ms
- Memory: 1.1GB model + 300MB KV cache

---

## Troubleshooting

### Gate Errors

```
[Agent_BitNet • Error]: Gate not found: outgoing/gates/bitnet.ok
```

**Solution**: Create gate file:
```powershell
New-Item -ItemType File -Path outgoing\gates\bitnet.ok -Force
# Edit JSON content to set "enabled": true
```

### WSL2 Not Found

```
[Agent_BitNet • Error]: WSL distribution 'Ubuntu' not found
```

**Solution**: Verify WSL2:
```powershell
wsl --list --verbose
wsl --set-default Ubuntu
```

### Model Path Invalid

```
[Agent_BitNet • Error]: cannot open model file
```

**Solution**: Verify path in WSL2:
```bash
wsl bash -c "ls ~/bitnet_build/BitNet/models/BitNet-2B-official/ggml-model-i2_s.gguf"
```

### Timeout Errors

```
[Agent_BitNet • Error]: Inference timeout (120s)
```

**Solution**: Increase timeout in config.yaml:
```yaml
bitnet:
  timeout_sec: 300  # 5 minutes
```

---

## Integration Points

### SVF Protocol

Agent BitNet emits heartbeats to `outgoing/agent_bitnet.lock`:

```json
{
  "agent": "agent_bitnet",
  "status": "inference",
  "timestamp": "2026-01-05T15:45:00Z",
  "message": "Prompt: Explain BitNet quantization...",
  "pid": "12345"
}
```

**Status values**: `starting`, `inference`, `complete`, `timeout`, `error`

### Watcher Integration

To add BitNet to Watcher UI:

1. Add icon entry to `outgoing/watcher_icons.json`:
```json
{
  "agent_bitnet": {
    "icon": "??",
    "color": "#4A90E2",
    "label": "BitNet"
  }
}
```

2. Restart Watcher to detect new agent

---

## Safety and Limits

### Gate Enforcement

- **Required**: `outgoing/gates/bitnet.ok` with `enabled: true`
- **Checked**: On every inference call
- **Bypass**: Not possible (hard-coded validation)

### Resource Limits

- **Max Tokens**: Configurable via `--n-predict` (default: 50)
- **Timeout**: 120 seconds (configurable)
- **Memory**: ~1.4GB per inference session
- **Concurrency**: Single-threaded (no parallel inference)

### Security Considerations

- **No Network**: BitNet runs entirely offline
- **WSL2 Isolation**: Separate filesystem namespace
- **Input Sanitization**: Prompt escaping via subprocess
- **No File Access**: Model files are read-only

---

## Future Enhancements

### Phase 2.5: Reasoning Layer Integration

```yaml
bitnet:
  reasoning:
    enabled: true
    confidence_threshold: 0.7
    svf_integration: true
    fallback_to_triage: true
```

**Capabilities**:
- Uncertainty detection ? route to CBO/Triage
- Confidence scoring for reasoning outputs
- SVF-tagged reasoning chains
- Integration with Navigator traffic flow

### Phase 3: Multi-Model Support

```yaml
bitnet:
  models:
    - name: "bitnet-2b"
      path: "~/bitnet_build/BitNet/models/BitNet-2B-official/ggml-model-i2_s.gguf"
      use_case: "general_reasoning"
    - name: "bitnet-3b"
      path: "~/bitnet_build/BitNet/models/bitnet_b1_58-3B/model.gguf"
      use_case: "complex_analysis"
```

---

## References

- **Phase 1 Report**: `Testing/BitNet_Evaluation/PHASE1_REPORT.md`
- **BitNet Repository**: https://github.com/microsoft/BitNet
- **Official Model**: https://huggingface.co/microsoft/BitNet-b1.58-2B-4T-gguf
- **Technical Paper**: https://arxiv.org/abs/2410.16144 (bitnet.cpp)

---

## Changelog

- **2026-01-05**: Phase 2 integration complete
  - WSL2 bridge functional
  - Gate system integrated
  - Config-driven operation
  - SVF heartbeat emission
  - COMPENDIUM.md entry added

---

**[CBO • Overseer]: BitNet integration documentation complete. Phase 2 operational.**
