# STATION_MEMORY_LIFECYCLE_DOCTRINE_V1

## Intent
Station Calyx treats memory as a governed resource: observed, budgeted, and reclaimed safely.

## Principles
1. Memory is not a cache unless explicitly labeled.
2. Every buffer has a ceiling.
3. Reclamation emits a receipt.
4. Degrade before crash.
5. No silent restarts.

## Memory Classes
- M0: Critical State
- M1: Operational State
- M2: Caches
- M3: Observability Buffers
- M4: Ephemera

## Pressure Tiers and Response Levels
Tier 0: <70% — normal
Tier 1: 70–85% — trim caches
Tier 2: 85–95% — shed optional features
Tier 3: >95% — safe mode + pressure receipt
Tier 4: OOM imminent — controlled restart on explicit receipt

## Heartbeat Requirements
- heartbeat_emitted_ts
- station_boot_ts
- per-service pid, uptime, rss_mb
- memory_pressure_tier

## Prohibitions
- No unbounded segments
- No reused heartbeat timestamps
- No hidden restarts

## Compliance
- Budgets defined
- Tiers enforced
- Receipts emitted
- Heartbeat integrity verified
