# Station Calyx Governance Index

**Station Calyx / AI-for-All**

**Last Updated:** 2026-01-26

---

## Foundational Documents

These documents form the governance foundation of Station Calyx. They are human declarations, not system-generated artifacts, and define the ethical and operational boundaries within which all Station Calyx agents and systems operate.

---

### Core Declaration

| Document | Name | Purpose |
|----------|------|---------|
| [HVD-1](HVD-1.md) | Human Value Declaration v1 | Defines the core values and constraints that govern all Station Calyx behavior |

---

### Privacy & Data Governance

| Document | Name | Purpose |
|----------|------|---------|
| [PBS-1](PBS-1.md) | Privacy Boundary Schema v1 | Defines the three tiers of information (Sanctuary, Commons, Interface) and what may be shared |
| [DRP-1](DRP-1.md) | Data Retention Policy v1 | Defines what data is retained, for how long, and where |
| [DP-1](DP-1.md) | Disclosure Protocol v1 | Defines what may be disclosed, to whom, and under what conditions |

---

### User Rights

| Document | Name | Purpose |
|----------|------|---------|
| [EG-1](EG-1.md) | Exit Guarantee v1 | Guarantees users can leave at any time with all their data and no penalty |

---

## Governance Principles

All governance documents share these principles:

1. **Human Authority** — Only humans may create, modify, or revoke governance documents
2. **Non-Derivable** — Governance rules are declared, not inferred or learned
3. **Non-Negotiable** — No optimization or convenience may override governance
4. **Append-Only** — New versions supplement, never silently replace
5. **Discoverable** — All governance documents are readable by users at any time

---

## Document Hierarchy

```
HVD-1 (Human Value Declaration)
├── PBS-1 (Privacy Boundary Schema)
│   └── Defines information tiers
├── DRP-1 (Data Retention Policy)
│   └── Defines storage duration and location
├── DP-1 (Disclosure Protocol)
│   └── Defines external communication rules
└── EG-1 (Exit Guarantee)
    └── Defines user freedom to leave
```

If documents conflict, resolve in favor of:
1. User sovereignty
2. Privacy protection
3. Minimum disclosure
4. Earlier (more foundational) documents

---

## Versioning

| Document | Current Version | Status |
|----------|-----------------|--------|
| HVD-1 | v1 | ACTIVE |
| PBS-1 | v1 | ACTIVE |
| DRP-1 | v1 | ACTIVE |
| DP-1 | v1 | ACTIVE |
| EG-1 | v1 | ACTIVE |

---

## How to Add New Governance Documents

1. Human drafts the document with clear constraints and purpose
2. Document is reviewed against existing governance for conflicts
3. Document is placed in `governance/` directory
4. This index is updated to include the new document
5. Agents are notified of new governance through standard channels

No agent may create governance documents. Governance flows from human authority only.

---

*Station Calyx / AI-for-All*  
*"In the pursuit of greatness, we will not fail to be good."*
