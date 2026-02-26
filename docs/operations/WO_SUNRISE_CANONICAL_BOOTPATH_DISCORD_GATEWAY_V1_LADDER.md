---
status: active
owner: station
last_reviewed_utc: "2026-02-21"
doctrine_scope: governed
---

# WO_SUNRISE_CANONICAL_BOOTPATH_DISCORD_GATEWAY_V1 — Validation Ladder

**Purpose:** Confirm Station Sunrise is the single canonical boot path for all core services including Discord Gateway, with invariant checks active immediately after boot.

---

## System Invariants

| Invariant | Enforcement |
|-----------|-------------|
| One canonical executor path | `Scripts/sunrise_calyx.ps1` → `Scripts/start_calyx_core_services.ps1`; no manual `python -m calyx.cbo.discord_gateway` required |
| No untraceable boot events | Gateway starts with same gating/receipts as other services |
| Fail closed on ambiguity | External emitter gate + singularity checks must pass before claiming healthy |

---

## V1 — Fresh Sunrise from Sunset

### Step 1.1 — Sunset

```powershell
.\Scripts\sunset_calyx.ps1
```

### Step 1.2 — Sunrise

```powershell
.\Scripts\sunrise_calyx.ps1
```

**Expected:**
- Discord Gateway is started automatically (no manual step)
- `audit.runtime.singularity.confirmed` exists for this boot (in ledger)
- `audit_health` passes (exit 0) — sender identity checks, no external emitters
- External emitter gate passes (OpenClaw not detected)
- Sunrise receipt written to `runtime/receipts/sunrise_receipt__*.json` with `discord_gateway_started: true`, `audit_health_passed: true`

**Verification:**

```powershell
python Scripts/audit_health.py --since-minutes 5
# Must exit 0
```

---

## V2 — Restart Invariance

### Step 2.1 — Three Restart Cycles

```powershell
for ($i=1; $i -le 3; $i++) {
    Write-Host "Cycle $i"
    .\Scripts\sunset_calyx.ps1
    Start-Sleep -Seconds 3
    .\Scripts\sunrise_calyx.ps1
    if ($LASTEXITCODE -ne 0) { throw "Sunrise failed cycle $i" }
    Start-Sleep -Seconds 5
}
```

**Expected each cycle:**
- Exactly one `audit.runtime.singularity.confirmed` per boot
- No multiple sender identities
- No manual steps required
- Sunrise exits 0

---

## V3 — Forced Gateway Failure

### Step 3.1 — Simulate Gateway Start Failure

Option A: Port conflict (if gateway used a port, bind it first — Discord gateway typically does not; use Option B).

Option B: Temporarily break the module path so gateway fails to import:

```powershell
# Backup and break
Rename-Item -Path "calyx\cbo\discord_gateway.py" -NewName "discord_gateway.py.bak" -ErrorAction SilentlyContinue

.\Scripts\sunset_calyx.ps1
.\Scripts\sunrise_calyx.ps1

# Restore
Rename-Item -Path "calyx\cbo\discord_gateway.py.bak" -NewName "discord_gateway.py" -ErrorAction SilentlyContinue
```

**Expected:**
- Sunrise fails closed (exit non-zero)
- Emits `audit.runtime.component.failed` (discord_gateway) or equivalent in receipt
- Does not report healthy
- Receipt has `status: "failed"` or `discord_gateway_started: false`

---

## Definition of Done

- [ ] Running sunrise results in Discord Gateway running every time
- [ ] Heartbeat singularity confirmation is present on every sunrise
- [ ] Sunrise fails closed if Discord Gateway cannot start
- [ ] Post-sunrise `audit_health` confirms one sender identity and no external emitters

---

## Next Risk to Watch

If Discord Gateway is part of Sunrise, any alternate start method (`python -m calyx.cbo.discord_gateway` manually) should either:
- Be considered a debug-only path that emits `audit.runtime.manual_start`, or
- Be documented as deprecated to prevent "two boot paths" drift.
