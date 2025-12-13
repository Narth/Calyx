# Data Retention Policy — Station Calyx

**Effective Date:** 2025-10-25  
**Authority:** CBO (Command Bridge Overseer)  
**Purpose:** Ensure efficient data retention and orderly archival of Station Calyx artifacts

---

## Overview

Station Calyx maintains comprehensive documentation and telemetry across multiple directories. This policy defines retention periods, archival procedures, and maintenance schedules to ensure system efficiency while preserving historical data.

---

## Retention Periods

### Active Data (Keep Unarchived)

| Data Type | Location | Retention | Action |
|-----------|----------|-----------|--------|
| Agent metrics | `logs/agent_metrics.csv` | 90 days | Keep last 1000 rows |
| System heartbeats | `outgoing/*.lock` | 30 days | Current active files |
| Recent reports | `reports/*.md` | 30 days | Keep active |

### Archival Thresholds

| Data Type | Location | Threshold | Action |
|-----------|----------|-----------|--------|
| Agent run directories | `outgoing/agent_run_*` | 7 days | Archive to `logs/archive/` |
| Chronicles | `outgoing/chronicles/` | 7 days | Archive to `logs/archive/` |
| Shared logs | `outgoing/shared_logs/` | 14 days | Archive to `logs/archive/` |
| Overseer reports | `outgoing/overseer_reports/` | 14 days | Archive to `logs/archive/` |
| Dialogues | `outgoing/dialogues/` | 30 days | Archive to `logs/archive/` |
| Field notes | `outgoing/field_notes/` | 30 days | Archive to `logs/archive/` |

### Archive Format

All archives are stored as compressed tar.gz files:
- Location: `logs/archive/YYYY-MM/`
- Format: `{category}_{YYYY-MM}.tar.gz`
- Compression: gzip
- Naming: `{category}_{YYYY-MM}_{timestamp}.tar.gz`

---

## Maintenance Schedule

### Daily Maintenance

**Automated Tasks:**

1. **Registry Sanitization** (Nightly @ 03:15)
   - Tool: `tools/sanitize_records.py`
   - Purpose: Canonicalize and deduplicate registry/persona records
   - Max history: 100 entries per entity

2. **CBO Maintenance Cycle** (Every 30 minutes)
   - Tool: `calyx/cbo/maintenance.py`
   - Purpose: Prune JSONL/CSV files, vacuum SQLite database
   - Keep: Last 500 rows JSONL, 1000 rows CSV

### Weekly Maintenance

**Scheduled Tasks:**

1. **Agent Run Archival** (Weekly @ Sunday 02:00)
   - Tool: `tools/archive_agent_runs.py`
   - Days: 7
   - Command: `python -u tools/archive_agent_runs.py --days 7`

2. **Chronicles Archival** (Weekly @ Sunday 02:30)
   - Tool: `tools/archive_chronicles.py`
   - Days: 7
   - Command: `python -u tools/archive_chronicles.py --days 7`

3. **SVF Log Archival** (Weekly @ Sunday 03:00)
   - Tool: `tools/log_housekeeper.py`
   - Days: 14
   - Command: `python -m tools.log_housekeeper run --keep-days 14`

### Monthly Maintenance

**Cleanup Tasks:**

1. **Archive Compression Verification** (Monthly @ 1st 04:00)
   - Verify archive integrity
   - Check compression ratios
   - Report space savings

2. **Metrics Truncation** (Monthly @ 1st 05:00)
   - Truncate agent_metrics.csv to last 1000 rows
   - Archive historical metrics
   - Vacuum SQLite databases

---

## Archival Procedures

### Agent Run Directories

**Process:**
1. Identify directories older than 7 days
2. Compress to tar.gz with timestamp
3. Store in `logs/archive/YYYY-MM/agent_runs_YYYY-MM.tar.gz`
4. Remove original directory
5. Log operation in archive report

**Verification:**
- Archive size should be < 10% of original
- All files preserved
- Extraction test successful

### Chronicles

**Process:**
1. Identify files older than 7 days
2. Group by modification month
3. Compress to tar.gz by month
4. Store in `logs/archive/YYYY-MM/chronicles_YYYY-MM.tar.gz`
5. Remove original files
6. Preserve directory structure

### Shared Logs

**Process:**
1. Identify markdown files older than 14 days
2. Group by modification month
3. Compress to tar.gz by month
4. Store in `logs/archive/YYYY-MM/shared_logs_YYYY-MM.tar.gz`
5. Remove original files

---

## Monitoring

### Disk Usage Monitoring

**CBO Heartbeat Integration:**
- Track `outgoing/` directory size
- Monitor file count
- Alert thresholds:
  - Warning: > 10GB
  - Critical: > 20GB

**Metrics Reported:**
- Total disk usage
- File count
- Archive size
- Last archival date
- Space savings

### Archival Reports

**Generation:**
- After each archival operation
- Location: `logs/archive/archive_report_{timestamp}.json`
- Contents:
  - Timestamp
  - Files archived
  - Space saved
  - Archive locations
  - Verification status

---

## Emergency Procedures

### Disk Space Critical

**If disk usage exceeds 20GB:**

1. Immediate archival of oldest data
2. Reduce retention periods temporarily
3. Compress existing archives
4. Alert CBO and User1

**Commands:**
```powershell
# Emergency cleanup
python -u tools/archive_agent_runs.py --days 3
python -u tools/archive_chronicles.py --days 3
python -m tools.log_housekeeper run --keep-days 7
```

### Archive Corruption

**If archive verification fails:**

1. Extract backup copies
2. Report to CBO
3. Investigate root cause
4. Fix archival process
5. Regenerate archives

---

## Configuration

### Retention Settings

**Location:** `config.yaml`

```yaml
data_retention:
  agent_runs_days: 7
  chronicles_days: 7
  shared_logs_days: 14
  overseer_reports_days: 14
  dialogues_days: 30
  field_notes_days: 30
  
  alert_thresholds:
    warning_gb: 10
    critical_gb: 20
    
  maintenance:
    cbo_interval_minutes: 30
    archival_day: sunday
    archival_time: "02:00"
```

### Scheduled Tasks

**PowerShell Scheduled Tasks:**

1. **Calyx Nightly Sanitizer** (Daily @ 03:15)
2. **Calyx Weekly Archival** (Weekly @ Sunday 02:00)
3. **Calyx Monthly Cleanup** (Monthly @ 1st 04:00)

---

## Compliance

### Monitoring Compliance

- CBO monitors retention policy adherence
- Weekly reports generated
- Monthly audits conducted
- User1 notified of violations

### Documentation Updates

- Retention periods reviewed quarterly
- Policy updated as needed
- Changes documented in audit reports
- Historical records preserved

---

## Tools Reference

### Archival Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| `tools/archive_agent_runs.py` | Archive agent_run directories | `--days N` |
| `tools/archive_chronicles.py` | Archive chronicles | `--days N` |
| `tools/log_housekeeper.py` | Archive SVF logs/reports | `run --keep-days N` |
| `calyx/cbo/maintenance.py` | CBO maintenance cycle | Integrated |

### Monitoring Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| CBO Heartbeat | Disk usage monitoring | Integrated |
| Archive reports | Archival verification | `logs/archive/` |

---

## Review Schedule

- **Monthly:** Review archival reports
- **Quarterly:** Update retention periods
- **Annually:** Comprehensive policy review

---

**Policy Version:** 1.0  
**Last Updated:** 2025-10-25  
**Next Review:** 2026-01-25
