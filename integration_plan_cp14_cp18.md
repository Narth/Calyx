# CP14/CP18 Integration Plan
**Date:** 2025-10-26  
**Prepared:** By CBO  
**Status:** Awaiting CP14/CP18 Processors from CGPT

---

## Integration Overview

Ready to integrate CP14 and CP18 processors once received from CGPT. Integration points documented and prepared.

---

## Integration Points

### CP14 Sentinel (`tools/cp14_sentinel.py`)

**Current State:**
- Security monitoring operational
- Anomaly detection active
- SVF v2.0 integrated

**Add Processor Function:**
```python
def review_proposal(intent_id: str, artifacts: dict) -> dict:
    """
    Review proposal using CP14 processor
    
    Args:
        intent_id: Intent ID
        artifacts: {diff, reverse_diff, metadata, reports_dir}
        
    Returns:
        Verdict dictionary per CGPT spec
    """
    # Load CP14 processor
    # Scan change.patch
    # Generate verdict.json
    # Write to outgoing/reviews/
    # Return verdict
```

**Integration Steps:**
1. Receive CP14 processor from CGPT
2. Add `review_proposal()` to cp14_sentinel.py
3. Route from review_orchestrator.py
4. Write verdict to reviews directory
5. Update SVF audit

---

### CP18 Validator (`tools/cp18_validator.py`)

**Current State:**
- Testing framework operational
- Validation capabilities active
- SVF v2.0 integrated

**Add Processor Function:**
```python
def review_proposal(intent_id: str, artifacts: dict) -> dict:
    """
    Review proposal using CP18 processor
    
    Args:
        intent_id: Intent ID
        artifacts: {diff, reverse_diff, metadata, reports_dir}
        
    Returns:
        Verdict dictionary per CGPT spec
    """
    # Load CP18 processor
    # Run static analysis
    # Simulate tests
    # Generate verdict.json
    # Write to outgoing/reviews/
    # Return verdict
```

**Integration Steps:**
1. Receive CP18 processor from CGPT
2. Add `review_proposal()` to cp18_validator.py
3. Route from review_orchestrator.py
4. Write verdict to reviews directory
5. Update SVF audit

---

## Review Orchestrator Integration

**Current State:**
- State machine operational
- Routing implemented
- Verdict collection ready

**Update Needed:**
```python
# In review_orchestrator.py

def send_for_review(intent_id: str, artifacts: dict, reviewers: List[str]):
    """Send intent to reviewers via SVF"""
    for reviewer in reviewers:
        if reviewer == "cp14":
            # Call CP14 processor
            from tools.cp14_sentinel import review_proposal
            verdict = review_proposal(intent_id, artifacts)
            
        elif reviewer == "cp18":
            # Call CP18 processor
            from tools.cp18_validator import review_proposal
            verdict = review_proposal(intent_id, artifacts)
        
        # Write verdict file
        verdict_file = REVIEWS_DIR / f"{intent_id}.{reviewer}.verdict.json"
        verdict_file.write_text(json.dumps(verdict, indent=2))
```

---

## Testing Plan

### Test Cases Ready:
1. AWS secret injection → CP14 must FAIL
2. Broken unit test → CP18 must FAIL
3. Valid optimization → Both must PASS
4. Large diff → Auto-reject (already working)

### Validation:
- Verdict files created correctly
- PASS/FAIL logic validated
- Integration with review loop confirmed
- SVF events logged properly

---

## Timeline

**Day 1:**
- Receive processors from CGPT
- Integrate into CP14/CP18 agents
- Test verdict generation

**Day 2:**
- Test full review loop
- Validate all test cases
- Document results

---

## Files Updated

**Ready for Update:**
- `tools/cp14_sentinel.py` - Add processor function
- `tools/cp18_validator.py` - Add processor function
- `tools/review_orchestrator.py` - Route to processors

**Created:**
- `integration_plan_cp14_cp18.md` - This file
- `REQUESTS_TO_CGPT.md` - Formal request

---

## Success Criteria

- ✅ CP14 processor integrates successfully
- ✅ CP18 processor integrates successfully
- ✅ Verdict files generated per spec
- ✅ Test cases all pass
- ✅ Review loop completes end-to-end
- ✅ SVF events logged correctly

---

*Prepared by CBO*  
*Awaiting CP14/CP18 processors from CGPT*

