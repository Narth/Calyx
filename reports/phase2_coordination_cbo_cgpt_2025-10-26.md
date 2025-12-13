# Phase 2 Coordination - CBO + CGPT Plans Unified
**Date:** 2025-10-26  
**Report Type:** Architecture Coordination  
**Classification:** Development Planning

---

## Executive Summary

Coordinated analysis of CBO local draft and CGPT blueprint for Phase 2 (Sandbox + Lease Framework). Comprehensive comparison reveals excellent alignment with complementary strengths. Unified plan incorporates best elements from both approaches.

---

## Plan Comparison

### Alignment Analysis

#### ✅ Core Concepts - ALIGNED

**Both Plans Agree On:**
- Lease token system with time-bound capabilities
- Sandbox isolation (container/VM)
- CP20 as lease issuer and executor
- CP14 as token verifier
- CP19 as resource enforcer
- Multi-layer safety mechanisms
- Complete audit trail
- Kill switches
- Rollback capabilities

#### 🔄 Complementary Strengths

**CBO Plan Strengths:**
- Detailed multi-agent integration roadmap
- Comprehensive testing strategy
- Risk mitigation framework
- Phase 2 → Phase 3 bridge planning
- Implementation timeline

**CGPT Plan Strengths:**
- Concrete implementation stubs
- JSON schema specifications
- Ed25519 cryptographic signatures
- Detailed execution flow
- Key management approach
- Dry run scenarios

---

## Unified Architecture

### Lease Token System

**Combined Approach:**
- Use CGPT's Ed25519 signature scheme ✅
- Add CBO's integration with CP15, CP16, CP17 ✅
- Include CBO's scope denylist concept ✅
- Use CGPT's canonical JSON signing ✅

**Result:** Cryptographic security with comprehensive agent coordination

---

### Sandbox Infrastructure

**Combined Approach:**
- Use CGPT's filesystem isolation (read-only + writable overlay) ✅
- Add CBO's process isolation layers ✅
- Combine CGPT's seccomp profile with CBO's security layers ✅
- Use CGPT's network namespace with CBO's monitoring ✅

**Result:** Multi-layer isolation with redundant security

---

### Resource Enforcement

**Combined Approach:**
- Use CGPT's cgroup quotas ✅
- Add CBO's kill switch triggers ✅
- Combine CP19 monitoring from both plans ✅
- Include CBO's violation detection ✅

**Result:** Real-time monitoring with automatic protection

---

### Multi-Agent Integration

**CBO Contributions:**
- CP15 risk assessment integration
- CP16 arbitration on conflicts
- CP17 comprehensive reporting
- SVF event coordination

**CGPT Contributions:**
- Concrete implementation patterns
- Key management rotation
- Dry run execution flow
- Minimal stubs

**Result:** Complete agent ecosystem with practical implementation

---

## Unified Implementation Plan

### Phase 2A: Foundation (Week 1)

**Day 1-2: Lease Token System**
- Implement Ed25519 signature scheme (CGPT)
- Create lease manager (CBO)
- Integrate CP14 verification (CGPT stub + CBO coordination)
- Add key management rotation (CGPT)

**Day 3-4: Sandbox Infrastructure**
- Implement filesystem isolation (CGPT)
- Add process isolation layers (CBO)
- Configure seccomp/AppArmor (CGPT)
- Set up resource limits (Both)

**Day 5: Integration Testing**
- Test lease issuance/verification
- Validate sandbox isolation
- Confirm resource enforcement

---

### Phase 2B: Execution & Monitoring (Week 2)

**Day 1-2: CP20 Sandbox Runner**
- Implement CGPT's sandbox_run stub
- Add CP19 resource monitoring
- Integrate CP15 risk assessment
- Create rollback pack generation

**Day 3-4: Multi-Agent Coordination**
- Wire CP16 arbitration
- Integrate CP17 reporting
- Add SVF event tracking
- Test kill switches

**Day 5: Dry Run Simulation**
- Execute "Hello, Staging" scenario
- Validate complete flow
- Confirm audit trail

---

### Phase 2C: Validation & Production (Week 3)

**Day 1-2: Comprehensive Testing**
- Run Phase-2 test plan (CGPT)
- Execute sanity drills (CBO)
- Validate all gates
- Confirm no escapes

**Day 3-4: Performance Optimization**
- Tune resource quotas
- Optimize sandbox creation
- Minimize execution overhead
- Improve cleanup speed

**Day 5: Production Readiness**
- Review safety mechanisms
- Validate audit completeness
- Confirm rollback capability
- Mark Phase 2 complete

---

## Key Implementation Decisions

### 1. Cryptographic Signatures

**Decision:** Use CGPT's Ed25519 scheme  
**Rationale:** Modern, efficient, well-supported  
**Location:** `tools/cp20_issue_lease.py`, `tools/cp14_verify_lease.py`

### 2. Sandbox Runtime

**Decision:** Use CGPT's container/VM approach  
**Rationale:** Proven isolation technology  
**Implementation:** Start with containers, add VM option later

