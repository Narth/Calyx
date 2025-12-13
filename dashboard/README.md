# Station Calyx Interactive Dashboard

**Status:** ✅ Operational  
**Version:** Phase B Complete  
**Access:** http://localhost:8080

---

## Quick Start

### Start Dashboard:
```bash
cd dashboard
python backend/main.py
```

### Access Dashboard:
Open your browser to: **http://localhost:8080**

---

## Features

### System Status Panel
- Real-time CPU/RAM/Disk/TES metrics
- Phase status indicators
- Resource pressure heatmap

### Agent Grid
- Live agent status cards
- Click for detailed information
- Heartbeat monitoring

### Diagnostics Console
- System alerts
- Action buttons
- Log management

### Security & Governance Center
- Pending approvals
- Active leases
- Two-key governance status

### Communication Terminal
- Broadcast messages
- Direct messaging
- SVF chat history

### Analytics Footer
- TES trends
- Lease efficiency
- System metrics

---

## Architecture

### Frontend:
- `frontend/templates/dashboard.html` - Main UI
- `frontend/static/css/dashboard.css` - Dark theme
- `frontend/static/js/dashboard.js` - Real-time updates

### Backend:
- `backend/main.py` - Flask application
- `backend/api/` - API endpoints
- `backend/data_broker.py` - Metrics broker

### Data Sources:
- CP19 Optimizer - System metrics
- SVF Registry - Agent status
- CP14 Sentinel - Approvals
- CP17 Scribe - Chat logs
- CP15 Prophet - Analytics

---

## Dependencies

```bash
pip install flask flask-cors pyyaml psutil
```

---

## Troubleshooting

### Template Not Found Error:
Flask now correctly configured with template and static directories.

### API Not Responding:
- Check backend is running: `python backend/main.py`
- Verify port 8080 is available
- Check logs for errors

### No Data Displaying:
- Verify data sources exist:
  - `logs/agent_metrics.csv`
  - `outgoing/*.lock`
  - `logs/svf_audit/`

---

## Development

### Phase B Complete ✅
- Frontend UI
- Backend API
- Live data integration
- Real-time updates

### Phase C (Optional)
- Advanced filtering
- Historical visualization
- WebSocket push updates
- Accessibility enhancements

---

**Station Calyx Dashboard**  
*"The flag we fly; autonomy is the dream we share."*
