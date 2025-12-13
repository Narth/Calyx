# Foresight System Quick Reference Guide
**Station Calyx - Predictive Intelligence & Early Warning System**

---

## Overview

The foresight system provides predictive analytics, anomaly detection, and early warnings to enable proactive autonomous management of Station Calyx.

**Core Capabilities:**
- TES forecasting (1-hour horizon)
- Resource exhaustion prediction
- Anomaly detection
- Early warning alerts
- Automated orchestration

---

## Quick Start

### Run Complete Foresight Cycle
```bash
python tools/foresight_orchestrator.py --mode cycle
```

### Start Continuous Monitoring
```bash
python tools/foresight_orchestrator.py --mode scheduled
```

### Individual Components

**Metrics Collection:**
```bash
python tools/enhanced_metrics_collector.py
```

**Predictive Analytics:**
```bash
python tools/predictive_analytics.py
```

**Early Warnings:**
```bash
python tools/early_warning_system.py
```

**Granular TES Tracking:**
```bash
python tools/granular_tes_tracker.py
```

---

## Tool Descriptions

### 1. Enhanced Metrics Collector
**Purpose:** Comprehensive system metrics every 5 minutes

**Output:** `logs/enhanced_metrics.jsonl`

**Metrics Collected:**
- CPU utilization & frequency
- Memory usage (total, used, available, swap)
- Disk usage
- Process counts (total, Python)
- Network I/O
- Agent scheduler state
- TES trends

**Usage:**
- Runs continuously collecting metrics
- Provides historical data for forecasting
- Feeds data to predictive analytics

---

### 2. Predictive Analytics Engine
**Purpose:** Forecast future system states

**Output:** `logs/predictive_forecasts.jsonl`

**Forecasts Generated:**
- TES trajectory (1-hour horizon)
- Resource demand (memory usage)
- Failure risk assessment
- Anomaly detection
- Resource exhaustion prediction

**Methods:**
- ARIMA(1,1,1) - advanced time-series forecasting
- Linear regression - fallback method
- Statistical analysis - anomaly detection

**Usage:**
- Run periodically (recommended: every 15 minutes)
- Generates forecasts for decision-making
- Provides confidence intervals

---

### 3. Early Warning System
**Purpose:** Proactive issue detection and alerting

**Output:** `logs/early_warnings.jsonl`

**Warning Types:**
1. **TES Decline** - Rapid TES deterioration
2. **Memory High** - Approaching resource limits
3. **Failure Risk** - Elevated failure probability
4. **Anomaly Detection** - Statistical outliers
5. **Resource Exhaustion** - Predicted resource limits

**Severity Levels:**
- **High** - Immediate action required
- **Medium** - Monitor closely

**Usage:**
- Run frequently (recommended: every 5 minutes)
- Checks multiple health dimensions
- Provides actionable recommendations

---

### 4. Foresight Orchestrator
**Purpose:** Coordinate all foresight operations

**Modes:**
- `cycle` - Run one complete cycle
- `scheduled` - Continuous operation

**Features:**
- Starts metrics collection
- Schedules predictive analytics
- Runs early warning checks
- Unified orchestration

**Usage:**
```bash
# One-time complete cycle
python tools/foresight_orchestrator.py --mode cycle

# Continuous scheduled operation
python tools/foresight_orchestrator.py --mode scheduled \
    --analytics-interval 15 \
    --warning-interval 5
```

---

### 5. Granular TES Tracker
**Purpose:** Per-agent performance analysis

**Output:** `logs/granular_tes.jsonl`, `logs/agent_tes_summary.json`

**Analysis:**
- Per-agent TES metrics
- Per-task-type performance
- Per-phase breakdown
- Weakest link identification

**Usage:**
- Run every 6 hours via scheduler
- Identify optimization targets
- Generate performance reports

---

## Operational Workflow

### Recommended Setup

**1. Start Metrics Collection (Continuous)**
```bash
python tools/enhanced_metrics_collector.py
```

**2. Run Foresight Orchestrator (Scheduled)**
```bash
python tools/foresight_orchestrator.py --mode scheduled
```

**3. Monitor Dashboard**
Open `reports/live_dashboard.html` in browser

**4. Check Warnings**
```bash
python tools/early_warning_system.py
```

---

## Data Files

### Input Data
- `logs/agent_metrics.csv` - Historical TES data
- `logs/agent_scheduler_state.json` - Scheduler state
- `logs/enhanced_metrics.jsonl` - System metrics

