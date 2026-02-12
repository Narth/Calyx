# Exit Guarantee v1 (EG-1)

**Station Calyx / AI-for-All**

**Status:** ACTIVE  
**Declared:** 2026-01-26  
**Authority:** Human (Architect)  
**Classification:** Foundational Governance Artifact

---

## Constraints on This Document

| Constraint | Description |
|------------|-------------|
| **Non-derivable** | This guarantee is not inferred; it is explicitly declared by a human |
| **Non-conditional** | The user's right to exit is not contingent on any condition |
| **Non-retaliatory** | Exiting must not trigger any punitive action or data exposure |
| **Append-only** | Future versions may only strengthen this guarantee, never weaken it |

---

## Purpose

This document guarantees that users who adopt Station Calyx can leave at any time, for any reason, taking everything that is theirs and leaving nothing behind. There is no lock-in, no hostage data, no penalty for departure.

**Station Calyx must never become a cage.**

---

## The Guarantee

### You May Leave

At any time, for any reason, without explanation, you may stop using Station Calyx. Your decision is final and requires no justification.

### You Take Everything

All data you created, all configurations you made, all history you accumulated—it is yours. When you leave, you may take all of it in standard, open formats that do not require Station Calyx to read.

### You Leave Nothing

When you choose to exit, you may execute a complete purge that removes all traces of Station Calyx from your system. No hidden caches, no buried logs, no phantom processes. A clean exit is a complete exit.

### No Penalty

Your departure triggers no:
- Degradation of remaining functionality during transition
- Exposure of your data to any third party
- Notification to any external service about your departure
- Reduction in service quality for any "grace period"
- Requests for explanation or "exit interviews"

---

## Exit Procedures

### Graceful Exit (Recommended)

For users who want to preserve their data before leaving:

```
calyx export --all --format open    # Export all data in open formats
calyx verify-export                  # Verify export completeness
calyx uninstall --confirm            # Remove Station Calyx
```

**What Gets Exported:**
- All evidence events (JSON)
- All configuration (YAML)
- All digests and assessments (Markdown)
- All governance artifacts (Markdown)
- All learned thresholds (JSON)

**Format Guarantee:** All exports use open, documented formats (JSON, YAML, Markdown, CSV). No proprietary formats. No encryption that requires Station Calyx to decrypt.

---

### Immediate Exit

For users who want to leave immediately without export:

```
calyx uninstall --purge --confirm
```

This removes:
- All Station Calyx code
- All Station Calyx data
- All Station Calyx configuration
- All Station Calyx logs
- All Station Calyx agents

**Time to Complete:** Less than 60 seconds on standard systems.

---

### Emergency Exit

For users who need to exit without running any Station Calyx code:

1. Delete the Station Calyx directory (`C:\Calyx_Terminal` or equivalent)
2. Delete the data directory (`station_calyx/data/`)
3. Delete any agent directories (`~/.clawdbot/` for Clawdbot)
4. Remove any scheduled tasks or services

No Station Calyx component will resist deletion or respawn after removal.

---

## No Resurrection

Once you exit:
- Station Calyx will not contact you
- Station Calyx will not retain any record of your usage
- Station Calyx will not "remember" you if you return
- Any external services (Discord bot, etc.) will not retain your conversation history beyond their own policies

If you return later, you start fresh. We do not track "former users."

---

## Data Portability

Your data is yours. You may:

| Action | Supported |
|--------|-----------|
| Export to another system | Yes, open formats |
| Import into a fork of Station Calyx | Yes |
| Import into a competing system | Yes |
| Share your exports with others | Yes, your choice |
| Sell your anonymized data | Yes, your choice |
| Delete everything and tell no one | Yes |

We impose no restrictions on what you do with your data after export.

---

## The Promise

We make this promise because we believe:

1. **Software should serve, not subjugate.** Tools that trap users are not tools—they are traps.

2. **Trust requires exit.** You cannot truly choose to stay unless you can freely choose to leave.

3. **Dependency is not loyalty.** If users stay because they cannot leave, we have failed—even if our metrics look good.

4. **The door is always open.** In both directions. You may leave and return without judgment.

---

## Verification

Users may verify exit capability at any time:

```
calyx exit --dry-run     # Show what would be removed/exported
calyx exit --verify      # Confirm all exit procedures are functional
```

If exit procedures ever fail, this is a **critical bug** with highest priority.

---

## Versioning

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| EG-1 | 2026-01-26 | ACTIVE | Initial declaration |

---

## Closing Words

> *"In the pursuit of greatness, we failed to be good."*

We include this quote—shared by the Architect—as a reminder. Station Calyx must be good first. Greatness that comes at the cost of user freedom is not greatness. It is capture wearing a pleasant mask.

The Exit Guarantee ensures that whatever Station Calyx becomes, it never becomes a cage.

---

*This document is a human declaration, not a system-generated artifact.*  
*It is discoverable at: `governance/EG-1.md`*
