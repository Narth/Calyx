# Manual Relay Sync v0 Workflow

**Version:** v0 (Pre-Alpha)  
**Status:** Manual Transfer Only  
**Date:** 2026-01-09

---

## Overview

This workflow enables evidence synchronization between Station Calyx nodes using manually transferred bundle files. No network connectivity is required between nodes.

**Use Case:** Sync telemetry from a laptop (observer) to a workstation (receiver) when both are on the same local network or when transferring via USB/cloud storage.

---

## Constraints

| Constraint | Description |
|------------|-------------|
| **Advisory-only** | No execution authority on either node |
| **Evidence-first** | Only raw evidence is transferred |
| **Append-only** | Evidence is never modified after creation |
| **No conclusions** | Receiver stores evidence; analysis happens separately |

---

## Workflow Steps

### Step 1: Export Evidence (Source Node)

On the **laptop** (or source node), export evidence to a portable bundle:

```powershell
# Export new evidence since last export
python -B -m station_calyx.ui.cli export-evidence

# Or export all evidence (ignore previous exports)
python -B -m station_calyx.ui.cli export-evidence --all

# Check export status
python -B -m station_calyx.ui.cli export-evidence --status
```

**Output:** A JSONL bundle file in the exports directory:
```
station_calyx/data/exports/evidence_bundle_<node_id>_<timestamp>.jsonl
```

**What's Exported:**
- System snapshots
- Scheduled snapshots
- Reflections
- Advisories
- Temporal analyses
- Trends and drift warnings
- Recurring patterns

---

### Step 2: Transfer Bundle (User-Managed)

Transfer the bundle file from source to destination using any method:

| Method | Example |
|--------|---------|
| **USB Drive** | Copy to USB, then to destination |
| **Shared Folder** | Copy to network share |
| **Cloud Storage** | Upload to OneDrive/Dropbox/etc. |
| **Direct Copy** | `scp`, `robocopy`, etc. |

**Example (Windows):**
```powershell
# Copy to USB
Copy-Item "station_calyx\data\exports\evidence_bundle_*.jsonl" "E:\calyx_transfer\"

# Or copy to network share
Copy-Item "station_calyx\data\exports\evidence_bundle_*.jsonl" "\\server\share\calyx\"
```

**Important:** The bundle file is self-contained and includes:
- Node identity (source node ID and name)
- Monotonic sequence numbers
- Hash chain for tamper detection
- All envelope metadata

---

### Step 3: Ingest Evidence (Destination Node)

On the **workstation** (or destination node), ingest the transferred bundle:

```powershell
# Ingest the bundle
python -B -m station_calyx.ui.cli ingest path\to\evidence_bundle_abc123_20260109_120000.jsonl

# Dry-run to validate without ingesting
python -B -m station_calyx.ui.cli ingest bundle.jsonl --dry-run
```

**Output:**
```
[Ingest] Reading evidence bundle: evidence_bundle_abc123_20260109_120000.jsonl
[Ingest] Found 45 envelope(s) in file
[Ingest] Processing...

[Ingest] Results:
  Accepted: 45
  Rejected: 0

? Successfully ingested 45 envelope(s)
```

**Validation Performed:**
- Required fields present
- Sequence monotonicity (replay protection)
- Payload hash verification (tamper detection)
- Hash chain continuity

---

### Step 4: Verify Ingested Nodes

Check that the source node's evidence is now available:

```powershell
# List all known nodes
python -B -m station_calyx.ui.cli nodes

# JSON output
python -B -m station_calyx.ui.cli nodes --json
```

**Output:**
```
======================================================================
Known Evidence Nodes (2)
======================================================================
Node ID                        Last Seq   Envelopes    Last Ingested       
----------------------------------------------------------------------
local                          -1         0            Never               
abc123-laptop                  44         45           2026-01-09T12:15:00 
======================================================================
```

---

## Generating Node-Scoped Reports

After ingesting evidence from multiple nodes, generate reports scoped to specific nodes or merged:

### Human Assessment (Single Node)

```powershell
# Assess local node
python -B -m station_calyx.ui.cli assess --node local

# Assess specific remote node
python -B -m station_calyx.ui.cli assess --node abc123-laptop

# Assess all nodes (merged view)
python -B -m station_calyx.ui.cli assess --node all
```

### Status by Node

```powershell
# Status includes findings from specific node evidence
python -B -m station_calyx.ui.cli status --human
```

### Temporal Analysis

Run temporal analysis which will include evidence from all ingested nodes:

```powershell
python -B -m station_calyx.ui.cli analyze temporal
```

---

## Directory Structure After Sync

**Source Node (Laptop):**
```
station_calyx/data/
??? evidence.jsonl           # Local evidence
??? node_identity.json       # This node's identity
??? export_state.json        # Export tracking
??? exports/
    ??? evidence_bundle_abc123_20260109_120000.jsonl
```

**Destination Node (Workstation):**
```
station_calyx/data/
??? evidence.jsonl           # Local evidence
??? node_identity.json       # This node's identity
??? logs/evidence/
    ??? abc123-laptop/
        ??? evidence.jsonl       # Ingested evidence (append-only)
        ??? ingest_state.json    # Ingest tracking
```

---

## Replay Protection

If you try to ingest the same bundle twice:

```
[Ingest] Results:
  Accepted: 0
  Rejected: 45

Reasons:
  - Non-monotonic seq: 0 <= 44
```

The receiver tracks the last ingested sequence number per node and rejects duplicates.

---

## Troubleshooting

### "No exportable events found"

Run some snapshots first:
```powershell
python -B -m station_calyx.ui.cli snapshot
python -B -m station_calyx.ui.cli snapshot
python -B -m station_calyx.ui.cli snapshot
```

### "Hash chain mismatch"

The bundle may have been modified in transit. Re-export from source:
```powershell
python -B -m station_calyx.ui.cli export-evidence --all
```

### "Non-monotonic seq"

Evidence has already been ingested. This is expected for duplicate transfers.

### View Raw Evidence

```powershell
# View ingested evidence for a node
python -B -c "from station_calyx.evidence.store import get_node_evidence; import json; print(json.dumps(get_node_evidence('abc123-laptop', limit=5), indent=2))"
```

---

## Security Notes

| Concern | Mitigation |
|---------|------------|
| **Tampering** | SHA256 payload hash + hash chain |
| **Replay** | Monotonic sequence rejection |
| **Impersonation** | (v1) Signature verification planned |
| **Interception** | User responsibility during transfer |

---

## Next Steps (v1)

- [ ] Ed25519 signatures for envelope authentication
- [ ] Automatic sync over local network
- [ ] Conflict resolution for multi-source merges
- [ ] Compression for large bundles

---

## Quick Reference

| Action | Command |
|--------|---------|
| Export evidence | `calyx export-evidence` |
| Export all (reset) | `calyx export-evidence --all` |
| Check export status | `calyx export-evidence --status` |
| Ingest bundle | `calyx ingest <file.jsonl>` |
| Validate bundle | `calyx ingest <file.jsonl> --dry-run` |
| List nodes | `calyx nodes` |
| Assess node | `calyx assess --node <node_id>` |

---

*This workflow is advisory-only. No commands are executed on remote systems.*
