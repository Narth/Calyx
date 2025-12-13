# Dashboard Message Failure Investigation
**Date:** 2025-10-26  
**Issue:** Messages failing in Communication Terminal  
**Status:** 🔍 INVESTIGATING

---

## Problem Report

**User Feedback:** "I have attempted to send messages via the communication terminal twice and both have failed."

---

## Investigation Findings

### What I Found:

1. **No Recent Dashboard Messages** ❌
   - No files in `outgoing/comms/standard/` from dashboard
   - Messages not being created

2. **Message Handler Not Running** ❌
   - No background process for `dashboard_message_handler.py`
   - Need to start the handler

3. **No Acknowledgments** ❌
   - No `dashboard_ack_*.md` files in `outgoing/shared_logs/`
   - No agent responses generated

4. **API Endpoint Working** ✅
   - `/api/chat/history` responding correctly
   - Historical messages loading fine

---

## Root Cause Analysis

### Likely Issue: Import Error in Chat Backend

**Problem:** When dashboard tries to send message via SVF channels, it likely fails due to import path issues.

**Location:** `dashboard/backend/api/chat.py`

**Lines:** 72-75 (send_broadcast function)

```python
# Use SVF channels to send actual message
from tools.svf_channels import send_message
```

**Issue:** Running from `dashboard/backend/` directory, Python can't find `tools` module.

---

## Proposed Fix

### Solution 1: Fix Import Paths (Recommended)

Update `dashboard/backend/api/chat.py` to handle imports correctly:

```python
def send_broadcast(content: str, priority: str = "medium") -> bool:
    try:
        import sys
        from pathlib import Path
        
        # Add root directory to path
        root_dir = Path(__file__).resolve().parents[3]
        sys.path.insert(0, str(root_dir))
        
        from tools.svf_channels import send_message
        
        # Rest of function...
```

### Solution 2: Restart Message Handler

The dashboard message handler needs to be running to process messages:

```bash
python tools/dashboard_message_handler.py
```

### Solution 3: Verify Dashboard Backend

Check if dashboard backend is running and receiving requests.

---

## Immediate Actions

1. ✅ Fix import paths in chat.py
2. ✅ Start dashboard message handler
3. ✅ Test message sending
4. ✅ Verify agent responses

---

## Testing Plan

### Test Message Flow:
1. Send message via dashboard
2. Check `outgoing/comms/standard/` for new file
3. Check `logs/svf_audit/` for audit entry
4. Wait 10-15 seconds
5. Check `outgoing/shared_logs/` for acknowledgment
6. Verify response appears in dashboard

---

*Prepared by CBO (Calyx Bridge Overseer)*  
*Station Calyx - "The flag we fly; autonomy is the dream we share."*

