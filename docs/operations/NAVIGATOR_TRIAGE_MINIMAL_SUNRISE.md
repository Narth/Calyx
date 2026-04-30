---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Navigator and Triage Orchestrator — Minimal Sunrise Design

**Purpose:** Design Navigator and Triage Orchestrator to operate with minimal sunrise (CBO Core + Telemetry Gateway only). Both are lightweight, health-aware, and respect entropy. Navigator wires first; Triage goes live after simulations or Architect review of Station health.

**Status:** Implemented. Navigator and Triage validated. Navigator wires first; Triage goes live after Architect review of Station health.

---

## Minimal Sunrise Modes

| Mode | Services | Ports | Use case |
|------|----------|-------|----------|
| `bridge` | CBO Core | 7778 | get_state, /chat, /sponsorship, /execute — no repo tools |
| `remote` | CBO Core, Telemetry Gateway | 7778, 7781 | Remote access via ngrok; Navigator/Triage when human away |
| `patch` | Dev Harness, CBO Core | 7777, 7778 | Patch delivery, spine, repo tools |
| `full` | All four | 7777, 7778, 7780, 7781 | Full sunrise |

**Navigator and Triage** require at least `bridge` (CBO Core). For remote operation: `remote` (CBO + Telemetry Gateway).

---

## Navigator (Traffic Navigator)

**Role:** Control/cadence modulation; hot/cool intervals and pause control. Operational; status-focused.

**Behavior:**
1. Run `patch_readiness.ps1`; if exit 1 → output `interval_status: pause`, defer, exit.
2. Read STATE.md (health, entropy_tier) and/or station_health.json.
3. Determine interval:
   - `entropy_tier=unacceptable` or `health=fail` → **pause** (cool; do not add load)
   - `entropy_tier=high` → **cool** (proceed with caution; no heavy work)
   - `entropy_tier=pass` and `health!=fail` → **hot** (safe for concentrated runs)
4. Write `outgoing/navigator.lock` (JSON: interval_status, entropy_tier, health, ts, recommendation).
5. Exit 0 when hot; 1 when pause; 2 when cool (callers can treat 1=block, 2=caution).

**Dependencies:** patch_readiness, station_health.json or STATE.md. No CBO Core required for local read (files only). If Navigator needs to signal remote clients, it may ensure minimal sunrise (remote mode) is up.

**Artifacts:** `outgoing/navigator.lock`

---

## Triage Orchestrator

**Role:** Probing health/latency/errors, tightening stability. Diagnostic and brief.

**Behavior:**
1. Run `patch_readiness.ps1`; if exit 1 → output `status: deferred`, write lock, exit.
2. Read station_health.json (health, entropy, top processes).
3. If CBO Core (7778) reachable: GET /state, measure latency.
4. Summarize: health, entropy_tier, checks (cbo_core at minimum), latency_ms, top_entropy_sources.
5. Write `outgoing/triage.lock` (JSON: status, health_summary, latency_ms, recommendations, ts).
6. Exit 0 when health=pass; 1 when warn; 2 when fail.

**Dependencies:** patch_readiness, station_health.json. CBO Core optional (for latency probe). Works with minimal sunrise (bridge or remote).

**Artifacts:** `outgoing/triage.lock`

---

## Safety Invariants

| Invariant | Navigator | Triage |
|-----------|------------|--------|
| Never add load when entropy_tier=unacceptable | ✓ Pause | ✓ Defer |
| Never add load when health=fail | ✓ Pause | ✓ Defer |
| Read-only (no writes except lock files) | ✓ | ✓ |
| No service startup (caller may run start_minimal) | ✓ | ✓ |
| patch_readiness gate before any probe | ✓ | ✓ |

---

## Wiring Order

1. **Navigator first** — Wire to Telemetry Gateway / minimal sunrise. Test with simulations.
2. **Triage second** — Goes live after Navigator validated and Architect reviews Station health post-implementation.

---

## Test Plan

1. **Unit (simulation):** Run Navigator/Triage with mock station_health.json (pass, warn, fail, unacceptable). Verify output and exit codes.
2. **Integration:** With Station up (full or minimal), run both. Verify lock files, no service disruption.
3. **Safety:** Run when entropy_tier=unacceptable; verify both defer/pause and do not add load.
4. **Minimal sunrise:** Start remote mode only; run Navigator; verify it operates without Dev Harness/Avatar Web.

---

## Scripts

- `Scripts/start_minimal.ps1` — minimal sunrise by mode (bridge, remote, patch, full)
- `Scripts/navigator.ps1` — Navigator; writes outgoing/navigator.lock
- `Scripts/triage_orchestrator.ps1` — Triage; writes outgoing/triage.lock
- `Scripts/test_navigator_triage.ps1` — simulation test suite

## References

- `Scripts/patch_readiness.ps1`
- `docs/operations/PATCH_DELIVERY_WIRING_PLAN.md`
- `docs/operations/ENTROPY_AND_ENERGY_BASELINE.md`
- `COMPENDIUM.md` — Navigator, Triage Orchestrator
