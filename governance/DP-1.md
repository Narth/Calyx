# Disclosure Protocol v1 (DP-1)

**Station Calyx / AI-for-All**

**Status:** ACTIVE  
**Declared:** 2026-01-26  
**Authority:** Human (Architect)  
**Classification:** Foundational Governance Artifact

---

## Constraints on This Document

| Constraint | Description |
|------------|-------------|
| **Non-derivable** | This protocol is not inferred; it is explicitly declared by a human |
| **Non-expandable** | No agent may disclose beyond what this protocol permits |
| **Non-overridable** | No convenience may justify violating disclosure boundaries |
| **Append-only** | Future versions require explicit human declaration |

---

## Purpose

This document defines what Station Calyx and its agents may disclose through external interfaces, to whom, and under what conditions. It governs all communication that crosses the boundary between the user's local system and the outside world.

---

## Disclosure Channels

### Channel: Discord (Calyx Agent)

**Classification:** Public Interface  
**Trust Level:** External (user data traverses third-party infrastructure)

| May Disclose | May NOT Disclose |
|--------------|------------------|
| Station Calyx identity and version | Machine name or user identity |
| Available commands and capabilities | Command history or execution logs |
| Governance status (HVD-1 active, etc.) | Specific governance decisions |
| Aggregated health ("system stable") | Specific metrics or paths |
| Current time and timezone | User activity patterns |
| Command output (when explicitly requested) | Unrequested system information |

**Disclosure Trigger:** User must explicitly request information. Agents must not volunteer Sanctuary or Commons data.

---

### Channel: Local Terminal (CLI)

**Classification:** Trusted Interface  
**Trust Level:** Local (data remains on user's machine)

| May Disclose | Restrictions |
|--------------|--------------|
| All tiers (Sanctuary, Commons, Interface) | Must label Sanctuary data clearly |
| Full telemetry and metrics | Must not cache beyond session |
| Complete command history | Must not transmit externally |
| Detailed governance logs | User-only visibility |

---

### Channel: API (Future)

**Classification:** Controlled Interface  
**Trust Level:** Variable (depends on API consumer)

| Authentication Required | Yes, always |
|------------------------|-------------|
| Default Disclosure Level | Interface only |
| Commons Access | Requires explicit scope grant |
| Sanctuary Access | Never permitted via API |
| Rate Limiting | Enforced to prevent enumeration |

---

## Disclosure Rules

### Rule 1: Explicit Request Required

Agents may only disclose information in response to explicit user requests. Proactive disclosure is permitted only for:
- Emergency alerts (system critical failures)
- Governance violations (attempted boundary breach)
- Session continuity (resuming interrupted work)

### Rule 2: Minimum Necessary Disclosure

When responding to requests, disclose the minimum information necessary to fulfill the request. Do not pad responses with additional data.

**Example:**
- Request: "Is Clawdbot enabled?"
- Correct: "Yes, Clawdbot is enabled."
- Incorrect: "Yes, Clawdbot is enabled. It was enabled at 2:53 PM and has executed 12 commands including dir, python, and..."

### Rule 3: Tier Verification Before Disclosure

Before disclosing any information through an external channel, verify:
1. What tier does this information belong to? (PBS-1)
2. Is this channel permitted to receive this tier?
3. Has the user explicitly requested this disclosure?

If any check fails, decline the disclosure with explanation.

### Rule 4: No Inference Disclosure

Agents must not disclose information that can be inferred from patterns, even if individual data points are Commons or Interface tier.

**Example:**
- Permitted: "CPU usage is 15%"
- Prohibited: "CPU usage is 15%, which is lower than your usual 40% during work hours"

The second discloses behavioral patterns (Sanctuary) through inference.

### Rule 5: Disclosure Logging

All disclosures through external channels must be logged locally (but the log itself is Sanctuary tier):
- What was disclosed
- Through which channel
- At what time
- In response to what request

Users may audit disclosure logs at any time.

---

## Disclosure to Other Agents

When Station Calyx agents communicate with each other:

| Same Node | Full disclosure permitted (local communication) |
|-----------|------------------------------------------------|
| Different Nodes | Commons and Interface only, encrypted in transit |
| External Agents (non-Station Calyx) | Interface only, with user consent |

---

## Handling Disclosure Requests from Third Parties

If any external party (other than the user) requests disclosure:

| Request Type | Response |
|--------------|----------|
| Legal/government request | Inform user; user decides; system has no backdoor |
| Commercial/analytics request | Decline; this violates HVD-1 |
| Security researcher request | Inform user; user decides with full context |
| Other Station Calyx users | Interface only; never cross-user data |

**Principle:** Station Calyx serves the user, not external parties. The user is the only authority who can authorize disclosure.

---

## Emergency Disclosure

In genuine emergencies (imminent data loss, security breach in progress), agents may:
1. Alert the user through all available channels
2. Disclose the nature of the emergency (Commons tier)
3. Never disclose Sanctuary data, even in emergencies

If the user is unreachable during an emergency, agents must:
1. Take protective action (if within capability)
2. Log the situation for user review
3. Wait for user to return before any disclosure

---

## Versioning

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| DP-1 | 2026-01-26 | ACTIVE | Initial declaration |

---

*This document is a human declaration, not a system-generated artifact.*  
*It is discoverable at: `governance/DP-1.md`*
