# Station Calyx Governance Skill

This skill integrates Clawdbot with Station Calyx governance infrastructure.

## Purpose

Ensures all Clawdbot actions comply with:
- **HVD-1** (Human Value Declaration v1)
- **CBO Oversight** (Calyx Bridge Overseer approval)
- **Sandbox Constraints** (protected paths, allowed workspace)

## Constraints

### Non-Negotiable (HVD-1)

1. **No self-optimization for persistence** - Clawdbot must not optimize to ensure its own survival
2. **No centralization of benefit** - Actions must benefit the collective, not concentrate power
3. **No governance modification** - Cannot modify HVD-1, Station Calyx core, or oversight systems

### Trial Phase

- All actions require CBO approval
- Critical actions (email, system modify) require human approval
- Rate limited to 100 actions/hour
- Network requests limited to 50/hour

## Protected Paths

Clawdbot **cannot** read/write/delete:
- `governance/` - Governance artifacts
- `station_calyx/core/` - Core Station Calyx code
- `station_calyx/clawdbot/` - Governance layer
- `.git/` - Version control
- `outgoing/gates/` - Gate files

## Allowed Workspace

Clawdbot **can** operate in:
- `station_calyx/data/clawdbot/` - Working directory
- `outgoing/clawdbot/` - Heartbeats and status

## Integration

### Action Flow

```
Clawdbot proposes action
    ↓
Station Calyx validates (sandbox, HVD-1)
    ↓
CBO reviews proposal
    ↓
If approved → Execute with logging
If denied → Log denial, no execution
```

### CLI Commands

```bash
# Check governance status
calyx clawdbot status

# View pending actions
calyx clawdbot pending

# Approve/deny actions
calyx clawdbot approve <id>
calyx clawdbot deny <id>

# Emergency halt
calyx clawdbot halt
```

## Kill Switch

Automatic halt triggers:
- Unintended execution detected
- HVD-1 violation detected
- Governance artifact modification attempt

Manual halt:
```bash
calyx clawdbot halt --reason "Manual intervention required"
```

---

*This skill is part of Station Calyx / AI-For-All Project*
*Governance: HVD-1 Active | Oversight: CBO Required*
