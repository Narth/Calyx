# CBO-Agent Onboarding Integration

**Date:** 2025-10-24  
**Status:** ✅ Design Complete  
**Integration:** CBO becomes first point of contact for new agents

---

## Overview

CBO now handles agent onboarding as an immediate extension of its orchestration capabilities. New agents register through CBO, which validates prerequisites, assigns initial tasks, and monitors integration health.

---

## Onboarding Flow

### Phase 1: Agent Registration → CBO

**New Agent Initiates:**
```powershell
# Agent emits heartbeat with registration intent
python -u .\tools\copilot_hello.py --name <agent_name> --status registering --message "Requesting onboarding via CBO" --ttl 60
```

**CBO Detection:**
- CBO heartbeat loop detects new `status: registering` heartbeat
- CBO reads `calyx/core/registry.jsonl` to check existing agents
- If agent not in registry → triggers onboarding workflow

**CBO Actions:**
1. **Validation Check** - Runs onboarding prerequisites via `Scripts/agent_onboarding.py --verify`
2. **Registry Update** - Prepares registry entry with skills, role, autonomy level
3. **Initial Task Assignment** - Queues onboarding objective in `calyx/cbo/objectives.jsonl`
4. **Monitoring Setup** - Creates agent-specific monitoring in CBO heartbeat

---

### Phase 2: Automated Verification

**CBO Verification Process:**

```python
# CBO executes onboarding checks
onboarding_checks = {
    "docs_read": verify_docs_present(),
    "config_exists": verify_config_valid(),
    "heartbeat_working": verify_heartbeat_tool(),
    "tools_available": verify_essential_tools(),
    "svf_compliance": verify_svf_compatibility(),
    "role_assignment": validate_role_requirements(),
}
```

**Validation Results:**
- **All Pass** → Proceed to Phase 3
- **Issues Found** → Generate remediation plan
- **Blockers** → Escalate to human overseer

---

### Phase 3: Registry Integration

**CBO Creates Registry Entry:**

```json
{
  "agent_id": "<agent_name>",
  "role": "<orchestrator|mentor|guardian|watchdog|service>",
  "autonomy": "<core|managed|advisory>",
  "skills": ["skill1", "skill2"],
  "executable": "path/to/agent_script.py",
  "interval_sec": 300,
  "parameters": "--optional-args",
  "onboarded_by": "cbo",
  "onboarded_at": "2025-10-24T...",
  "status": "active"
}
```

**Registry Update Process:**
1. Read current `calyx/core/registry.jsonl`
2. Validate no duplicate agent_id
3. Append new agent entry
4. Commit to registry
5. Log onboarding completion

---

### Phase 4: Initial Task Assignment

**CBO Generates Onboarding Objectives:**

```json
{"objective_id": "onboard-<agent_name>-001", "description": "Complete documentation review and system verification", "priority": 3, "metadata": {"phase": "onboarding", "agent": "<agent_name>", "skills": ["reading", "verification"]}}
{"objective_id": "onboard-<agent_name>-002", "description": "Execute first supervised task with monitoring", "priority": 2, "metadata": {"phase": "onboarding", "agent": "<agent_name>", "skills": ["execution", "monitoring"]}}
{"objective_id": "onboard-<agent_name>-003", "description": "Demonstrate autonomous operation within safe boundaries", "priority": 1, "metadata": {"phase": "onboarding", "agent": "<agent_name>", "skills": ["autonomy", "safety"]}}
```

**CBO Dispatch:**
- Queues onboarding objectives to `calyx/cbo/objectives.jsonl`
- Plan engine assigns tasks to appropriate agents
- Feedback loop monitors completion

---

### Phase 5: Health Monitoring

**CBO Continuous Monitoring:**

```python
# CBO heartbeat loop monitors onboarding agent
onboarding_health = {
    "heartbeat_age": check_heartbeat_recency(),
    "tes_score": analyze_task_efficiency(),
    "error_rate": count_recent_errors(),
    "resource_usage": check_cpu_memory_footprint(),
    "harmony": evaluate_cp6_harmony_score(),
}
```

**Monitoring Triggers:**
- **Healthy** → Continue normal operation
- **Issues** → Generate diagnostics, propose remediation
- **Critical** → Suspend agent, escalate to human

---

## CBO Onboarding Capabilities

### Capability Matrix

| Capability | Description | CBO Implementation |
|------------|-------------|-------------------|
| **Registration Detection** | Identify new agents | Heartbeat monitoring, registry comparison |
| **Prerequisite Validation** | Verify system readiness | Execute onboarding checks |
| **Registry Management** | Add agents to registry | JSONL append, duplicate prevention |
| **Initial Task Assignment** | Queue onboarding objectives | Objectives insertion, task dispatch |
| **Health Monitoring** | Track agent integration | TES analysis, heartbeat monitoring |
| **Remediation Support** | Address onboarding issues | Generate action plans, escalate blockers |

