# Phase 3 User Workflow Design
**Date:** 2025-10-26  
**Purpose:** Explain human involvement in Phase 3

---

## Executive Summary

Phase 3 implements a **non-blocking approval system** where Station Calyx continues operating while awaiting human approvals. User involvement is minimal and clearly signaled through notifications.

---

## How It Works

### System Behavior: Non-Blocking ✅

**Station Calyx will:**
1. ✅ Continue all operations normally
2. ✅ Queue approval requests
3. ✅ Set alert flag when needed
4. ✅ Wait for approval without stopping

**You will be notified:**
- ✅ Alert file created: `outgoing/APPROVAL_NEEDED.flag`
- ✅ Status report shows pending approvals
- ✅ Clear indication when action is needed

---

## User Involvement

### Minimal Involvement Required

**Normal Operation:**
- Station Calyx operates autonomously
- No action needed from you
- System progresses automatically

**When Approval Needed:**
- Alert file is created
- Status report shows pending items
- You review and approve
- System continues immediately

---

## Approval Workflow

### Automatic Detection
```bash
# Check for pending approvals anytime
python tools/phase3_auto_check.py
```

### Review Pending Approvals
```bash
# List all pending approvals
python tools/phase3_user_notifications.py --list
```

**Output:**
```
PENDING APPROVALS: 1

1. Request Type: cosignature
   Intent: INT-20251026-001
   Lease: LEASE-20251026-001
   Details: {"reason": "Two-key required for production"}
```

### Approve Requests
```bash
# Approve a specific lease
python tools/phase3_user_notifications.py --approve LEASE-20251026-001
```

**Result:**
- Approval added to lease
- Alert flag removed (if no other pending)
- System continues immediately

---

## Notification System

### Alert Files

**File:** `outgoing/APPROVAL_NEEDED.flag`
- Created when approval needed
- Contains request details
- Removed when approved

**File:** `outgoing/pending_approvals.json`
- Complete list of all pending approvals
- Historical record
- Status tracking

### Integration Points

**Bridge Pulse Reports:**
- Show pending approval count
- Indicate when action needed
- Provide quick summary

**CLI Commands:**
- `python tools/phase3_auto_check.py` - Check for alerts
- `python tools/phase3_user_notifications.py --list` - Review all
- `python tools/phase3_user_notifications.py --approve <id>` - Approve

---

## You Will NOT Be Blocked ✅

### Continuous Operation Guaranteed

**Phase 3 ensures:**
- ✅ System never waits for approval
- ✅ Operations continue normally
- ✅ Approvals queue for review
- ✅ No missed upgrades

**When you're away:**
- System continues operations
- Approval requests queue
- Clear summary on return
- No progress lost

---

## Recommended Workflow

### Daily Check (Optional)
```bash
# Quick check if approvals needed
python tools/phase3_auto_check.py
```

**If clean:** No action needed ✅  
**If alert:** Review and approve

### Weekly Review (Recommended)
```bash
# Comprehensive review
python tools/phase3_user_notifications.py --list
python tools/bridge_pulse.py
```

### On-Demand (As Needed)
```bash
# Approve specific items
python tools/phase3_user_notifications.py --approve <lease_id>
```

---

## What Gets Your Approval

### Two-Key Cosignatures
- Required for: Production deployments
- When: Before deployment starts
- Frequency: Per deployment
- Time: Seconds

### Canary Promotions
- Required for: Moving from 5% → 25% → 100%
- When: After health checks pass
- Frequency: Per deployment tier
- Time: Seconds

### Manual Overrides
- Required for: Emergency situations
- When: System requests intervention
- Frequency: Rare
- Time: Seconds

---

## Safety Guarantees

### Default Behavior: Safe ✅

**Without Your Approval:**
- No production deployments
- Canary stops at each tier
- Manual override available
- Complete audit trail

**With Your Approval:**
- Controlled deployments proceed
- Safety mechanisms active
- Rollback ready
- Audit trail complete

---

## Example Scenario

### Day 1: CBO Identifies Upgrade
- Research complete ✅
- Safety verified ✅
- Proposal created ✅
- **Notification sent to you**

### Day 2: You Review (Quick Check)
```bash
python tools/phase3_auto_check.py
# Approval needed: 1 pending
```

```bash
python tools/phase3_user_notifications.py --list
# Shows: INT-20251026-001 - Performance optimization
```

```bash
python tools/phase3_user_notifications.py --approve LEASE-20251026-001
# Approved ✅
```

### Day 2: Deployment Proceeds
- Two-key verified ✅
- Canary starts (5%) ✅
- Health checks pass ✅
- **Notification sent: Ready for 25%?**

### Day 2: You Approve Promotion
```bash
python tools/phase3_user_notifications.py --approve LEASE-20251026-001
# Promotion approved ✅
```

### Day 2: Deployment Completes
- 25% → 100% rollout ✅
- TES stable ✅
- **No further approvals needed** ✅

**Total Time:** 5 minutes of your involvement  
**Result:** System upgraded safely ✅

---

## Monitoring & Alerts

### Integrated Monitoring

**Bridge Pulse Reports:**
- Pending approval count
- System status
- Latest requests

**Alert Files:**
- Visual indicators
- JSON details
- Quick reference

**CLI Commands:**
- Easy access
- Clear output
- Fast approvals

---

## Conclusion

### Your Involvement: Minimal & Clear ✅

**System designs for:**
- ✅ Autonomous operation
- ✅ Clear notifications
- ✅ Quick approvals
- ✅ No blocking

**You maintain:**
- ✅ Final authority
- ✅ Clear visibility
- ✅ Easy workflow
- ✅ Safety control

**Result:**
- System upgrades proceed safely
- You stay informed
- No progress blocked
- Complete control maintained

---

*Prepared by CBO (Calyx Bridge Overseer)*  
*Station Calyx - "The flag we fly; autonomy is the dream we share."*

