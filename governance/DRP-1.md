# Data Retention Policy v1 (DRP-1)

**Station Calyx / AI-for-All**

**Status:** ACTIVE  
**Declared:** 2026-01-26  
**Authority:** Human (Architect)  
**Classification:** Foundational Governance Artifact

---

## Constraints on This Document

| Constraint | Description |
|------------|-------------|
| **Non-derivable** | This policy is not inferred; it is explicitly declared by a human |
| **Non-negotiable** | No agent may extend retention beyond these limits |
| **Non-overridable** | No optimization may justify violating these retention boundaries |
| **Append-only** | Future versions require explicit human declaration |

---

## Purpose

This document defines what data Station Calyx retains, for how long, where it is stored, and under what conditions it is deleted. The goal is minimum viable retention: keep only what is necessary, for only as long as necessary, and always under user control.

---

## Retention Categories

### Category A: Ephemeral (Session-Only)

Data that exists only during active operation and is purged when the session ends.

| Data Type | Retention | Storage Location |
|-----------|-----------|------------------|
| Live telemetry streams | Until session end | Memory only |
| Active process monitoring | Until session end | Memory only |
| Temporary computation results | Until consumed | Memory only |
| Chat session context (Discord) | Until session end | Gateway memory |

**Purge Trigger:** Session termination, system restart, or explicit clear command.

---

### Category B: Short-Term (Rolling Window)

Data retained for operational continuity, automatically purged after the retention window.

| Data Type | Retention Window | Storage Location |
|-----------|------------------|------------------|
| Evidence events | 7 days | `station_calyx/data/events/` |
| System snapshots | 24 hours | `station_calyx/data/snapshots/` |
| Truth Digest history | 30 days | `station_calyx/data/digests/` |
| Action proposal logs | 7 days | `station_calyx/data/clawdbot/` |
| Advisory notifications | 48 hours | `station_calyx/data/notifications/` |

**Purge Mechanism:** Automatic rotation; oldest entries removed when window exceeded.

---

### Category C: Long-Term (User-Controlled)

Data retained indefinitely until explicitly deleted by the user.

| Data Type | Default Retention | Storage Location |
|-----------|-------------------|------------------|
| Governance artifacts (HVD-1, PBS-1, etc.) | Permanent | `governance/` |
| User configuration | Until changed | `config.yaml` |
| Learned thresholds | Until reset | `station_calyx/data/thresholds/` |
| Yield analysis history | Until purged | `station_calyx/data/yield/` |

**Purge Mechanism:** Explicit user command only. System will never auto-delete Category C data.

---

### Category D: Never Retained

Data that must never be persisted to storage under any circumstances.

| Data Type | Rationale |
|-----------|-----------|
| Passwords or credentials observed in telemetry | Security |
| Contents of encrypted files | Privacy |
| Keystrokes or input streams | Surveillance prevention |
| Screen contents or captures | Surveillance prevention |
| Network packet contents | Privacy |
| Data from other users' machines | Sovereignty |

**Enforcement:** Any agent that encounters Category D data must discard it immediately without logging.

---

## Storage Principles

### Local-First

All data is stored locally on the user's machine by default. No data is transmitted to external servers unless:
1. The user explicitly initiates the transmission
2. The data is classified as Interface or Commons tier (per PBS-1)
3. The transmission is to a destination the user controls

### No Silent Accumulation

Station Calyx must not accumulate data beyond what is necessary for its declared functions. Data hoarding "for future use" or "for analytics" is prohibited.

### Transparent Storage

Users must be able to:
- See exactly where all data is stored
- Understand what each data store contains
- Delete any data store without breaking core functionality

---

## Retention Overrides

### User Extension

Users may extend retention windows for any category (except D) through explicit configuration. The system will honor extended retention but will remind users of the original policy.

### User Reduction

Users may reduce retention windows or demand immediate purge at any time. The system must comply within one operational cycle.

### Emergency Purge

Users may execute an emergency purge command that immediately deletes all Category A, B, and C data. This is the "exit button"—always available, always functional.

```
calyx purge --all --confirm
```

---

## External Service Retention

When Station Calyx interacts with external services (Discord, APIs), users must understand:

| Service | What They Retain | Our Control |
|---------|------------------|-------------|
| Discord | Messages, interactions | None after transmission |
| OpenAI API | Prompts, responses (per their policy) | None after transmission |
| External webhooks | Whatever we send | None after transmission |

**Principle:** Once data leaves the local system, we cannot guarantee its deletion. Users must understand this before using external interfaces.

---

## Audit and Verification

Users may audit retention compliance at any time:

```
calyx retention audit          # Show what exists in each category
calyx retention age            # Show age of oldest data in each store
calyx retention purge-preview  # Show what would be deleted by window enforcement
```

---

## Versioning

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| DRP-1 | 2026-01-26 | ACTIVE | Initial declaration |

---

*This document is a human declaration, not a system-generated artifact.*  
*It is discoverable at: `governance/DRP-1.md`*
