# Station Calyx Interactive Dashboard - Wireframe
**Phase:** A - Wireframe Design  
**Status:** Draft  
**Last Updated:** 2025-10-26

---

## Layout Structure

```
┌────────────────────────────────────────────────────────────────────────────┐
│ 🛰️  STATION CALYX COMMAND DASHBOARD                          [Status: OK] │
│────────────────────────────────────────────────────────────────────────────│
│                                                                             │
│ ┌──────────────────────────────── SYSTEM STATUS ────────────────────────┐ │
│ │  ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐  │ │
│ │  │ CPU      │ RAM      │ DISK     │ TES      │ NETWORK  │ PHASE    │  │ │
│ │  │ 91%      │ 72%      │ 23% FREE │ 96.8     │ ⛔ CLOSED │ 3 ACTIVE│  │ │
│ │  │ [██████░]│ [██████░]│ [██░░░░░]│ [███████░]│ [███████░]│ ✅✅✅⏳ │  │ │
│ │  └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘  │ │
│ │                                                                          │ │
│ │  Resource Pressure Heatmap: CPU ████░ RAM ██░ DISK █░ NET █░ TES ███░  │ │
│ │  Last Sync: 2025-10-26 20:01:00 UTC | Throttling: Active                │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌──────────────────────────────── AGENT GRID ──────────────────────────┐ │
│ │                                                                          │ │
│ │  ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬────────┐ │ │
│ │  │   CBO   │  CP14   │  CP18   │  CP19   │  CP20   │  CP16   │  CP17  │ │ │
│ │  │ Overseer│Sentinel │Validator│Optimizer│Deployer │Referee  │ Scribe │ │ │
│ │  │  ✅ ACT │ ✅ ACT  │ ✅ ACT  │ ✅ ACT  │ ✅ ACT  │ ✅ ACT  │ ✅ ACT │ │ │
│ │  │   4m ago│   2m ago│   3m ago│   1m ago│   5m ago│   3m ago│   2m ago│ │ │
│ │  └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴────────┘ │ │
│ │                                                                          │ │
│ │  ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬────────┐ │ │
│ │  │  CP15   │  CP9    │  CP8    │  CP7    │  CP6    │         │        │ │ │
│ │  │ Prophet │Auto-Tune│Upgrader │Chronicler│Harmony  │         │        │ │ │
│ │  │ ✅ ACT  │ ✅ ACT  │ ✅ ACT  │ ✅ ACT  │ ✅ ACT  │         │        │ │ │
│ │  │   4m ago│   3m ago│   4m ago│   2m ago│   3m ago│         │        │ │ │
│ │  └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴────────┘ │ │
│ │                                                                          │ │
│ │  [Click agent → detailed view | logs | recent actions]                  │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌────────────── DIAGNOSTICS & TRIAGE ──────────────┐ ┌── SECURITY ───────┐ │
│ │ Latest Findings:                                 │ │ Pending: 2        │ │
│ │ • CP14: Lease expiry alert (5m)                 │ │ Active: 7         │ │
│ │ • CP18: Tests PASS (98%)                        │ │ Revoked: 0        │ │
│ │ • CP19: CPU normalized                           │ │                    │ │
│ │                                                   │ │ INT-0001 ⏳ Human  │ │
│ │ [Rerun] [Force Check] [Archive]                  │ │ INT-0002 ✅ Dual   │ │
│ │                                                   │ │                    │ │
│ │                                                   │ │ [Approve] [Reject] │ │
│ └───────────────────────────────────────────────────┘ └────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────── COMMUNICATION TERMINAL ─────────────────────┐ │
│ │                                                                          │ │
│ │  📢 @Station: "Phase 3 operational - autonomous deployment ready"      │ │
│ │  [Send] [Broadcast] [Direct to CBO]                                     │ │
│ │                                                                          │ │
│ │  ────────────────────────────────────────────────────────────────────  │ │
│ │                                                                          │ │
│ │  CBO 20:01:00 | "Acknowledged. All agents notified."                    │ │
│ │  CP14 20:01:01 | "Security watch active."                               │ │
│ │  CP19 20:01:02 | "Resource throttling stable at 92%."                   │ │
│ │  CP20 20:01:03 | "Phase 3 deployments ready."                           │ │
│ │                                                                          │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────── ANALYTICS FOOTER ───────────────────┐ │
│ │  TES Trend (24h): ▲ +2.1% | Lease Efficiency: 98.4% | SII: 97.3       │ │
│ │  Next Rotation: 2025-Q4 | Alerts: 0 | Pending Approvals: 2            │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### System Status Panel
**Position:** Top, full width  
**Height:** ~150px  
**Updates:** Every 5 seconds  
**Data Source:** CP19 Optimizer + SVF audit

**Metrics Displayed:**
- CPU, RAM, Disk usage (gauge + percentage)
- TES score (current + delta)
- Network status (OPEN/CLOSED)
- Phase indicators (0-3 status)
- Resource pressure heatmap
- Last sync timestamp

### Agent Grid
**Position:** Below system status  
**Height:** ~300px  
**Updates:** Every 10 seconds  
**Data Source:** SVF registry + Lock files

**Layout:** Card grid (2 rows, flexible columns)  
**Card Contents:**
- Agent name and role
- Status indicator (✅ ACTIVE / ⏸️ STANDBY / ⚠️ ISSUE)
- Last heartbeat timestamp
- Click for detailed view

**Interactions:**
- Click card → Detailed view modal
- Filter by status/role
- Search by name

### Diagnostics & Triage Console
**Position:** Left side, below agent grid  
**Width:** 50%  
**Height:** ~200px  
**Updates:** Every 5 seconds  
**Data Source:** CP14, CP18, CP19 alerts

**Contents:**
- Latest findings (scrollable)
- Alert severity indicators
- Action buttons (Rerun, Force Check, Archive)

### Security & Governance Center
**Position:** Right side, below agent grid  
**Width:** 50%  
**Height:** ~200px  
**Updates:** Real-time  
**Data Source:** Pending approvals, Active leases

**Contents:**
- Approval queue (list view)
- Approval action buttons
- Lease status summary
- Security flags

### Communication Terminal
**Position:** Bottom left  
**Width:** 100%  
**Height:** ~250px  
**Updates:** Real-time  
**Data Source:** SVF message stream

**Components:**
- Input box (message composer)
- Broadcast/Direct selectors
- Message history (scrollable)
- Agent replies

### Analytics Footer
**Position:** Bottom  
**Width:** 100%  
**Height:** ~50px  
**Updates:** Every 30 seconds  
**Data Source:** CP15 Prophet, CP7 Chronicler

**Contents:**
- Key metrics summary
- Trend indicators
- Status counts

---

## Responsive Breakpoints

- **Desktop (> 1920px):** Full layout as specified
- **Laptop (1366-1920px):** Condensed metrics, 2-column agent grid
- **Tablet (768-1366px):** Stacked layout, single column
- **Mobile (< 768px):** Collapsible panels, mobile-friendly cards

---

## Color Scheme (Dark Theme)

**Background:** #0A0E1A (Deep Space)  
**Cards:** #141824 (Dark Panel)  
**Primary:** #00D9FF (Station Cyan)  
**Success:** #00FF88 (Active Green)  
**Warning:** #FFB800 (Caution Orange)  
**Danger:** #FF4444 (Alert Red)  
**Text:** #E0E0E0 (Light Gray)

---

## Interaction Patterns

### Hover States
- Cards: Border highlight + tooltip
- Metrics: Detailed breakdown
- Agents: Status summary

### Click Actions
- Agent card → Modal with logs, metrics, history
- Approval item → Quick approve/reject dialog
- Messages → Expand full content

### Keyboard Shortcuts
- `Ctrl+K`: Search agents/intents
- `Ctrl+A`: Show approvals
- `Ctrl+M`: Focus chat input
- `Ctrl+R`: Refresh all data

---

## Loading States

**Initial Load:**
- Skeleton screens for 1-2 seconds
- Progressive rendering (system status first)
- Data streams populate sequentially

**Update Period:**
- Smooth transitions
- No flicker
- Indicate new data gently

---

## Accessibility

- ARIA labels for all interactive elements
- Keyboard navigation support
- Screen reader compatible
- High contrast mode option
- Font size scaling

---

*Design aligned with Station Calyx aesthetic*

