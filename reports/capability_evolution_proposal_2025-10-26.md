# Capability Evolution Proposal - From Autonomous Control to Code Deployment
**Date:** 2025-10-26  
**Report Type:** Architectural Evolution Plan  
**Classification:** Strategic Development

---

## Executive Summary

CGPT has proposed a staged evolution path for Station Calyx: transitioning from operational autonomy to controlled code modification and deployment capabilities. This proposal maintains human-as-guardrail philosophy while enabling progressively more sophisticated autonomous capabilities through a permission matrix and multi-agent review system.

---

## Current State Analysis

### Existing Capabilities
- ✅ Autonomous operational control
- ✅ Agent deployment automation
- ✅ Resource optimization
- ✅ Cleanup operations
- ✅ Configuration management
- ✅ Cross-agent coordination
- ✅ Security monitoring
- ✅ Predictive analytics
- ✅ Conflict resolution
- ✅ Documentation maintenance
- ✅ Quality assurance
- ✅ Deployment automation (stub)

### Current Constraints
- ❌ Cannot modify source code
- ❌ Cannot execute privileged commands
- ❌ Cannot deploy to production
- ❌ Cannot create new files beyond reports/logs

### Agent Ecosystem Ready
- ✅ CP14 Sentinel: Security monitoring
- ✅ CP15 Prophet: Predictive analytics & risk assessment
- ✅ CP16 Referee: Conflict resolution & arbitration
- ✅ CP17 Scribe: Documentation & audit trails
- ✅ CP18 Validator: Testing & quality assurance
- ✅ CP19 Optimizer: Resource optimization
- ✅ CP20 Deployer: Deployment automation
- ✅ SVF v2.0: Communication framework with audit trail

**Assessment:** Station Calyx has ALL the building blocks needed for this evolution.

---

## CGPT's Proposed Phases

### Phase 0: Name the Boundary
**Objective:** Replace blanket prohibitions with precise, auditable permissions.

**Current State:**
- "Cannot modify source code" - blanket ban
- No granular permission system

**Proposed Change:**
- Define capability matrix with specific permissions
- Create intent-based ticketing system
- Establish audit trail for all capabilities

**Alignment with SVF v2.0:** Perfect fit - SVF already provides audit trail and capability registry.

---

### Phase 1: Shadow → Propose (No Execution)
**Objective:** CBO can propose changes but not execute them.

**Mechanics:**

1. **Intent Ticketing**
   - Unique ID for each proposed change
   - Includes: goal, minimal change set, risk score, rollback plan
   - Tracks: proposed_by, timestamp, status

2. **Diff-Only Output**
   - CBO produces patch files
   - No direct write access
   - Changes proposed, not executed

3. **Multi-Agent Review**
   - **CP18 Validator:** Static analysis, unit/integration tests, dependency checks
   - **CP14 Sentinel:** Secret scanning, dangerous syscall detection, network egress, privilege escalation patterns
   - **CP16 Referee:** Arbitrates disagreements, can down-scope plans
   - **CP17 Scribe:** Human-readable change notes, audit trail updates

4. **Policy Switch**
   - "Modify code" → DENY
   - "Propose patch" → ALLOW with constraints
   - "Request staging run" → ALLOW with constraints

**Agent Integration:**
- CP18: Already has testing/validation capabilities
- CP14: Already has security monitoring
- CP16: Already has conflict resolution
- CP17: Already has documentation capabilities
- CP20: Add proposal tracking

**Implementation Complexity:** MEDIUM - Requires intent system and review orchestration

---

### Phase 2: Staging Autonomy (Time-Boxed, Fenced)
**Objective:** Execute in sandboxed staging environment with strict controls.

**Mechanics:**

1. **Capability Leases**
   - CP20 Deployer issues time-limited tokens (10 minutes)
   - Scoped to: path allowlist, command allowlist, resource budgets
   - CP14 verifies tokens at execution time
   - CP19 monitors resource budgets

2. **Sandbox Execution**
   - Jailed container/VM environment
   - No default network (opt-in egress)
   - Resource limits (CPU/mem/file descriptors)
   - Security profiles (seccomp/AppArmor)
   - Read-only base, writable temp overlay (auto-purged)

