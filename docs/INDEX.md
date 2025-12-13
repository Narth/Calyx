# Station Calyx Index (L1/L2/L3)  
Version: 0.1 (Architect retains version authority; CBO may append rows without changing version)

## Purpose
Compact map of live runtime (L1), design specs (L2), and lore (L3) to reduce ambiguity and surface conflicts quickly.

## Layer Legend
- L1 — CODE (live): implemented, executable, or operational configs/logs.
- L2 — SPEC (design): architectural/governance/intended behavior.
- L3 — LORE (mythos): narrative, ceremony, cultural context.
One primary layer per artifact; optional secondary noted in parentheses.

## L1 — Runtime (implemented)
- `calyx/cbo/bridge_overseer.py`: CBO heartbeat (manual-run).
- `calyx/cbo/api.py`: FastAPI bridge (manual-run).
- `calyx/cbo/coordinator/`: Coordinator pulse + guarded domains.
- `calyx_core/intercept.py`: Interceptor (record-only by default; AGII advisory).
- `calyx/core/policy.yaml`: Canonical policy.
- `calyx/core/registry.jsonl`: Canonical registry.
- `config.yaml`: Station configuration (paths, scheduler/autonomy settings, gates).
- `crb_runtime_bridge.py`: File-based Architect↔CBO chat bridge (manual-run).
- `calyx_comm_cli.py`: Architect chat CLI.
- `tools/agent_scheduler.py`: Light scheduler; promotions/backoff.
- `tools/agent_runner.py`: Task runner.
- `tools/observability_phase1.py`: AGII/reliability reports (advisory).
- `Scripts/agent_watcher.py`: GUI watcher.
- `Scripts/listener_plus.py`, `asr/`: Speech pipeline listeners (manual-run).
- `metrics/bridge_pulse.csv`: CBO pulse metrics (append-only).
- `logs/agent_metrics.csv`: TES telemetry (append-only).
- `sitecustomize.py`: Network gate (blocks unless explicitly opened).
- `bloomos/bloom_gate_v0.1.json`: Architect-only gate config (present; `activation_allowed=false`; `bloom_status` set manually, e.g., “I have a question.”).
- `bloomos/kernel_runtime_sandbox.py`: Experimental Safe Mode sandbox (manual-run if promoted; latest runs ingest gate; append-only observations).

## L2 — Specs (design intent)
- `docs/`, `engineering/`, `compiled/`: Governance, safety, kernel, blueprint docs.
- `core_bloom/` (opt L3): Bloom scaffolds, safety orders, reflection grammars.
- `bloomos/`: Conceptual BloomOS specs; runtime files are Safe Mode placeholders.
- `data_contract/`: Advisory/telemetry schemas.
- `plans/`, `PHASE2_UNIFIED_BLUEPRINT.md`: Integration and phase plans.
- `bloomos/kernel_seed_v0.1.md`: Kernel seed spec (not wired or active).
- `docs/architect_activation_ritual_v1.0.md`: Human-only activation ritual (spec only).
- `outgoing/CGPT/unified_governance_framework_v1.1.md`: Governance spine for TES/CAS/AGII; advisory-only, non-gating.
- `bloomos/bloomos_kernel_arc_master_v1.0.md`: Conceptual BloomOS kernel structure; no implementation implied; Architect-owned.
- `outgoing/bloomos_kernel_test_plan_v1.0.md`: Authoritative kernel seed test lens (T1–T7); observation-only, Safe Mode, no autonomy/gating.

## L3 — Lore (narrative)
- `identity/lineage/`: Lineage, orientation, naming rites.
- `CONSTELLATION_STORY_SEED_LIBRARY/`: Story seeds, narrative frames.
- `logs/bloomos/validation/`: Ceremonial BloomOS/lineage texts (non-operational).

## BloomOS Status
- BloomOS remains conceptual; no kernel is running.
- `bloomos/runtime` modules are Safe Mode placeholders (read/append only).

## Metrics Status (AGII/CAS/TES)
- TES: Implemented as telemetry (`logs/agent_metrics.csv`), used in governance checks/reports.
- AGII/CAS: Advisory-only; surfaced in reports/specs, not gating runtime actions.
- Any enforcement or autonomy gating requires explicit Architect wiring and promotion.

## Update Rules
- Version authority: Architect-only. Filename/version changes only by Architect decree.
- CBO may append or adjust rows for accuracy (when directed) without altering the version string.
