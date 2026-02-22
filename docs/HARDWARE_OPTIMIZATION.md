# Hardware Optimization (CPU vs GPU)

**Purpose:** Reduce CPU load and thermal stress when CBO (OpenClaw + Ollama) and GPU-heavy workloads run. Align with Lane 2 moratorium and determinism where applicable.

---

## Observed behavior (2026-02-17)

- **Goal:** Offload AI/tooling/reasoning from CPU to GPU where possible.
- **Benchmarks (PyTorch vs NumPy 10k×10k matrix multiply):**
  - GPU: ~1.2 s, GPU ~100%, VRAM ~7.5 GB (8 GB card).
  - CPU: ~12.5 s, CPU 100%.
- **Issue:** During runs (including “GPU” runs), **CPU still reaches 100% in the second half** and stays there until the task finishes.

---

## Two different sources of CPU load

### 1. When CBO is working (Discord, tools, replies)

The main workload is **Ollama LLM inference** (e.g. `qwen3:8b`). Even with the model on GPU:

- Tokenization, sampling, KV-cache coordination, and result handling are **CPU-bound**.
- So “prompting CBO” will always involve non-trivial CPU use; the lever is to **maximize GPU use and cap CPU contention**.

**Levers:**

- **Confirm GPU usage:** While CBO is replying, run `ollama ps` and check that the model is using the GPU (and that VRAM is in use).
- **Limit Ollama CPU threads:** `OLLAMA_NUM_THREADS=2` (or 4) reduces CPU thread contention. **Important:** Ollama reads env when *it* starts, not from OpenClaw. Set in Windows user env (or start Ollama from a shell that has the var) and restart Ollama so it takes effect.
- **Existing GPU env:** `OLLAMA_NUM_GPU=1`, `OLLAMA_CUDA=1`, `OLLAMA_MAX_LOADED=1` are already set; keep these.
- **Context size:** Larger `OLLAMA_NUM_CTX` increases memory and can increase CPU work; keep at 32K only if needed.

### 2. When running synthetic GPU benchmarks (e.g. PyTorch matmul)

If CPU still spikes in the **second half** of a GPU-only benchmark:

- **Possible causes:** CPU↔GPU data transfer, Python/CUDA driver cleanup, or other processes (Ollama, Discord, IDE) waking up.
- **Isolation test:** Run a minimal GPU matmul script with other apps (and CBO) idle; watch Task Manager and `nvidia-smi`. If CPU still spikes, the cost is likely PyTorch/CUDA overhead or transfer.
- **Mitigation:** Smaller matrices (e.g. 5k×5k), tensors created on device (`device='cuda'`), avoid unnecessary `.cpu()` or numpy round-trips; use `torch.cuda.synchronize()` only when measuring so the main work stays on GPU.

---

## Recommendations

1. **For “CPU maxed when CBO is working”:** Treat Ollama as the primary source. Verify GPU usage with `ollama ps`; tune `OLLAMA_NUM_THREADS` (e.g. 2–4); avoid running other heavy CPU work while CBO is active.
2. **For “CPU maxed during GPU benchmarks”:** Run a small, GPU-only benchmark in isolation; if CPU still spikes, document as PyTorch/CUDA overhead and prefer smaller batches or fewer round-trips.
3. **Defer** broader GPU-offload work (federated telemetry parsing, GDH GPU hashing, etc.) until the CPU spike during normal CBO use is understood and, where possible, reduced.
4. **Monitoring:** Use `nvidia-smi` and Task Manager (or equivalent) to compare CPU/GPU during (a) CBO replies and (b) standalone PyTorch runs.

---

## Applying OLLAMA_* on Windows

`~/.openclaw/.env` is loaded only by the **OpenClaw gateway**. The **Ollama** process is separate (tray or service) and gets its environment when *Ollama* starts — it does **not** read the OpenClaw .env file. So for `OLLAMA_NUM_THREADS=2` to take effect:

1. **Option A (recommended):** Set the variable in Windows user environment.
   - `Win + R` → `sysdm.cpl` → Advanced → Environment Variables.
   - Under "User variables", add or edit `OLLAMA_NUM_THREADS` = `2`.
   - Close Ollama from the system tray, then start Ollama again (tray or Start menu).
2. **Option B:** Start Ollama from PowerShell with the var set: close Ollama, then run  
   `$env:OLLAMA_NUM_THREADS=2; ollama serve`  
   (or your usual Ollama start command) so the child process inherits it.

Restarting only the OpenClaw gateway does **not** pass these variables to Ollama.

---

## References

- OpenClaw + Ollama: `docs/OPENCLAW_CALYX_INTEGRATION.md`
- OpenClaw env: `~/.openclaw/.env` (used by gateway; for Ollama to see OLLAMA_*, set them in Windows env or when starting Ollama)
- Governance: `docs/governance/DETERMINISM_POLICY_v0.1.md`, `docs/governance/LANE2_TOOL_MORATORIUM_v0.1.md`
