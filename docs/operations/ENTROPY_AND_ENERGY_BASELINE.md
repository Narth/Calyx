# Entropy and Energy Baseline — Station Calyx

**Purpose:** Report how much entropy (hardware load) an action commits; establish a baseline for safe energy transfer. Maxing entropy burns energy; we throttle.

**Principle:** Anything above 50% CPU is high-priority / energy-intensive. Anything above 70%, even on a cadence, is unacceptable when repeated. We report entropy so the Station and agents can make activity decisions.

---

## Thresholds (Architect directive)

| CPU | Tier | Meaning |
|-----|------|---------|
| &lt; 50% | pass | Safe energy transfer; baseline breathing |
| 50–70% | high | Energy-intensive; proceed with awareness |
| ≥ 70% | unacceptable | Repeated cadence = burning energy; throttle |

---

## Entropy reporting

**station_health.json** now includes:

- **entropy** — Current tier (pass | high | unacceptable), baseline (rolling median of last 60 samples), and cadence (how many of last 60 samples hit ≥70%)
- **entropy_sources** — Top processes by current CPU % (who is committing entropy). Per-process CPU is capped at 100% for decision-making (multi-core can report 700%+; 100% = max allowed throughput). `cpu_pct_raw` present when raw exceeds 100 (diagnostics).
- **baseline_cpu** — Rolling median when "at rest"; used to compute delta above baseline

**Baseline:** Median of last 60 CPU samples. Represents "idle" when no heavy input. Delta = current − baseline = entropy above rest.

---

## Attribution (outside Architect-directed requests)

Processes that commonly stress the system without explicit Architect request:

- **CorsairCpuIdService** — Corsair hardware/RGB; can spike
- **SearchIndexer** — Windows search indexing
- **AntimalwareServiceExecutable** — Defender scans
- **Ollama** — Model loaded but idle; background
- **Discord** — Notifications, presence
- **Cursor** — Mixed: user + agent; when idle, still has background work

**Action:** Report `entropy_sources` so we see who is burning energy. Agents and humans can decide: is this Architect-directed, or background we should throttle?

---

## Safe energy transfer

- **Baseline** — Establish via rolling median. When current &lt; baseline + 20%, we're in "safe transfer" zone.
- **Budget** — (Future) Cap total entropy per minute; reject or defer actions that would exceed.
- **Cadence gate** — If `cadence_70` (samples ≥70% in last 60) &gt; 10, we're repeatedly maxing; patch_readiness and Navigator both defer/pause. No bulk or frequent 100% usage.

---

## Patch readiness gate

**Scripts/patch_readiness.ps1** — entropy-aware pre-check before patches and repairs.

- Reads `station_health.json` if present and recent (< 120s); else falls back to build_safety_check.
- **Ready** when: `entropy_tier != unacceptable` and `health != fail`.
- **-Strict:** also require `entropy_tier=pass` (reject "high").
- **Exit 0** = ready; **exit 1** = defer (reason printed).

Usage: run before patch/repair scripts; if exit 1, defer and re-run when entropy allows.

---

## Patch delivery wiring (items 2–5)

Full wiring plan for minimal sunrise, standalone repair, deferred queue, single-service restart: **docs/operations/PATCH_DELIVERY_WIRING_PLAN.md**.

---

## Carbon intensity (Electricity Maps)

**Scripts/carbon_intensity.ps1** — Fetches real-time carbon intensity (gCO2eq/kWh) from Electricity Maps API. Writes `runtime/carbon_intensity.json`. Navigator includes carbon in its lock. Power window: clean (≤200), mixed (201–400), dirty (>400). See **docs/operations/CARBON_INTENSITY_INTEGRATION.md**.

---

## References

- `docs/operations/CARBON_INTENSITY_INTEGRATION.md` — Electricity Maps integration
- `docs/operations/PATCH_DELIVERY_WIRING_PLAN.md` — wiring plan for items 2–5
- `Scripts/patch_readiness.ps1` — patch readiness gate (entropy + health)
- `Scripts/station_health_loop.ps1` — writes entropy to station_health.json
- `Scripts/update_state_checks.ps1` — merges entropy_tier into STATE.md on heartbeat
- `STATE.md` — BloomOS reads entropy_tier; act on entropy_tier=unacceptable
- `docs/operations/STATION_HEALTH_BLOOMOS_AUDIT.md` — health loop audit
- `docs/HARDWARE_OPTIMIZATION.md` — CPU/GPU levers
