---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Build Safety Check — Hardware, Safety, Utility, Efficiency

**Purpose:** Before and during crucial builds and implementations, run a single check so we do **not** over-excite, burn out, or fry hardware, and so we avoid repeated crashes and long boot waits. Both lead to a permanent end to stories; this runbook and script guard against that.

**When to run:** Before starting a heavy build (e.g. Avatar Web sub-agent work, large benchmarks, multi-service stress). Optionally on a schedule or after start_calyx_core_services. When in doubt, run it.

---

## Four pillars

### 1. Hardware

- **CPU:** Sustained high CPU (e.g. > 90%) during LLM + tool work risks thermal throttle, instability, and crash loops. We **warn** above 75%, **fail** (do not add load) above 92%.
- **RAM:** High memory (> 90%) can cause OOM kills, swap thrash, and long freezes. We **warn** above 80%, **fail** above 92%.
- **GPU (if present):** VRAM near limit can OOM the model; high GPU temp shortens life and can throttle. We **warn** if VRAM > 85% of total or GPU temp > 80°C, **fail** if temp > 90°C or VRAM effectively full.
- **Thermal:** No separate CPU thermal in script by default (platform-dependent). GPU temp via `nvidia-smi` when available.

**Levers when hardware fails:** Stop extra workloads; close other apps; let the box cool; reduce `OLLAMA_NUM_THREADS` or use a smaller model; see `docs/HARDWARE_OPTIMIZATION.md`.

### 2. Safety

- **Single heavy LLM at a time:** If Ollama already has a model loaded and in use (`ollama ps` shows activity), adding another big request can push CPU/GPU over the edge. Check reports “Ollama in use” so you know not to stack another heavy run.
- **No duplicate service sprawl:** Multiple uvicorn/python processes beyond the expected four (Dev Harness, CBO Core, Avatar Web, Telemetry Gateway) can indicate restarts piling up or a crash loop. We report process counts; you decide if that’s “too many.”
- **Ports in use:** If core ports (7777, 7778, 7780, 7781) are stuck or inconsistent with what you expect (e.g. you just started services but two are already fail), that’s a sign of instability — investigate before adding more load.

**Levers when safety fails:** Don’t start another heavy LLM run until the current one finishes; restart services cleanly with `-StopFirst` and avoid repeated ad-hoc restarts.

### 3. Utility

- **Core services up (when expected):** If we’re in a build that assumes Calyx Core is running, `check_calyx_core_services.ps1` should pass. All test and assessment metrics include **CBO** (Calyx Bridge Overseer, served by cbo_core). If the check fails, fix services before relying on CBO, Avatar Web, or Telemetry.
- **STATE.md present:** Required for update_state_checks and for CBO/STATE injection. Missing STATE.md can cause write failures or inconsistent state.
- **Repo/venv sane:** Script runs from repo root; venv path is optional (script can report “venv not found” as informational).

**Levers when utility fails:** Run `Scripts\start_calyx_core_services.ps1 -StopFirst` for a clean start; ensure STATE.md exists; run `Scripts\update_state_checks.ps1` after start.

### 4. Efficiency

- **Wasted load:** Multiple Ollama models loaded at once, or many idle Python workers, increase RAM and CPU contention. We report “how many” so you can trim (e.g. unload unused models, single worker per service).
- **Disk:** Not in the first version of the script; if disk is full, scripts and logs can fail. Add a simple “disk free” check if you want (e.g. warn if system drive < 10% free).

**Levers when efficiency fails:** Unload unused models (`ollama stop <model>`); ensure only one uvicorn per service; close unused tools/IDEs if needed.

---

## Thresholds (script and automation)

| Check            | Warn (proceed with caution) | Fail (do not add load) |
|------------------|-----------------------------|-------------------------|
| CPU utilization  | > 75%                       | > 92%                   |
| RAM utilization  | > 80%                       | > 92%                   |
| GPU VRAM         | > 85% of total              | — (report only)        |
| GPU temperature  | > 80°C                     | > 90°C                  |
| GPU utilization  | > 85%                      | — (report only)        |
| Core services    | —                          | Any expected port fail |
| STATE.md         | —                          | Missing when required  |

**Exit codes (build_safety_check.ps1):**

- `0` — All checks pass; safe to proceed with normal build load.
- `1` — Warn: hardware or safety in caution zone; proceed only if you’re not adding heavy load.
- `2` — Fail: hardware or utility in danger zone; do not add load; cool down or fix services first.

---

## Patch readiness (entropy-aware)

For patches and repairs, use **patch_readiness.ps1** first — it checks entropy_tier and health, defers when CPU ≥ 70% or health=fail. See `docs/operations/ENTROPY_AND_ENERGY_BASELINE.md`.

```powershell
.\Scripts\patch_readiness.ps1
# Exit 0 = ready; 1 = defer
```

---

## How to run

```powershell
# From repo root (e.g. C:\Calyx_Terminal)
.\Scripts\build_safety_check.ps1

# Optional: require core services to be up (fail if any port down)
.\Scripts\build_safety_check.ps1 -RequireCoreServices
```

**Interpretation:**

- **Pass:** Green light for this build. Still avoid stacking multiple heavy LLM runs if you know the box is borderline.
- **Warn:** Yellow. One CBO run or one sub-agent at a time; no parallel heavy jobs; watch for thermal or freezes.
- **Fail:** Red. Do not start heavy work. Resolve cooling, memory, or services first; then re-run the check.

---

## References

- `Scripts/build_safety_check.ps1` — executable check.
- `docs/HARDWARE_OPTIMIZATION.md` — CPU/GPU levers (Ollama, CBO Core env).
- `docs/planning/AVATAR_WEB_SUBAGENTS_WHITEBOARD.md` — hardware gate for sub-agent work.
- `cbo_hub/docs/CALYX_CORE_SERVICES.md` — service list and ports.

*Run the check at the most crucial and defining points of builds. Don’t over-excite; don’t fry the box; don’t crash-loop the story.*