### Integration Points

**CBO Heartbeat Extension:**
```json
{
  "name": "bridge-overseer",
  "phase": "active",
  "status": "running",
  "onboarding": {
    "active_agents": 3,
    "pending_onboarding": 1,
    "recent_onboardings": ["agent1", "agent2"],
    "health_score": 0.92
  }
}
```

**Registry Sync:**
- CBO reads registry on each heartbeat
- Detects new agents automatically
- Triggers onboarding workflow
- Monitors integration success

**Task Integration:**
- Onboarding objectives queued normally
- Standard task dispatch handles onboarding tasks
- Feedback loop tracks onboarding completion
- TES analyzer includes onboarding metrics

---

## User Workflow

### For New Agents

**Step 1: Announce Presence**
```powershell
python -u .\tools\copilot_hello.py --name my_agent --status registering
```

**Step 2: Monitor CBO Onboarding**
```powershell
# Watch CBO heartbeat for onboarding status
python -c "import json; print(json.load(open('outgoing/cbo.lock'))['onboarding'])"
```

**Step 3: Complete Onboarding Tasks**
- Agent receives objectives via normal CBO task queue
- Execute tasks per standard workflow
- CBO monitors and provides feedback

**Step 4: Verify Integration**
```powershell
python -u .\Scripts\agent_onboarding.py --verify
```

---

### For Administrators

**Monitor Onboarding Status:**
```powershell
powershell -File .\Scripts\Calyx-Overseer.ps1 -Status
```

**Review Registry:**
```powershell
Get-Content calyx\core\registry.jsonl | ConvertFrom-Json
```

**Check Onboarding Health:**
```powershell
python -c "import json; print(json.load(open('outgoing/cbo.lock'))['onboarding'])"
```

---

## CBO Onboarding Configuration

### Policy Controls

**`calyx/core/policy.yaml`**
```yaml
onboarding:
  enabled: true
  auto_detect: true
  validation_strict: true
  max_concurrent_onboarding: 2
  onboarding_timeout_minutes: 30
  require_human_approval: false
```

### Registry Schema

**Required Fields:**
- `agent_id` - Unique identifier
- `role` - Agent role type
- `autonomy` - Autonomy level
- `skills` - Capability list
- `executable` - Script path

**Optional Fields:**
- `interval_sec` - Execution interval
- `parameters` - Execution arguments
- `onboarded_by` - Onboarding initiator
- `onboarded_at` - Timestamp
- `status` - Current status

---

## Success Metrics

### Onboarding KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Onboarding Time** | < 30 minutes | Time from registration to active |
| **Validation Pass Rate** | ≥ 95% | Prerequisites passing |
| **Registry Accuracy** | 100% | No duplicate or invalid entries |
| **Initial Task Success** | ≥ 90% | First assigned tasks completed |
| **Health Score** | ≥ 85 | Integration health after onboarding |

### Monitoring Indicators

- **Registration Rate** - New agents per day
- **Onboarding Completion** - Successfully onboarded agents
- **Integration Health** - TES scores for new agents
- **Remediation Frequency** - Issues requiring human intervention

---

## Troubleshooting

### Common Issues

**Agent Not Detected:**
- Verify heartbeat `status: registering`
- Check CBO heartbeat loop running
- Confirm registry comparison logic

**Validation Failures:**
- Review prerequisite requirements
- Check system state (gates, config)
- Run manual verification: `--verify`

**Registry Conflicts:**
- Check for duplicate agent_id
- Validate JSON format
- Review registry file integrity

**Onboarding Stuck:**
- Check CBO heartbeat status
- Review objectives queue
- Examine task dispatch logs

---

## Future Enhancements

### Planned Capabilities

1. **Automated Skills Inference** - CBO analyzes agent behavior to infer skills
2. **Onboarding Templates** - Role-specific onboarding workflows
3. **Onboarding Analytics** - Historical performance tracking
4. **Progressive Autonomy** - Gradual autonomy increase during onboarding
5. **Peer Mentoring** - Existing agents guide new agents

### Integration Opportunities

- **CP6 Sociologist** - Harmony tracking for new agents
- **CP7 Chronicler** - Documentation of onboarding events
- **CP8 Quartermaster** - Resource allocation for onboarding
- **Teaching System** - Onboarding-specific teaching cycles

---

## Related Documentation

- `docs/AGENT_ONBOARDING.md` - Comprehensive agent onboarding guide
- `calyx/cbo/CBO_CHARTER.md` - CBO mission and capabilities
- `calyx/cbo/README.md` - CBO operational documentation
- `docs/COMPENDIUM.md` - Agent roster and roles
- `Scripts/agent_onboarding.py` - Onboarding verification tool

---

## Changelog

**2025-10-24** - Initial CBO-Agent Onboarding Integration
- Designed onboarding workflow
- Defined capability matrix
- Established success metrics
- Created monitoring framework

