# Station Calyx — Working Memory

## Architect
Primary human operator: Architect (Jorge / Narth)

## Current Phase
Energy Telemetry & Power Governance Research (E3–E5)

## Recent Major Work (2026-02-09 → 2026-02-10)
- Multi-scenario energy telemetry executed:
  - Scenario A: Controlled AC intake baseline
  - Scenario B: Manual sunset / sunrise
  - Scenario C: Abrupt power loss + recovery
  - Scenario D: Network stability (home vs hotspot)
- Energy phases completed:
  - E3: Drain rate observation
  - E4: Energy budget advisory
  - E5a: Advisory-only decision engine
  - E5b-OBS: Full-charge boundary observation (ongoing)
- Strong emphasis on:
  - Observation-only telemetry
  - No mitigation or automation without confidence
  - Explicit marking of temporal validity vs provisional data

## Key Constraints
- Laptop battery health is degraded; prior inflation suspected
- Power sources may be unstable (extensions, hotspot usage)
- Tooling limits reached in Visual Studio → migrated to Cursor
- Human primacy and HALT discipline strictly enforced

## Current Focus
- Observe behavior at or near 100% charge
- Detect charging oscillation, trickle intake, or instability
- Do NOT recommend action or infer risk without evidence

## Explicit Non-Goals
- No automation enactment
- No daemon restarts unless explicitly directed
- No policy enforcement changes yet
