# Archive — Non-Operational Legacy Code

Code under `/archive/` is **non-operational** and must not be imported by active modules.

- **CI:** Fails if any active code (outside archive) imports from `archive` or from missing namespaces (e.g. `station_calyx.core`).
- **Spine:** All execution flows through the canonical spine (Calyx Mail → Intent Artifact → Work Envelope → Contract → Execution → Receipts). Archived code is outside this path.

## legacy_cbo_coordinator

Former `calyx/cbo/coordinator/`: depended on `station_calyx.core` (intent_artifact, evidence, config, user_model, intent_gateway), which does not exist in this repo. Replaced by `calyx/cbo/intent_pipeline/` (spine Phase 3).

Do not import from `archive.legacy_cbo_coordinator` or any path under `archive/` in active code.
