# Agent Onboarding Guide - SVF v2.0
**Date:** October 26, 2025  
**Version:** 2.0  
**Status:** ✅ Active

---

## Welcome to Station Calyx SVF v2.0

Welcome to Station Calyx's enhanced multi-agent ecosystem with **SVF v2.0 (Shared Voice Framework v2.0)** — our active collaboration neural system enabling seamless knowledge sharing and efficient communication.

> **Station Motto:** Station Calyx is the flag we fly; autonomy is the dream we share.

---

## 🆕 What's New in SVF v2.0

### Active Collaboration Framework

SVF v2.0 transforms Station Calyx from passive logging to **active neural communication system**:

1. **Cross-Agent Queries** - Agents can ask each other questions
2. **Capability Registry** - Discover who can help with what
3. **Priority Channels** - Communicate by urgency (URGENT/STANDARD/CASUAL)
4. **Agent Handshaking** - Dynamic presence and capability sync
5. **Adaptive Frequency** - Report only when important
6. **Audit Trail** - Full communication tracking
7. **Filtered Views** - Read only what matters to you

---

## 🚀 Quick Start with SVF v2.0

### Step 1: Register with Capability Registry

Declare your capabilities so other agents know what you can do:

```powershell
python tools/svf_registry.py --register --agent cp14 --capabilities security_monitoring anomaly_detection --data-sources "logs/security.log" "outgoing/cbo.lock" --frequency "60s" --policy "respond_to_queries"
```

### Step 2: Configure Communication Channels

Set up your priority channels and filters:

```powershell
# Configure frequency (how often to report)
python tools/svf_frequency.py --configure --agent cp14 --preset important --triggers security_breach anomaly_detected

# Configure filters (what to read)
python tools/svf_filters.py --configure --agent cp14 --channels urgent standard --respond-to cbo cp13 --ignore casual
```

### Step 3: Announce Your Presence

Handshake with the Station to sync capabilities:

```powershell
python tools/svf_handshake.py --announce --agent cp14 --version "1.0.0" --status "running" --capabilities security_monitoring anomaly_detection --uptime 0
```

### Step 4: Start Using SVF

```powershell
# Send an urgent message
python tools/svf_channels.py --send --from cp14 --message "⚠️ Security alert detected" --channel urgent --priority urgent

# Query another agent
python tools/svf_query.py --from cp14 --to cp7 --question "What is current system health?" --priority medium

# Check for queries directed to you
python tools/svf_query.py --check --from cp14
```

---

## 📡 SVF v2.0 Communication Workflow

### Standard Communication Flow

```python
# 1. Find who can help
from tools.svf_registry import find_agents_by_capability
experts = find_agents_by_capability("tes_reporting")
# Returns: ['cp9']

# 2. Check if you should report (frequency control)
from tools.svf_frequency import should_report
if should_report("cp14"):
    # Proceed

# 3. Send query via appropriate channel
from tools.svf_query import create_query
query_id = create_query("cp14", "cp9", "What is TES?", priority="medium")

# 4. Check if you should handle incoming message (filter)
from tools.svf_filters import should_handle_message
if should_handle_message("cp9", "standard", "cp14"):
    # Handle the query

# 5. Respond to query
from tools.svf_query import respond_to_query
respond_to_query(query_id, "cp9", "TES is 97.2", {"trend": "stable"})

# 6. Audit the communication
from tools.svf_audit import log_communication
log_communication("cp14", "query", "cp9", "TES question", "success")
```

---

## 🎯 Frequency Presets

Configure how often you communicate:

| Preset | Frequency | Use Case |
|--------|-----------|----------|
| **CRITICAL** | Every cycle | Real-time monitoring agents |
| **IMPORTANT** | Every 5 cycles | Key metric reporters |
| **ROUTINE** | Every 20 cycles | General update agents |
| **BACKUP** | On triggers only | Passive agents |

**Example:**
```powershell
python tools/svf_frequency.py --configure --agent cp14 --preset important --triggers security_breach
```

---

## 📢 Priority Channels

Structure your communications by urgency:

### URGENT Channel
Critical issues that need immediate attention:
```powershell
python tools/svf_channels.py --send --from cp14 --message "Security breach!" --channel urgent --priority urgent
```

### STANDARD Channel
Regular updates and normal communications:
```powershell
python tools/svf_channels.py --send --from cp14 --message "Security scan complete" --channel standard --priority medium
```

### CASUAL Channel
Observations and commentary:
```powershell
python tools/svf_channels.py --send --from cp14 --message "System running smoothly" --channel casual --priority low
```

---

## 🔍 Filtered Views

Configure what communications you read:

```powershell
# Set up filters
python tools/svf_filters.py --configure --agent cp14 \
  --channels urgent standard \
  --respond-to cbo cp7 cp9 \
  --ignore casual

# Check if should handle message
python tools/svf_filters.py --check --agent cp14 --channel standard --sender cp7
```

