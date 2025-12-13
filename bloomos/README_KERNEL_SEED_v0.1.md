# BloomOS Kernel Seed v0.1 - Runtime README

Layer: L2 (SPEC / operator documentation)  
Status: Experimental, Architect-owned.  

---

## What this is

This README explains how the **BloomOS Kernel Seed runtime sandbox** is intended to be used:

- As a **manual tool** for the Architect.
- To collect **read-only, append-only** snapshots of Station state.
- With **no dispatch, no autonomy, no gating**.

---

## Files

- L2 Spec: `bloomos/kernel_seed_v0.1.md`
- Gate config (L1 CONFIG, Architect-owned): `bloomos/bloom_gate_v0.1.json`
- Runtime sandbox (L1 CODE, experimental): `bloomos/kernel_runtime_sandbox.py`
- Output log (append-only): `logs/bloomos/kernel_seed_observations.jsonl`

---

## How to Run (Manual Only)

From the repo root, as the Architect:

```bash
python -m bloomos.kernel_runtime_sandbox
