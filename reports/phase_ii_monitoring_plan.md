# Phase II Monitoring Plan

**Date:** 2025-10-24  
**Purpose:** Continuous monitoring of TES and capacity metrics for conditional track activation  
**Status:** ACTIVE

---

## Monitoring Objectives

1. Track TES scores toward ≥96 target
2. Monitor capacity score toward >0.5 threshold
3. Maintain CPU <50% and RAM <75% for conditional tracks
4. Enable Tracks B, C, F when criteria met

---

## Current Metrics Baseline

### TES Monitoring
- **Current:** 46.6
- **Target:** ≥96
- **Trend:** Declining (concern)
- **Status:** ACTIVE MONITORING

### Capacity Score
- **Current:** 0.489
- **Target:** >0.5
- **Status:** Near threshold (99% progress)

### System Resources
- **CPU:** 20.7% ✅ (well below 50% threshold)
- **RAM:** 81.5% ⚠️ (slightly above 75% threshold)
- **Status:** Stable but RAM marginal

---

## Track Eligibility Status

### Track B: Autonomy Ladder Expansion
**Status:** DEFERRED  
**Reason:** TES below 95 or insufficient data  
**Requirement:** TES ≥95 for 5 pulses AND CPU <50% for 24h

**Current State:**
- TES: 46.6 (significantly below 95)
- CPU: 20.7% ✅ (within requirement)
- Trend: Declining
- **Action:** Investigate TES decline, monitor for improvement

### Track C: Resource Governor
**Status:** DEFERRED  
**Reason:** RAM 81.5% slightly above 75% threshold  
**Requirement:** CPU <50%, RAM <75%, capacity score >0.5

**Current State:**
- CPU: 20.7% ✅ (well within requirement)
- RAM: 81.5% ⚠️ (1.5% above threshold)
- Capacity: 0.489 ⚠️ (slightly below 0.5)
- **Action:** Monitor RAM trend, capacity score near threshold

### Track F: Safety & Recovery Automation
**Status:** DEFERRED  
**Reason:** Blocked by Track C requirement  
**Requirement:** Track C active + playbooks validated + human sign-off

**Current State:**
- Depends on Track C activation
- **Action:** Await Track C eligibility

---

## Monitoring Schedule

### Bridge Pulse Reports
- **Frequency:** Every 20 minutes
- **Purpose:** Track system-wide metrics
- **Output:** `reports/bridge_pulse_bp-####.md`

### Metrics Monitoring
- **Frequency:** Every Bridge Pulse
- **Purpose:** Track TES and capacity trends
- **Tool:** `tools/metrics_monitor.py`
- **Output:** `state/metrics_tracking.json`

### Trend Analysis
- **Frequency:** Daily
- **Purpose:** Generate trend insights
- **Tool:** `tools/bridge_pulse_analytics.py`
- **Output:** `reports/trends/trends_YYYYMMDD_HHMMSS.json`

---

## Alerts and Thresholds

### TES Alerts
- **Warning:** TES <90 sustained for >1 hour
- **Critical:** TES <85 sustained for >30 minutes
- **Action:** Investigate root cause, review recent agent runs

### Capacity Alerts
- **Warning:** Capacity score <0.30
- **Critical:** Capacity score <0.20
- **Action:** Review resource utilization, consider scaling back

### Resource Alerts
- **CPU Warning:** >60% sustained for >15 minutes
- **CPU Critical:** >80% sustained for >5 minutes
- **RAM Warning:** >85% sustained for >15 minutes
- **RAM Critical:** >90% sustained for >5 minutes

---

## Track Activation Criteria

### Track B Activation
**Prerequisites:**
1. TES ≥95 for 5 consecutive pulses
2. CPU <50% sustained for 24 hours
3. No policy violations in last 24 hours
4. Human approval confirmed

**Monitoring:** Check every Bridge Pulse

### Track C Activation
**Prerequisites:**
1. CPU <50% sustained
2. RAM <75% sustained
3. Capacity score >0.5
4. System stability confirmed
5. Human approval

**Monitoring:** Check every Bridge Pulse

### Track F Activation
**Prerequisites:**
1. Track C operational
2. Playbooks validated offline
3. Human sign-off on recovery procedures
4. Testing completed

**Monitoring:** Check after Track C activation

---

## Immediate Actions

### TES Investigation
**Issue:** TES dropped to 46.6 (target: ≥96)  
**Action Required:**
1. Review `logs/agent_metrics.csv` for recent failures
2. Check `logs/agent_scheduler.log` for scheduler issues
3. Analyze TES trend in `tools/metrics_monitor.py`
4. Identify root cause of decline

### Capacity Score
**Status:** 0.489 (99% of target)  
**Action:** Monitor RAM utilization, capacity score trending positive

### RAM Monitoring
**Status:** 81.5% (1.5% above threshold)  
**Action:** Continue monitoring trend, investigate if sustained above 80%

---

## Success Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| TES | 46.6 | ≥96 | ⚠️ Critical |
| Capacity Score | 0.489 | >0.5 | ⚠️ Near target |
| CPU | 20.7% | <50% | ✅ Good |
| RAM | 81.5% | <75% | ⚠️ Marginal |
| Uptime | 100% | ≥95% | ✅ Excellent |

---

## Next Review

**Date:** Bridge Pulse bp-0006  
**Expected:** Track C eligibility assessment, TES investigation results  
**Focus:** TES trend analysis, capacity score improvement

---

**Status:** ACTIVE MONITORING  
**Generated:** 2025-10-24 10:51:00  
**Tool:** `tools/metrics_monitor.py`

