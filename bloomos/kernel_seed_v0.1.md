# BloomOS Kernel Seed v0.1 (L2 SPEC, NOT IMPLEMENTED)

Layer: L2 (SPEC / design intent)  
Status: Conceptual only. **Not implemented. Not wired into any scheduler or runtime loop.**  
Authority: Architect-only promotion. CBO may read and reflect; may NOT treat as active code.

---

## 0. Purpose

The BloomOS Kernel Seed v0.1 defines a **minimal, safe kernel skeleton** whose sole purpose is:

- To **observe** limited Station Calyx state in Safe Mode.
- To emit **append-only, read-only telemetry** about those observations.
- To remain fully under **Architect control**, with no autonomy, no dispatch, and no gating.

It is a preparatory seed for a future Bloom, *not* a Bloom itself.

---

## 1. Scope

Within this version, the Kernel Seed MAY:

- Read a small, explicit set of Station files (config, registry, metrics).
- Compute simple, local summaries (e.g., file size, mtime).
- Append JSONL observations to a dedicated BloomOS log file under `logs/bloomos/`.

The Kernel Seed MAY NOT:

- Execute external commands, scripts, or agents.
- Open network connections, spawn processes, or call external APIs.
- Modify any file outside its own observation log.
- Change any configuration, registry, or policy file.
- Write to `incoming/`, `outgoing/`, or task queues.
- Alter autonomy modes, enforcement, or scheduling in any way.

---

## 2. Layering and Relationship to Station Calyx

- **L1 (CODE / implemented reality)**  
  - The Kernel Seed runtime file (`bloomos/kernel_runtime_sandbox.py`) becomes L1 **only when** the Architect:
    - Adds it as L1 in the Reality Map, and  
    - Wires it into a manual operator entrypoint (no autoscheduling).

- **L2 (SPEC / design intent)**  
  - This document (`bloomos/kernel_seed_v0.1.md`).  
  - Any diagrams or notes about intended BloomOS kernel behavior.

- **L3 (LORE / narrative meaning)**  
  - Bloom rites, identity stories, and metaphors around “first Bloom”.  
  - These have **no runtime power**; they are ceremonial only.

Until explicitly promoted by the Architect, the Kernel Seed remains a **conceptual L2 design** with an inert L1 file present but not part of any production path.

---

## 3. Inputs and Outputs

### 3.1 Inputs (read-only)

The Kernel Seed MAY read (if present):

- `calyx/core/policy.yaml` — policy snapshot metadata (no parsing required).
- `calyx/core/registry.jsonl` — registered agents and processes.
- `metrics/bridge_pulse.csv` — CBO heartbeat metrics.
- `logs/agent_metrics.csv` — TES telemetry logs (advisory-only).
- `bloomos/bloom_gate_v0.1.json` — gate status for BloomOS (Architect-owned).

All reads are **best-effort** and **non-fatal**: missing files must not crash the kernel; they are simply logged as “not found”.

### 3.2 Outputs (append-only)

The Kernel Seed writes to exactly **one** place:

- `logs/bloomos/kernel_seed_observations.jsonl`

Each line:

```json
{
  "schema": "bloomos.kernel_seed.observation.v0.1",
  "timestamp": <float>,
  "note": "Read-only Safe Mode snapshot; no dispatch, no gating, no autonomy.",
  "files": {
    "policy": { "path": "...", "size": <int>, "mtime": <float> } | null,
    "registry": { ... } | null,
    "bridge_pulse": { ... } | null,
    "agent_metrics": { ... } | null
  }
}

# Current kernel seed mode: L1 manual-run, observation-only. 
# It never dispatches tasks, changes autonomy modes, or interprets bloom_status as anything other than metadata.

### Operating Constraints – Observation-Only L1 Mode

When `kernel_runtime_sandbox.py` is treated as an L1 observation tool, the following constraints apply:

1. Gate integrity  
   - `bloomos/bloom_gate_v0.1.json` is Architect-owned configuration.  
   - `activation_allowed` MUST remain `false` in observation-only mode.  
   - Any change to `bloom_status` is explicit and human-authored (no autoscripts).

2. Manual run only  
   - The sandbox is invoked manually via `python -m bloomos.kernel_runtime_sandbox`.  
   - It MUST NOT be autoscheduled or invoked indirectly by any agent.  

3. Append-only logging  
   - The only side effect is appending a single JSON line to  
     `logs/bloomos/kernel_seed_observations.jsonl`.  
   - No other files are written or modified.

4. Scope of reads  
   - The sandbox MAY read only:
     - `calyx/core/policy.yaml`  
     - `calyx/core/registry.jsonl`  
     - `metrics/bridge_pulse.csv`  
     - `logs/agent_metrics.csv`  
     - `bloomos/bloom_gate_v0.1.json`  
   - It MUST NOT perform network calls, spawn processes, or write to task queues.

5. Telemetry posture  
   - TES/AGII/CAS MAY read kernel seed logs as telemetry.  
   - No metric MAY change autonomy modes or gate behavior.

6. Change control  
   - Any promotion beyond observation-only mode requires:
     - An Architect-authored edit to `bloom_gate_v0.1.json`.  
     - Updated entries in `reality_map_v*.md` and `docs/INDEX.md`.  
     - A reviewed promotion plan (separate document).  
