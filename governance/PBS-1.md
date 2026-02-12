# Privacy Boundary Schema v1 (PBS-1)

**Station Calyx / AI-for-All**

**Status:** ACTIVE  
**Declared:** 2026-01-26  
**Authority:** Human (Architect)  
**Classification:** Foundational Governance Artifact

---

## Constraints on This Document

| Constraint | Description |
|------------|-------------|
| **Non-derivable** | This schema is not inferred; it is explicitly declared by a human |
| **Non-negotiable** | No agent may weaken these boundaries through interpretation |
| **Non-overridable** | No system logic may bypass or deprioritize these boundaries |
| **Append-only** | Future versions require explicit human declaration; prior versions are preserved |

---

## Purpose

This document defines the boundaries of information within Station Calyx systems. It establishes what is protected, what may be shared, and under what conditions—ensuring that users who entrust their technological livelihood to Station Calyx are protected, not exploited.

---

## The Three Tiers

### Tier 1: The Sanctuary (NEVER SHARED)

The Sanctuary contains information that is **strictly local** and must **never** be transmitted, logged externally, or surfaced through any interface—including Discord, APIs, or agent communications.

| Category | Examples | Rationale |
|----------|----------|-----------|
| **Raw Telemetry** | Process names, file paths, directory structures, usage timestamps | Reveals behavioral patterns |
| **Personal Identifiers** | Machine name, username, user directories, IP addresses, MAC addresses | Directly identifies the user |
| **Sensitive Paths** | Contents of `/keys`, `/credentials`, `.ssh`, `.env`, private directories | Security-critical |
| **Behavioral Signatures** | Work patterns, active hours, application sequences, focus periods | Intimate portrait of life |
| **Evidence Chain Details** | Specific event contents tied to user actions | Historical exposure risk |

**Sanctuary Principle:**
> *The Sanctuary is inviolable. What happens on the user's machine stays on the user's machine unless the user explicitly, knowingly, and specifically chooses otherwise—and even then, only for that specific instance.*

---

### Tier 2: The Commons (SHAREABLE WITH CONSENT)

The Commons contains information that **may be shared** when explicitly requested by the user, but only in **aggregated, anonymized, or summarized form** that does not expose Sanctuary data.

| Category | Permitted Form | Prohibited Form |
|----------|----------------|-----------------|
| **System Health** | "Storage is 80% full" | "C:\Users\Name\Documents uses 50GB" |
| **Capability Status** | "Clawdbot is enabled" | "Clawdbot executed 47 commands today" |
| **Advisory Assessments** | "System is stable" | "Process X caused instability at 3:47 PM" |
| **Resource Metrics** | "CPU averaged 15% this hour" | "CPU spiked when running Application Y" |
| **Governance State** | "HVD-1 is active, CBO oversight enabled" | "CBO denied action X at timestamp Y" |

**Commons Principle:**
> *The Commons serves communication without exposure. It answers "how is the system?" without revealing "what is the user doing?"*

---

### Tier 3: The Interface (PUBLIC BY DESIGN)

The Interface contains information that is **intentionally visible** and designed for external interaction. This is the "porch" of Station Calyx—welcoming, but not revealing.

| Category | Examples |
|----------|----------|
| **Identity** | Station Calyx name, version, project affiliation |
| **Capabilities** | What commands are available, what the system can do |
| **Governance Status** | HVD-1 active, trial mode, oversight requirements |
| **Documentation** | Public guides, onboarding information, philosophy |

**Interface Principle:**
> *The Interface invites without revealing. It shows what Station Calyx is, not what the user has.*

---

## Boundary Enforcement

### For All Agents

Every agent operating under Station Calyx governance must:

1. **Classify before transmitting** — Determine the tier of any information before sharing
2. **Default to Sanctuary** — When uncertain, treat information as Sanctuary
3. **Never infer downward** — Cannot demote Sanctuary to Commons through interpretation
4. **Log boundary decisions** — Record when tier classification was evaluated (without logging the data itself)

### For External Interfaces (Discord, APIs, Webhooks)

External interfaces are inherently **not Sanctuary**. They may access:
- ✅ Interface tier (always)
- ✅ Commons tier (with explicit user request)
- ❌ Sanctuary tier (never)

### For Local Interfaces (Terminal, Local UI)

Local interfaces may access all tiers, as they remain within the user's control. However, they must:
- Clearly indicate when displaying Sanctuary data
- Never cache Sanctuary data beyond the immediate session
- Never transmit Sanctuary data to external services

---

## User Rights

Under this schema, users have the following inviolable rights:

| Right | Description |
|-------|-------------|
| **Right to Opacity** | The user may operate Station Calyx without any external visibility |
| **Right to Disclosure** | The user may choose to share Commons data, instance by instance |
| **Right to Silence** | The user may disable all external interfaces without losing functionality |
| **Right to Audit** | The user may review what data exists in each tier at any time |
| **Right to Deletion** | The user may delete any or all data without consequence to system function |

---

## Versioning

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| PBS-1 | 2026-01-26 | ACTIVE | Initial declaration |

Future versions will be appended as PBS-2, PBS-3, etc. Prior versions remain on record.

---

*This document is a human declaration, not a system-generated artifact.*  
*It is discoverable at: `governance/PBS-1.md`*
