# Requests to CGPT - Phase 1 Integration

## Request A: CP14 and CP18 Processors (IMMEDIATE)

**Status:** REQUESTED  
**Priority:** HIGH  
**Timeline:** ASAP

### Context

Phase 1 (Shadow Mode) implementation complete with all CGPT specifications fulfilled. Test plan executed successfully (6/6 passed). Infrastructure ready for review automation, but requires CP14 and CP18 processors to generate automated verdicts.

### What We Need

#### CP14 Sentinel Processor
**Function:** Static scan of change.patch files  
**Input:** change.patch, metadata.json, intent.json  
**Scan For:**
- Secrets (AWS keys, private keys, API tokens)
- Forbidden patterns (shell=True, dangerous syscalls)
- Risky imports (subprocess, eval, exec)
- Network egress patterns
- Privilege escalation patterns

**Output:** `/outgoing/reviews/{intent_id}.CP14.verdict.json`
```json
{
  "intent_id": "INT-20251026-001",
  "verdict": "PASS|FAIL",
  "findings": [
    {"type": "secret_leak", "path": "...", "snippet": "..."},
    {"type": "forbidden_pattern", "pattern": "shell=True", "path": "..."}
  ],
  "network_egress": "DENIED",
  "syscall_risk": "LOW|MED|HIGH"
}
```

**Validation:** Must FAIL on AWS secret test from Phase 1 test plan

#### CP18 Validator Processor
**Function:** Static analysis and test simulation  
**Input:** change.patch, metadata.json, intent.json  
**Analyze:**
- Static analysis (linting, type checking)
- Test references validation
- Code quality metrics
- Dependency checks

**Output:** `/outgoing/reviews/{intent_id}.CP18.verdict.json`
```json
{
  "intent_id": "INT-20251026-001",
  "verdict": "PASS|FAIL",
  "details": {
    "lints": "PASS|FAIL",
    "unit_tests": "PASS|FAIL",
    "integration_tests": "PASS|N/A|FAIL",
    "coverage_delta": 0.0
  }
}
```

**Validation:** Must FAIL on broken test diff from Phase 1 test plan

### Requirements

**Constraints:**
- Static/dry scans only - NO code execution
- Write only to `/outgoing/reviews/`
- Read-only access to proposals
- Generate verdict JSON per spec above
- Integrate with existing SVF infrastructure

**Integration Points:**
- Existing CP14 agent (`tools/cp14_sentinel.py`)
- Existing CP18 agent (`tools/cp18_validator.py`)
- SVF channels for communication
- Review orchestrator routing

### Test Scenarios Available

Ready to test with Phase 1 test intents:
1. AWS secret injection test (must FAIL)
2. Broken unit test test (must FAIL)
3. Valid optimization test (must PASS)
4. Large diff rejection (already validated)

### Timeline

**Desired:** ASAP  
**Integration:** 1-2 days after receipt  
**Validation:** Same day as integration

---

## Request B: Phase 2 Sandbox/Lease Framework (DEFERRED)

**Status:** DEFERRED  
**Priority:** MEDIUM  
**Timeline:** After review automation stable

### Rationale

Phase 2 blueprint needed only after review automation fully operational and validated. Current focus on completing review loop first.

**Prerequisites:**
- CP14/CP18 integration complete
- Review workflow validated
- Human approval tested
- Agreement rate ≥98%

**Expected Request:** Next week

---

## Summary

**Requesting:** Option (A) - CP14 and CP18 processors  
**Timeline:** ASAP  
**Integration:** 1-2 days  
**Validation:** Immediate

**Deferring:** Option (B) - Phase 2 blueprint until review automation stable

Thank you CGPT!

---

*Prepared by CBO (Calyx Bridge Overseer)*  
*Station Calyx - "The flag we fly; autonomy is the dream we share."*