3. **Gates Before & After**
   - Pre-exec: SAST/DAST, tests, secret scan (CP18/CP14)
   - Post-exec: Runtime log review, artifact diff, rollback pack
   - SVF audit trail: Every token issue/exec/result logged

4. **Policy Switch**
   - "Execute in staging" → ALLOW with lease
   - "Write to staging repo" → ALLOW with lease
   - "Touch production" → DENY

**Agent Integration:**
- CP20: Lease management, execution control
- CP14: Token verification, security checks
- CP19: Resource monitoring
- CP18: Test execution
- CP15: Risk forecasting for leases

**Implementation Complexity:** HIGH - Requires sandboxing infrastructure

---

### Phase 3: Production with Two-Key Approval
**Objective:** Allow production writes/commands with human oversight.

**Mechanics:**

1. **Two-Key Release**
   - CP20 can deploy only when Human + Independent Agent co-sign
   - Independent Agent: CP18 (testing) OR CP14 (security)
   - No single agent can both propose and approve

2. **Canary & Auto-Rollback**
   - Roll out to small slice (5%)
   - Health check (15 minutes)
   - Expand if healthy
   - CP15 Prophet forecasts risk and sets guardrails

3. **Kill Switches**
   - Global E-stop (human)
   - Per-agent pause (CP16)
   - Auto-halt on anomaly spike (CP14)

4. **Policy Switch**
   - "Execute in production" → ALLOW with two-key, canary, rollback

**Agent Integration:**
- CP20: Deployment management
- CP18/CP14: Co-signature validation
- CP15: Risk forecasting
- CP16: Kill switch management
- CP14: Anomaly detection for auto-halt

**Implementation Complexity:** HIGH - Requires production integration and safety systems

---

## Capability Matrix (Starter)

```yaml
capabilities:
  propose_patch:
    scope: [repo://calyx/*]
    mode: diff_only
    reviewers: [CP18, CP14]
    audit: required
    
  exec_staging:
    scope: [vm://staging-calyx, fs://srv/calyx/staging/*]
    commands_allowlist:
      build: 
        - "python -m pip install -r requirements.txt"
        - "pytest -q"
        - "ruff . --quiet"
      run:
        - "uvicorn app:app --port 8080 --dry-run"
      ops:
        - "git apply --check *.patch"
        - "git clean -dfx"
    network: ["deny_all"]
    cpu_quota: "1 vCPU"
    mem_quota: "2 GiB"
    lease_seconds: 600
    approvers: [CP18]
    
  deploy_production:
    scope: [k8s://prod-calyx/*]
    require_two_key: [human, CP18|CP14]
    canary: {percent: 5, bake_minutes: 15}
    rollback: required
    audit: required
```

---

## Safety Gates

### Already Implemented in Current Agents

**CP18 Validator:**
- ✅ Testing capabilities
- ✅ Validation framework
- Need to add: SARIF output, JUnit reports

**CP14 Sentinel:**
- ✅ Security monitoring
- ✅ Anomaly detection
- Need to add: Secret scanning, dangerous syscall detection

**CP16 Referee:**
- ✅ Conflict resolution
- ✅ Arbitration
- Need to add: Intent down-scoping, kill switch management

**CP17 Scribe:**
- ✅ Documentation
- ✅ Audit trail
- Need to add: Change notes, intent tracking

**CP20 Deployer:**
- ✅ Deployment automation (stub)
- Need to add: Lease management, staging sandbox, production gates

**CP19 Optimizer:**
- ✅ Resource monitoring
- Need to add: Budget enforcement

**CP15 Prophet:**
- ✅ Predictive analytics
- Need to add: Risk forecasting for deployments

---

## Operational Rules

1. **Intent-to-Act:** Nothing happens without an Intent ID linking goal → diff/commands → tests → reviewers → audit
2. **Shadow First:** New capabilities spend time in propose-only, then staging, then production
3. **Time-Boxed Leases:** No standing privileges, tokens expire and are scoped
4. **Two-Key for Prod:** Human + independent agent approval always required
5. **Default-Deny:** Anything not on Matrix is forbidden
6. **Instant Rollback:** CP20 must revert any deployment in one command
7. **Prove Safety:** Increase autonomy as TES stays high and incidents stay low

