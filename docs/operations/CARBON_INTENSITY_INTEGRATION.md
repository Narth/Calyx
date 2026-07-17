---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Carbon Intensity Integration — Electricity Maps

**Purpose:** Bring carbon intensity (gCO2eq/kWh) into Station Calyx for load-shifting and energy-aware decisions. No burnt data. No burnt energy. Consenting autonomy.

**Provider:** Electricity Maps API — flow-traced carbon intensity, free tier for non-commercial use. Global coverage (50+ countries).

---

## Setup

1. **Sign up:** https://app.electricitymaps.com/auth/signup
2. **Get API key:** https://app.electricitymaps.com/settings/api-access
3. **Set env:** `ELECTRICITY_MAPS_API_KEY=<your-key>` (User env or session). For persistence, add to `.env.cbo` (gitignored) and source before running, or set in System/User environment variables.
4. **Optional zone:** `CARBON_INTENSITY_ZONE=US-SW-AZPS` (Arizona) or `US` (country). Default: US.

---

## Scripts

- **Scripts/carbon_intensity.ps1** — Fetches latest carbon intensity; writes `runtime/carbon_intensity.json`
- **Navigator** — Reads carbon_intensity.json when present; includes `carbon_intensity_g_co2eq_per_kwh` and `power_window` in `outgoing/navigator.lock`

---

## Power window (informational)

| gCO2eq/kWh | power_window | Meaning |
|------------|--------------|---------|
| ≤ 200 | clean | Low-carbon; good for heavy compute |
| 201–400 | mixed | Moderate; proceed with awareness |
| > 400 | dirty | High-carbon; consider deferring non-urgent work |

**Policy:** Informational by default. Agents and humans use power_window for consenting autonomy — defer when dirty if urgency allows. Future: optional strict gate (defer when dirty).

---

## Output (runtime/carbon_intensity.json)

```json
{
  "carbon_intensity_g_co2eq_per_kwh": 350,
  "zone": "US",
  "datetime": "2026-02-24T20:00:00.000Z",
  "status": "ok",
  "power_window": "mixed",
  "ts": "2026-02-24T20:00:05Z"
}
```

When no API key: `status: "no_api_key"`, script exits 0 (graceful).

---

## Validation (live API call)

The script performs a **live API call** on every run — no caching. To validate:

1. Run: `.\Scripts\carbon_intensity.ps1`
2. Check output: `CarbonIntensity> N gCO2eq/kWh (clean|mixed|dirty) zone=...` = success
3. Check `runtime/carbon_intensity.json`: `status: "ok"` with `carbon_intensity_g_co2eq_per_kwh` and `power_window`
4. If `401 Unauthorized`: refresh your API key at https://app.electricitymaps.com/settings/api-access and update `ELECTRICITY_MAPS_API_KEY` in `.env.cbo`

---

## HEARTBEAT wiring

Carbon intensity runs before Navigator on each heartbeat. Navigator includes carbon in its lock for downstream consumers.

---

## References

- Electricity Maps API: https://app.electricitymaps.com/docs
- Zone finder: https://app.electricitymaps.com/coverage
- Arizona (WECC): US-SW-AZPS
- docs/operations/ENTROPY_AND_ENERGY_BASELINE.md