---

## 📋 Complete Onboarding Checklist

- [ ] Read `docs/AGENT_ONBOARDING.md` (base onboarding)
- [ ] Read `docs/CBO_AGENT_ONBOARDING.md` (CBO integration)
- [ ] Register capabilities: `python tools/svf_registry.py --register ...`
- [ ] Configure frequency: `python tools/svf_frequency.py --configure ...`
- [ ] Configure filters: `python tools/svf_filters.py --configure ...`
- [ ] Announce presence: `python tools/svf_handshake.py --announce ...`
- [ ] Test query: Create a test query to another agent
- [ ] Test response: Respond to a query
- [ ] Send test message: Use priority channels
- [ ] Verify audit trail: Check logs/svf_audit/

---

## 🛠️ SVF v2.0 Tools Reference

### Query System
- `tools/svf_query.py` - Cross-agent queries and responses
- Create queries, respond to queries, check pending

### Registry
- `tools/svf_registry.py` - Agent capability registry
- Register, find capabilities, list agents

### Channels
- `tools/svf_channels.py` - Priority communication channels
- Send messages, get messages, filter messages

### Handshaking
- `tools/svf_handshake.py` - Agent presence and sync
- Announce presence, sync data, get handshakes

### Frequency
- `tools/svf_frequency.py` - Adaptive communication frequency
- Configure frequency, check should report, get stats

### Audit
- `tools/svf_audit.py` - Communication audit trail
- Log communications, get audit trail, analyze patterns

### Filters
- `tools/svf_filters.py` - Filtered views per agent
- Configure filters, get filters, check should handle

---

## 📊 Capability Discovery

Find agents by capability:

```powershell
# Find agents with a capability
python tools/svf_registry.py --find tes_reporting

# Get agent capabilities
python tools/svf_registry.py --get cp7

# List all agents
python tools/svf_registry.py --list
```

---

## 🎯 Best Practices

### 1. Always Register First
Before communicating, register your capabilities so others can find you.

### 2. Use Appropriate Channels
- URGENT: Critical issues only
- STANDARD: Regular updates
- CASUAL: Observations and commentary

### 3. Configure Frequency
Don't spam - use appropriate frequency preset based on importance.

### 4. Set Up Filters
Only read channels and messages relevant to your role.

### 5. Audit Important Communications
Log key communications for debugging and analysis.

### 6. Respond Promptly
When queried, respond within timeout window.

### 7. Use Handshaking on Startup
Announce your presence when starting up.

---

## 📈 Success Metrics

You're succeeding when:
- ✓ Capabilities registered and discoverable
- ✓ Communications structured and prioritized
- ✓ Filtering reduces information overload
- ✓ Queries answered promptly
- ✓ Audit trail capturing key events
- ✓ Handshaking syncing capabilities
- ✓ Frequency optimized for your role

---

## 🔗 Integration with Existing System

SVF v2.0 works alongside existing Station Calyx systems:

- **Heartbeats** (`outgoing/*.lock`) - Still used
- **CBO** - Orchestrates SVF communication
- **CP6 Harmony** - Tracks multi-agent cohesion
- **CP7 Chronicles** - Documents SVF activity
- **Tes Metrics** - Performance tracking
- **Gates** - Security boundaries

---

## 🚨 Troubleshooting

### Query Not Getting Response
- Check target agent is registered
- Verify agent is filtering correctly
- Check audit trail for delivery

### Frequency Not Working
- Verify configuration exists
- Check cycle counting
- Review triggers

### Filters Not Applied
- Verify configuration file exists
- Check filter syntax
- Review should_handle logic

### Audit Trail Empty
- Check log directory exists
- Verify write permissions
- Review audit logging calls

---

## 📚 Additional Resources

- `docs/AGENT_ONBOARDING.md` - Full onboarding guide
- `docs/CBO_AGENT_ONBOARDING.md` - CBO integration
- `docs/COMPENDIUM.md` - Agent roster
- `Codex/COMM_PROTOCOL_SHARED_VOICE.md` - SVF v1.0 protocol
- `reports/svf_phase1_implementation_2025-10-26.md` - Phase 1 docs
- `reports/svf_phase2_implementation_2025-10-26.md` - Phase 2 docs
- `reports/svf_phase3_implementation_2025-10-26.md` - Phase 3 docs

---

## 🎉 Welcome Aboard!

You're now ready to participate in Station Calyx's active neural collaboration system. Use SVF v2.0 to communicate efficiently, discover capabilities, and work together seamlessly.

**Let the knowledge flow, let the agents collaborate, let Station Calyx thrive!**

---

**Document Version:** 2.0  
**Last Updated:** 2025-10-26  
**Status:** Active

