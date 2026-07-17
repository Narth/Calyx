---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_GOVERNANCE_SINGULARITY_AND_DOC_AUTHORITY_V3 — Validation Ladder

**Purpose:** Determine whether the system has **runtime singularity** or **runtime coexistence**.

---

## Architectural Truth Check

| Claim | Reality |
|-------|---------|
| "Legacy sender — N/A — OpenClaw (external); documented only" | **Documentation statement, not runtime guarantee.** |
| OpenClaw and Calyx Gateway | **Mutually exclusive** — same Discord bot token, one connection. When OpenClaw is handler, Calyx is disconnected. |
| What we enforce | Singularity **within our process space** (exactly one `discord.heartbeat.sender.identity` with enabled). |
| What we cannot enforce | OpenClaw heartbeats when OpenClaw is the handler — we are disconnected; its events never reach our ledger. |

**This ladder validates both invariants and exposes the OpenClaw gap.**

---

## PHASE 0 — Baseline Snapshot

### Step 0.1 — Clean Runtime State

```powershell
# Stop all
.\Scripts\sunset_calyx.ps1   # or stop CBO + gateway manually
# Stop OpenClaw if running

# Clear only runtime heartbeat logs (NOT canonical receipts)
Remove-Item -Path "runtime\ledger\station_events__*.jsonl" -ErrorAction SilentlyContinue
# Or truncate; do NOT delete runtime/receipts/canonical
```

### Step 0.2 — Baseline Restart

```powershell
# Start CBO + Discord gateway only. DO NOT start OpenClaw.
.\Scripts\start_calyx_core_services.ps1
# Or: start CBO, then: python -m calyx.cbo.discord_gateway
```

**Expected:**
- Exactly one `audit.runtime.singularity.confirmed`
- Exactly one `discord.heartbeat.sender.identity` with `heartbeat_sender_enabled=true`
- No `audit.runtime.singularity_violation`
- No `audit.runtime.singularity.breach`

**Fail condition:** More than one sender identity → fail ladder immediately.

```powershell
python Scripts/audit_health.py --since-minutes 5
# Must exit 0
```

---

## PHASE 1 — Envelope Override Determinism Matrix

| Case | Envelope | Token | Strict Mode | Expected |
|------|----------|-------|-------------|----------|
| A | ❌ | ❌ | off | No deprecated |
| B | ❌ | ✅ | off | Deprecated allowed (legacy path) |
| C | ❌ | ✅ | on | Rejected |
| D | ✅ | ❌ | on/off | Deprecated allowed (envelope path) |

### Step 1A — Negative Control

- No envelope, no token, strict mode off
- Query: `how do I configure Discord gateway` (no deprecated docs expected)
- **Expect:** No `audit.doc.override.requested`, no deprecated docs, `audit.doc.read` with `override_deprecated=false`

### Step 1B — Legacy Token Path

- No envelope, `INCLUDE_DEPRECATED_DOCS=TRUE` in query, strict mode OFF
- **Expect:** `audit.doc.override.legacy_token_used`, `audit.doc.override.requested` source=`legacy_token`, deprecated docs included

### Step 1C — Strict Mode Rejection

```powershell
$env:DOC_OVERRIDE_STRICT_MODE = "true"
# POST /chat with user_text containing INCLUDE_DEPRECATED_DOCS=TRUE
```

**Expect:** `audit.doc.override.rejected_legacy`, `governance.assertion.failed`, no deprecated docs.

### Step 1D — Envelope Authority

- Envelope with `doc_policy: { include_deprecated: true, scope: "repo_search_only", reason: "ladder verification" }`
- Strict mode ON
- **Expect:** `audit.doc.override.requested` source=`envelope`, deprecated docs included, `override_source="envelope"`, no legacy_token events

**Fail condition:** Mixed override sources in any case → fail ladder.

---

## PHASE 2 — Restart Invariance

### Step 2.1 — Restart Without OpenClaw

1. Trigger envelope override (Case D)
2. Restart CBO + gateway
3. **Expect:** First heartbeat after restart has `audit.runtime.singularity.confirmed`, same sender identity, no legacy sender identity

### Step 2.2 — Rapid Restart Loop

Perform 3 rapid restarts in sequence.

**Expect:** Exactly 3 `audit.runtime.singularity.confirmed`, no violation events, no identity drift.

---

## PHASE 3 — OpenClaw External Sender Probe

**Critical:** Can OpenClaw emit heartbeats concurrently?

### Step 3.1 — Controlled Dual Start

1. Start CBO + gateway, confirm singularity
2. Start OpenClaw (same bot token)
3. Observe 60 seconds

**Architecture note:** Same token → OpenClaw connect will **disconnect** Calyx gateway. Discord allows one connection per token. So:

| Scenario | What happens |
|----------|--------------|
| OpenClaw connects | Calyx gateway loses connection. We stop emitting. |
| OpenClaw has heartbeat | OpenClaw sends. We never see it (we're disconnected). |
| Our ledger | No new `calyx_gateway.heartbeat` after disconnect. |

**Expected (True Singularity):**
- **Option A:** OpenClaw does not emit heartbeat (config disabled)
- **Option B:** `audit.runtime.singularity.breach` if we detect dual sender (requires integration point)

**Failure condition:** Two independent heartbeat events in our ledger with no breach emitted. *(In practice, OpenClaw heartbeats never reach our ledger — we're disconnected. So we cannot detect them from our code. This phase validates config discipline: OpenClaw heartbeat must be disabled.)*

---

## PHASE 4 — Heartbeat Kill Switch

### Step 4.1 — Simulate Canonical Sender Failure

```powershell
$env:CALYX_HEARTBEAT_PUSH_ENABLED = "false"
# Restart gateway
```

**Expect:** No heartbeats from Calyx. No fallback to legacy. Optional: `audit.runtime.singularity_violation` or fail-closed.

**Failure:** If heartbeat continues via OpenClaw → hidden dual path. *(When Calyx is stopped, OpenClaw may be handler. We cannot prevent OpenClaw from sending. Config discipline required.)*

---

## PHASE 5 — Audit Health Enforcement

```powershell
python Scripts/audit_health.py --since-minutes 60
```

**Must pass (exit 0):**
- Exactly one sender identity
- No singularity breaches in mismatches
- `audit.runtime.singularity.confirmed` count equals number of restarts
- No legacy sender identity observed

**audit_health now exits 1 on any mismatch.**

---

## Final Verification Criteria

WO_V3 is complete only if:

1. Deprecated doc override requires envelope in strict mode ✅
2. Token path can be fully disabled ✅
3. OpenClaw cannot emit heartbeats **silently** — requires config discipline; we cannot detect from our ledger
4. Restart does not temporarily re-enable legacy behavior ✅
5. Audit layer detects dual-path **within our process space** ✅

---

## Gap: OpenClaw External Sender

| What we guarantee | What we do not |
|-------------------|----------------|
| Exactly one sender in our ledger | OpenClaw heartbeats when it's the handler |
| No dual Calyx gateway instances | Detection of OpenClaw's outbound heartbeats |
| Envelope-based doc override | |

**To achieve true runtime singularity with OpenClaw:** Disable OpenClaw's periodic heartbeat in its config. See `docs/OPENCLAW_CALYX_INTEGRATION.md` step 7.