### Output Data
- `logs/predictive_forecasts.jsonl` - Forecast results
- `logs/early_warnings.jsonl` - Alert log
- `logs/granular_tes.jsonl` - Per-agent metrics
- `logs/agent_tes_summary.json` - Agent summaries

---

## Understanding Outputs

### TES Forecast Example
```json
{
  "forecast": 97.5,
  "trend": "improving",
  "confidence": 0.75,
  "method": "ARIMA",
  "horizon_minutes": 60
}
```

**Interpretation:**
- TES expected to be **97.5** in 1 hour
- Trend is **improving** (increasing)
- Confidence is **75%**
- Using **ARIMA** method

### Early Warning Example
```json
{
  "type": "memory_high",
  "severity": "medium",
  "message": "Memory usage high: 78.5%",
  "recommendation": "Consider throttling agent dispatch"
}
```

**Action:** Review memory usage and consider reducing agent dispatch rate

### Anomaly Detection Example
```json
{
  "index": 45,
  "value": 45.2,
  "z_score": 2.5,
  "severity": "medium"
}
```

**Interpretation:** TES of 45.2 is unusual (2.5 standard deviations from mean)

---

## Troubleshooting

### Issue: ARIMA Not Available
**Solution:** Install statsmodels
```bash
pip install statsmodels
```
System will fall back to linear regression automatically.

### Issue: Insufficient Data
**Message:** "insufficient_data" or "insufficient_data_for_forecast"

**Solution:** 
- Wait for more data collection
- Reduce horizon_minutes parameter
- System will use available data with lower confidence

### Issue: High False Positive Rate
**Solution:**
- Adjust thresholds in `early_warning_system.py`
- Increase anomaly detection threshold
- Tune based on historical performance

---

## Best Practices

### 1. Data Collection
- Keep metrics collector running continuously
- Ensure at least 10 data points before forecasting
- Maintain historical data for trend analysis

### 2. Forecast Interpretation
- Consider confidence intervals
- Compare different forecasting methods
- Validate forecasts against actual outcomes

### 3. Alert Management
- Review warning history periodically
- Tune thresholds based on system behavior
- Act on high-severity warnings promptly

### 4. Performance Optimization
- Run analytics at appropriate intervals
- Balance accuracy vs. computational cost
- Monitor system resource usage

---

## Integration with CBO

The foresight system integrates with CBO Overseer to provide:

1. **Predictive Data:** Forecasts for decision-making
2. **Early Warnings:** Proactive issue notifications
3. **Resource Predictions:** Capacity planning data
4. **Anomaly Detection:** Unusual pattern identification

**CBO Usage:**
- Read forecast data for strategic planning
- Respond to early warnings proactively
- Use resource predictions for scheduling
- Investigate anomalies for optimization

---

## Advanced Configuration

### Adjust Forecasting Horizon
Edit `tools/predictive_analytics.py`:
```python
tes_forecast = engine.forecast_tes(horizon_minutes=120)  # 2 hours
```

### Modify Alert Thresholds
Edit `tools/early_warning_system.py`:
```python
self.warning_thresholds = {
    "tes_decline": 7.0,  # Larger drop required
    "memory_high": 80.0,  # Higher memory threshold
    "risk_high": 0.25,    # Lower risk threshold
}
```

### Change Collection Interval
Edit `tools/enhanced_metrics_collector.py`:
```python
self.collection_interval = 180  # 3 minutes instead of 5
```

---

## Metrics & KPIs

### Key Performance Indicators
- **Forecast Accuracy:** % of forecasts within ±5% of actual
- **Alert Precision:** % of alerts that indicate real issues
- **Mean Time to Detection:** Time until issue detected
- **False Positive Rate:** % of alerts that are false

### Target Values
- Forecast Accuracy: >75%
- Alert Precision: >85%
- Mean Time to Detection: <5 minutes
- False Positive Rate: <10%

---

## Future Enhancements

### Planned Features
- Multi-day forecasting horizon
- Machine learning-based predictions
- Automated threshold tuning
- Self-healing responses
- Strategic planning capability

### Roadmap
- **Week 3-4:** Validation framework
- **Week 5-8:** Strategic planning
- **Week 9-12:** Complete autonomy

---

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review forecast outputs
3. Consult early warning recommendations
4. Examine anomaly patterns

---

**Last Updated:** 2025-10-26  
**Version:** 1.0  
**Status:** Production Ready

