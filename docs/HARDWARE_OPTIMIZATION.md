# Hardware Optimization (CPU vs GPU)

**Purpose:** Reduce CPU load and thermal stress when CBO (OpenClaw + Ollama) and GPU-heavy workloads run. Align with Lane 2 moratorium and determinism where applicable.

**Safe Travels (50% CPU target):** Station Calyx shoots for 50% CPU at all times. Under 40% = allow ML to reach target. Over 60% = hold back. Over 75% = pause. Preserves hardware life; quality of outputs improves when operating in the 40–60% zone. See `docs/operations/STATION_CALYX_OPERATIONAL_DOCTRINE.md` §4.1.

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
- **Limit Ollama CPU threads:** `OLLAMA_NUM_THREADS=4` (or 2) reduces CPU thread contention. **Important:** Ollama reads env when *it* starts, not from OpenClaw. Set in Windows user env (or start Ollama from a shell that has the var) and restart Ollama so it takes effect.
- **CPU affinity (4+4 split):** `Scripts\set_ollama_affinity.ps1` pins Ollama to cores 4-7; cores 0-3 reserved for Station Calyx and everything else. Run at sunrise; if Ollama not yet started, run manually after starting Ollama.
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
   - Under "User variables", add or edit `OLLAMA_NUM_THREADS` = `4` (for 4-core allocation).
   - Close Ollama from the system tray, then start Ollama again (tray or Start menu).
2. **Option B:** Start Ollama from PowerShell with the var set: close Ollama, then run
   `$env:OLLAMA_NUM_THREADS=2; ollama serve`
   (or your usual Ollama start command) so the child process inherits it.

Restarting only the OpenClaw gateway does **not** pass these variables to Ollama.

---

## Calyx Core services (reducing CPU during major operations)

The CBO Hub (Dev Harness, CBO Core, Avatar Web, Telemetry Gateway) runs one process per service with **one uvicorn worker each** (default). No multi-worker; that keeps CPU and memory lower.

**Tunable env (CBO Core):**

| Env | Default | Effect |
|-----|---------|--------|
| `CBO_STATE_CACHE_SEC` | `30` | Seconds to cache STATE.md in memory. Reduces disk reads when many requests inject STATE (second_opinion, local). Set `0` to disable cache (always read from disk). |
| `CBO_TOOL_LOOP_MAX` | `3` | Max tool executions per request (1–5). Lower (e.g. `2`) reduces Dev Harness calls and CPU when tools are on. |

**Recommendations when CPU is peaking:**

1. **Ollama (see above):** Set `OLLAMA_NUM_THREADS=2` (or 4) in Windows user env and restart Ollama.
2. **Calyx Core:** Ensure only one instance of each service; no extra workers. Optional: set `CBO_STATE_CACHE_SEC=60` and `CBO_TOOL_LOOP_MAX=2` in the environment before starting CBO Core (or in `.env.cbo`) to reduce per-request work.
3. **Avoid running** heavy Ollama + full tool ladder (architect/workhorse/second_opinion/local) + Telemetry Gateway under load at the same time if the machine is resource-constrained. Stagger or use smaller models.

---

## References

- OpenClaw + Ollama: `docs/OPENCLAW_CALYX_INTEGRATION.md`
- OpenClaw env: `~/.openclaw/.env` (used by gateway; for Ollama to see OLLAMA_*, set them in Windows env or when starting Ollama)
- Governance: `docs/governance/DETERMINISM_POLICY_v0.1.md`, `docs/governance/LANE2_TOOL_MORATORIUM_v0.1.md`