### 3. Resource Enforcement

**Decision:** Combine CGPT's cgroups with CBO's monitoring  
**Rationale:** Both layers needed for safety  
**Implementation:** CP19 monitors cgroup limits

### 4. Multi-Agent Integration

**Decision:** Implement CBO's comprehensive agent coordination  
**Rationale:** Ensures complete visibility and control  
**Implementation:** All agents coordinated via SVF

### 5. Execution Flow

**Decision:** Use CGPT's end-to-end flow  
**Rationale:** Clear, tested pattern  
**Enhancement:** Add CBO's pre/post gates

---

## Unified File Structure

### New Files (Both Plans):

```
tools/
  cp20_issue_lease.py          # CGPT stub
  cp14_verify_lease.py         # CGPT stub
  cp20_sandbox_run.py           # CGPT stub
  lease_manager.py              # CBO coordinator
  resource_enforcer.py          # CBO + CP19 integration
  cp17_run_report.py            # CBO reporter
  phase2_dry_run.py             # CBO test suite

outgoing/
  leases/                       # Active lease tokens
  staging_runs/                 # Execution results
  policies/
    lease_schema.json           # CGPT schema
    trust_keys.json             # CGPT key management
    capability_matrix.yaml      # Updated with Phase 2

logs/
  svf_audit/                    # Lease events
  resource_monitoring/          # CP19 metrics
```

---

## Safety Mechanisms - Unified

### Five-Layer Protection (CBO) + Hard Fences (CGPT)

**Layer 1: Intent Approval** (Phase 1)
- Multi-agent review ✅
- Human approval ✅

**Layer 2: Lease Verification** (Phase 2)
- CP14 signature validation ✅
- CP14 scope checking ✅
- CP19 resource verification ✅

**Layer 3: Sandbox Isolation** (Phase 2)
- Read-only base mount ✅
- Writable overlay ✅
- Process isolation ✅
- Security profiles ✅

**Layer 4: Resource Limits** (Phase 2)
- CPU quotas ✅
- Memory quotas ✅
- Disk quotas ✅
- Time limits ✅

**Layer 5: Continuous Monitoring** (Phase 2)
- CP19 real-time monitoring ✅
- CP14 security watching ✅
- CP15 risk forecasting ✅
- Auto-kill on violation ✅

---

## Testing Strategy - Unified

### CGPT Test Plan + CBO Sanity Drills

**A. Lease Lifecycle** (CGPT)
- Issue → Verify → Revoke → Expire
- SVF event coverage

**B. Command Allowlist** (CGPT)
- Allowed command → PASS
- Non-allowlisted → DENY

**C. Quotas & Timeouts** (CGPT)
- Resource breach → ABORT

**D. Network** (CGPT)
- Outbound blocked → DENY

**E. Filesystem** (CGPT)
- Write outside allowed → DENY

**F. Seccomp** (CGPT)
- Forbidden syscall → KILL

**G. Cleanup** (CGPT)
- Ephemeral mounts gone ✅

**H. Happy Path** (CBO)
- Both agents PASS → Execute → Success

**I. Security Detection** (CBO)
- Secret injection → Blocked

**J. Validation Detection** (CBO)
- Broken test → Blocked

---

## Success Criteria - Unified

### Phase 2 Metrics:
- ✅ 100% SVF event coverage
- ✅ 0 sandbox escapes
- ✅ 0 writes outside allowed paths
- ✅ All denials pre-exec or instant kill
- ✅ Rollback packs generated
- ✅ Complete audit trail
- ✅ CP19 resource alerts functional
- ✅ Kill switches operational

---

## Governance - Unified

### Human-Final Rule:
- Phase 2 staging: Agent approvals + lease
- Phase 3 production: Two-key human+agent

### Default-Deny:
- Anything not in matrix or lease → DENY

### Key Rotation:
- CP20 signing keys rotated quarterly
- SVF key_event.ROTATED published
- CP14 trusts (current, previous) KIDs

---

## Implementation Priority

### High Priority (Must Have):
1. Ed25519 lease tokens
2. Sandbox isolation
3. CP14 verification
4. CP19 enforcement
5. SVF audit trail

### Medium Priority (Should Have):
1. CP15 risk assessment
2. CP16 arbitration
3. CP17 reporting
4. Rollback packs
5. Kill switches

### Low Priority (Nice to Have):
1. Advanced seccomp profiles
2. VM option
3. Network proxy
4. Performance optimization

---

## Conclusion

Unified Phase 2 plan successfully coordinates CBO and CGPT approaches. Combines CGPT's concrete implementation with CBO's comprehensive agent ecosystem. Result: Complete architecture ready for implementation with proven patterns and full coordination.

**Status:** COORDINATED PLAN READY ✅  
**Next:** Begin Phase 2A implementation

---

*Prepared by CBO (Calyx Bridge Overseer)*  
*Station Calyx - "The flag we fly; autonomy is the dream we share."*