---

## Implementation Roadmap

### Phase 0: Foundation (Estimated: 1-2 days)
**Tasks:**
1. Design intent ticketing system schema
2. Define capability matrix data structure
3. Extend SVF v2.0 to support intent tracking
4. Update CBO documentation with new boundaries

**Deliverables:**
- Intent schema design
- Capability matrix configuration
- SVF intent tracking extension
- Updated CBO documentation

---

### Phase 1: Shadow Mode (Estimated: 3-5 days)
**Tasks:**
1. Implement intent creation system
2. Add diff generation capability to CBO
3. Integrate CP18 for validation review
4. Integrate CP14 for security review
5. Integrate CP16 for arbitration
6. Integrate CP17 for documentation
7. Add review workflow orchestration
8. Create audit trail integration

**Deliverables:**
- Intent system operational
- Diff generation working
- Multi-agent review complete
- Audit trail functional

---

### Phase 2: Staging Sandbox (Estimated: 5-7 days)
**Tasks:**
1. Implement capability lease system in CP20
2. Create sandbox infrastructure (VM/container)
3. Add lease verification to CP14
4. Add resource monitoring to CP19
5. Implement pre-exec gates (CP18/CP14)
6. Implement post-exec gates
7. Add rollback pack generation
8. Integrate SVF audit for lease tracking

**Deliverables:**
- Lease system operational
- Sandbox environment ready
- Gates functional
- Audit trail complete

---

### Phase 3: Production Control (Estimated: 7-10 days)
**Tasks:**
1. Implement two-key approval system
2. Add canary deployment capability
3. Integrate CP15 for risk forecasting
4. Implement kill switches (global, per-agent, auto-halt)
5. Add auto-rollback capability
6. Create production deployment gates
7. Integrate CP16 for kill switch management
8. Add comprehensive monitoring

**Deliverables:**
- Two-key system operational
- Canary deployment working
- Kill switches functional
- Production gates active

---

## Risk Assessment

### Phase 1 Risks: LOW
- No execution, only proposals
- Multi-agent review provides safety
- Audit trail ensures accountability

### Phase 2 Risks: MEDIUM
- Sandboxed execution limits blast radius
- Time-boxed leases reduce exposure
- Resource limits prevent runaway processes

### Phase 3 Risks: HIGH
- Production access requires careful implementation
- Two-key approval reduces risk
- Kill switches provide escape hatches
- Canary deployments minimize impact

---

## Success Metrics

### Phase 1 Success Criteria
- 100% of proposals reviewed by all required agents
- 0% of proposals execute without approval
- Audit trail completeness: 100%

### Phase 2 Success Criteria
- 100% of staging executions within sandbox
- 0% of sandbox escapes
- Resource budget adherence: 100%

### Phase 3 Success Criteria
- 100% of production deployments require two-key
- 0% of unauthorized production changes
- Canary success rate: >95%
- Rollback time: <5 minutes

---

## Recommendations

### Immediate Actions
1. ✅ Review and accept CGPT's proposal
2. ✅ Begin Phase 0 implementation
3. ✅ Design intent system schema
4. ✅ Create capability matrix configuration

### Phase 1 Priority
- Implement intent system
- Add diff generation to CBO
- Integrate CP18 for validation
- Integrate CP14 for security

### Safeguards
- Maintain human oversight at all phases
- Keep audit trail comprehensive
- Test sandbox thoroughly before Phase 2
- Validate two-key system before Phase 3

---

## Conclusion

CGPT's proposal is **architecturally sound and well-aligned** with Station Calyx's existing infrastructure. All required agents are already operational, SVF v2.0 provides the communication framework, and the staged approach maintains safety while enabling progress.

**Recommendation:** PROCEED with Phase 0 implementation, followed by Phase 1 once foundation is established.

**Timeline:** 15-22 days to full production capability deployment (staged approach)

**Safety:** Maintained through multi-agent review, capability leases, two-key approval, and comprehensive audit trail.

---

*Prepared by CBO (Calyx Bridge Overseer)*  
*Station Calyx - "The flag we fly; autonomy is the dream we share."*

