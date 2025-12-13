# Phase 2 Planning - CBO Local Draft
**Date:** 2025-10-26  
**Report Type:** Architecture Planning  
**Classification:** Development Roadmap

---

## Executive Summary

Phase 2 planning to enable controlled sandboxed execution with capability leases. Building on Phase 1's secure review framework, Phase 2 adds execution safety through tokenized permissions, resource isolation, and staged deployment gates.

---

## Architecture Overview

### Core Components

1. **Lease Token System** (CP20)
   - Time-bound capability grants
   - Scoped permissions (paths, commands, resources)
   - Cryptographic signatures
   - Audit trail integration

2. **Sandbox Infrastructure** (CP20 + System)
   - Isolated execution environment
   - Read-only base + writable overlay
   - Resource limits enforcement
   - Security profiles (seccomp/AppArmor)

3. **Resource Sentinel** (CP19)
   - Real-time quota monitoring
   - Budget enforcement
   - Resource alerts
   - Kill switch triggers

4. **Deployment Automation** (CP20)
   - Lease issuance
   - Token verification
   - Execution orchestration
   - Rollback management

---

## Lease Token Schema

### Token Structure

```json
{
  "lease_id": "LEASE-20251026-001",
  "intent_id": "INT-20251026-001",
  "issued_by": "cp20",
  "issued_to": "cbo",
  "issued_at": "2025-10-26T18:50:00Z",
  "expires_at": "2025-10-26T19:00:00Z",
  "lease_duration_seconds": 600,
  
  "scope": {
    "paths_allowlist": [
      "repo://calyx/tools/*",
      "repo://calyx/config.yaml"
    ],
    "paths_denylist": [
      "repo://calyx/tools/cbo*.py",
      "repo://calyx/logs/*"
    ]
  },
  
  "commands_allowlist": {
    "build": [
      "python -m pip install -r requirements.txt",
      "pytest -q"
    ],
    "run": [
      "python tools/test_script.py"
    ],
    "ops": [
      "git status",
      "git diff"
    ]
  },
  
  "resource_limits": {
    "cpu_quota": "1 vCPU",
    "memory_quota": "2 GiB",
    "disk_quota": "100 MiB",
    "network": "deny_all"
  },
  
  "conditions": {
    "require_cp14_verification": true,
    "require_cp19_monitoring": true,
    "require_cp15_risk_assessment": false,
    "allow_external_network": false
  },
  
  "signature": {
    "algorithm": "HMAC-SHA256",
    "signer": "cp20",
    "signature": "abc123..."
  }
}
```

### Token Lifecycle

1. **Issuance:** CP20 creates token with intent approval
2. **Verification:** CP14 validates token before execution
3. **Execution:** Sandbox runs command with token
4. **Monitoring:** CP19 tracks resource usage
5. **Expiration:** Token auto-expires after duration
6. **Audit:** SVF logs all token operations

---

## Sandbox Architecture

### Isolation Layers

**Level 1: Filesystem Isolation**
- Read-only base mount: `/repo` (git repository)
- Writable overlay: `/tmp/staging/{lease_id}`
- Workspace: `/workspace` (within overlay)
- Output: `/output` (within overlay)

**Level 2: Process Isolation**
- Namespace isolation
- PID namespace (isolated PIDs)
- Network namespace (isolated network)
- Mount namespace (isolated filesystem)

**Level 3: Security Profiles**
- seccomp-bpf: Restricted syscalls
- AppArmor: Restricted file access
- No privileged operations
- No device access

**Level 4: Resource Limits**
- CPU: cgroup limits
- Memory: cgroup limits
- Disk: quota enforcement
- Network: firewall rules

### Execution Flow

```
Intent Approved (Phase 1)
    ↓
CP20 Issues Lease Token
    ↓
CP14 Verifies Token
    ↓
CP19 Sets Resource Budget
    ↓
Sandbox Created
    ↓
Command Executed
    ↓
CP19 Monitors Resources
    ↓
Results Collected
    ↓
Sandbox Destroyed
    ↓
SVF Audit Logged
```

---

## CP19 Resource Sentinel Integration

### Monitoring Points

**Pre-Execution:**
- Verify resource availability
- Set budget limits
- Reserve resources

**During Execution:**
- Monitor CPU usage
- Monitor memory usage
- Monitor disk usage
- Detect resource exhaustion

**Post-Execution:**
- Collect metrics
- Release resources
- Report to SVF

### Budget Enforcement

```python
class ResourceBudget:
    cpu_quota = "1 vCPU"
    memory_quota = "2 GiB"
    disk_quota = "100 MiB"
    network = "deny_all"
    
    def enforce_budget(self, lease_token):
        # Set cgroup limits
        # Monitor usage
        # Kill if exceeded
```

### Kill Switch Triggers

- Memory usage > quota: Terminate
- CPU usage > quota: Throttle, then terminate
- Disk usage > quota: Terminate
- Execution time > lease duration: Terminate
- Network violation: Terminate

---

## CP20 Deployer Expansion

### New Capabilities

**Lease Management:**
- Issue lease tokens
- Validate token signatures
- Track active leases
- Expire stale leases

**Execution Orchestration:**
- Create sandbox environment
- Inject lease token
- Execute command
- Collect results
- Cleanup sandbox

**Rollback Management:**
- Capture state before execution
- Store rollback instructions
- Execute rollback if needed
- Verify rollback success

### Integration Points

**With CP14:**
- Verify token before execution
- Validate security constraints
- Scan execution results

**With CP19:**
- Set resource budget
- Monitor during execution
- Enforce limits

**With CP15:**
- Assess execution risk
- Forecast resource needs
- Predict potential issues

