# Station Calyx Dashboard Architecture
**Version:** 1.0  
**Phase:** A - Backend Skeleton  
**Status:** Draft

---

## Overview

The Station Calyx Interactive Dashboard provides real-time monitoring, governance controls, and communication capabilities for Station Calyx operations.

---

## Architecture Layers

### 1. Data Layer
- **Sources:** SVF v2.0, lock files, logs, outgoing directories
- **Format:** JSON files, CSV metrics, JSONL logs
- **Update Rate:** 5-10 seconds

### 2. Broker Layer
- **Component:** `data_broker.py`
- **Function:** Lightweight metrics streaming
- **Output:** `/outgoing/dashboard/metrics.json`

### 3. API Layer
- **Framework:** Flask
- **Endpoints:** Health, Agents, Leases, Approvals, Chat
- **Authentication:** Ed25519 (Phase D)

### 4. Frontend Layer
- **Framework:** React/Vue.js (Phase B)
- **Updates:** WebSocket/SSE
- **Styling:** Dark theme

---

## Data Flow

```
SVF v2.0 → Data Broker → API Endpoints → Frontend
   ↓           ↓              ↓              ↓
 Agents    Metrics       JSON       Real-time UI
```

---

## Security Model

- **Read-only data collection** (no system writes)
- **Ed25519 authentication** (Phase D)
- **HTTPS + encrypted WebSocket** (mandatory)
- **SVF audit logging** (all API calls)

---

## Module Organization

```
dashboard/
├── backend/
│   ├── api/         # API endpoints
│   ├── auth.py      # Authentication
│   ├── data_broker.py # Metrics broker
│   └── main.py      # Flask app
├── frontend/        # (Phase B)
├── specs/           # Specifications
└── docs/            # Documentation
```

---

## API Endpoints

See `specs/api_endpoints.yaml` for complete specification.

**Key Endpoints:**
- `/api/health/current` - Current metrics
- `/api/agents/list` - Agent list
- `/api/leases/active` - Active leases
- `/api/approvals/pending` - Pending approvals
- `/api/chat/history` - Chat history

---

## Performance Requirements

- **Update Latency:** < 5 seconds
- **Page Load:** < 2 seconds
- **Concurrent Connections:** 100+
- **WebSocket Broadcast:** ≤ 1 per 2 seconds

---

## Phase Schedule

- **Phase A:** Wireframe + Data Model ✅ (Current)
- **Phase B:** Frontend Prototype (Weeks 2-3)
- **Phase C:** Communication + Governance (Weeks 4-5)
- **Phase D:** Security Review + Integration (Week 6)

---

*Architecture subject to refinement during implementation*

