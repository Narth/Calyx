# Station Calyx Dashboard User Guide
**Version:** 1.0  
**Phase:** A - Documentation

---

## Overview

The Station Calyx Interactive Dashboard provides real-time monitoring, governance controls, and communication capabilities for Station Calyx operations.

---

## Getting Started

### Requirements
- Python 3.8+
- Browser (Chrome, Firefox, Edge)
- Ed25519 key (for authentication)

### Installation

```bash
cd dashboard
pip install -r requirements.txt
python backend/main.py
```

Dashboard will be available at `http://localhost:8080`

---

## Features

### System Health Panel
- Real-time CPU, RAM, Disk, TES metrics
- Resource pressure heatmap
- Phase status indicators
- Historical trends

### Agent Grid
- Live status of all 20 agents
- Heartbeat timestamps
- Quick access to logs
- Detailed agent views

### Diagnostics Console
- CP14 security alerts
- CP18 validation findings
- CP19 resource anomalies
- Quick action buttons

### Security Center
- Pending approvals
- Active leases
- One-click approve/reject
- Audit trail access

### Communication Terminal
- Station-wide broadcasts
- Direct CBO messaging
- Agent tagging (@cp14)
- Message history

---

## Usage

### Viewing System Health
The top panel displays current system health metrics.

### Monitoring Agents
Click any agent card to view detailed status, logs, and recent actions.

### Managing Approvals
Pending approvals appear in the Security Center with approve/reject buttons.

### Sending Messages
Use the Communication Terminal to broadcast station-wide or send direct messages.

---

## Keyboard Shortcuts

- `Ctrl+K` - Search
- `Ctrl+A` - Show approvals
- `Ctrl+M` - Focus chat
- `Ctrl+R` - Refresh data

---

## Security

- Ed25519 authentication required
- HTTPS + encrypted WebSocket
- Complete audit trail
- Role-based access control

---

*Full user guide available in Phase B*