**With CP16:**
- Arbitrate resource conflicts
- Decide on lease renewal
- Handle violations

**With CP17:**
- Document execution
- Log results
- Generate reports

---

## Safety Mechanisms

### Multi-Layer Protection

**Layer 1: Intent Approval** (Phase 1)
- Multi-agent review required
- Human approval required
- No execution without approval

**Layer 2: Lease Verification** (Phase 2)
- CP14 validates security
- CP19 verifies resources
- Token signature checked

**Layer 3: Sandbox Isolation** (Phase 2)
- Isolated environment
- No host access
- No network by default

**Layer 4: Resource Limits** (Phase 2)
- CPU quotas enforced
- Memory quotas enforced
- Disk quotas enforced
- Time limits enforced

**Layer 5: Continuous Monitoring** (Phase 2)
- CP19 watches resources
- CP14 watches security
- CP15 predicts issues
- Auto-kill on violation

---

## Integration Strategy

### Phase 2 Components

**New Files:**
- `tools/lease_manager.py` - Lease token management
- `tools/sandbox_executor.py` - Sandbox execution
- `tools/resource_enforcer.py` - CP19 budget enforcement
- `outgoing/policies/lease_schema.json` - Token schema

**Updated Files:**
- `tools/cp20_deployer.py` - Lease integration
- `tools/cp19_optimizer.py` - Resource monitoring
- `tools/cp14_sentinel.py` - Token verification
- `tools/cp15_prophet.py` - Risk assessment

**Directory Structure:**
```
outgoing/
  leases/                      # Active lease tokens
  sandboxes/                   # Sandbox state
  executions/                  # Execution results
logs/
  svf_audit/                  # Token lifecycle events
  resource_monitoring/         # CP19 metrics
```

---

## Testing Strategy

### Unit Tests

**Lease Token:**
- Token generation
- Signature verification
- Expiration checking
- Scope validation

**Sandbox:**
- Isolation verification
- Resource limit enforcement
- Security profile validation
- Cleanup confirmation

**Resource Sentinel:**
- Budget enforcement
- Kill switch triggers
- Monitoring accuracy
- Alert generation

### Integration Tests

**Happy Path:**
- Issue lease → Execute → Success → Cleanup

**Resource Violation:**
- Issue lease → Exceed quota → Kill → Report

**Security Violation:**
- Issue lease → Violate path → Reject → Log

**Network Violation:**
- Issue lease → Network access → Kill → Report

**Token Expiration:**
- Issue lease → Execute → Expire mid-execution → Kill

### Dry Run Simulation

**Scenario:**
1. CBO requests lease for test command
2. CP20 issues token
3. CP14 verifies token
4. CP19 sets budget
5. Sandbox executes `echo "test"`
6. CP19 monitors execution
7. Results collected
8. Sandbox destroyed
9. SVF logs cycle

**Expected:**
- Token issued successfully
- Execution within quota
- Results collected
- No resource violations
- Complete audit trail

---

## Implementation Timeline

### Week 1: Foundation
- Day 1-2: Lease token schema design
- Day 3-4: Sandbox infrastructure design
- Day 5: Integration planning

### Week 2: Core Implementation
- Day 1-2: Lease manager implementation
- Day 3-4: Sandbox executor implementation
- Day 5: CP19 resource enforcer integration

### Week 3: Integration & Testing
- Day 1-2: CP20 deployer integration
- Day 3-4: Multi-agent coordination
- Day 5: Dry run simulation

### Week 4: Validation
- Day 1-2: Comprehensive testing
- Day 3-4: Performance optimization
- Day 5: Production readiness review

---

## Success Criteria

### Phase 2 Metrics:
- ✅ 100% executions within sandbox
- ✅ 0% resource violations
- ✅ 100% lease validation
- ✅ 0% unauthorized access
- ✅ Complete audit trail
- ✅ Auto-kill on violations

### Performance Targets:
- Lease issuance: <5 seconds
- Sandbox creation: <10 seconds
- Token verification: <1 second
- Execution overhead: <20% resource
- Cleanup time: <5 seconds

---

## Risk Mitigation

### Identified Risks:

**Risk: Sandbox Escape**
- Mitigation: Multiple isolation layers, security profiles
- Detection: CP14 continuous monitoring
- Response: Immediate kill + rollback

**Risk: Resource Exhaustion**
- Mitigation: Strict quotas, CP19 monitoring
- Detection: Real-time monitoring
- Response: Immediate kill + rollback

**Risk: Token Forgery**
- Mitigation: Cryptographic signatures
- Detection: CP14 verification
- Response: Reject invalid tokens

**Risk: Execution Corruption**
- Mitigation: Read-only base, isolated overlay
- Detection: CP14 post-execution scan
- Response: Rollback + report

---

## Phase 2 → Phase 3 Bridge

### Requirements for Phase 3:
- ✅ Lease system proven stable
- ✅ Sandbox security validated
- ✅ Resource enforcement reliable
- ✅ Rollback tested
- ✅ Audit trail complete

### Phase 3 Capabilities:
- Canary deployments
- Two-key approval
- Production gates
- Auto-rollback
- Advanced monitoring

---

## Conclusion

Phase 2 planning complete. Comprehensive architecture for controlled sandboxed execution with capability leases. Multi-layer safety mechanisms, resource isolation, and continuous monitoring. Ready for coordination with CGPT's plan.

**Status:** PLAN DRAFTED ✅  
**Next:** Coordinate with CGPT plan, then implement

---

*Prepared by CBO (Calyx Bridge Overseer)*  
*Station Calyx - "The flag we fly; autonomy is the dream we share."*

