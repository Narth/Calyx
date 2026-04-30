---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Discord Outbox — Agent → User DM

**Purpose:** Allow agents (CBO, scripts) to send messages to the authorized user's Discord DM without going through CBO /chat.

**File:** `runtime/discord_outbox.jsonl`

**Format:** One JSON object per line:
```json
{"msg": "Your message here"}
```

**Flow:** Agent appends a line. Calyx Discord Gateway checks the file every 60s, sends each message to the heartbeat user's DM, then clears the file.

**Example (PowerShell):**
```powershell
$msg = @{msg="Station sunrise complete. FE-9 synthesis fix applied."} | ConvertTo-Json -Compress
Add-Content -Path "runtime\discord_outbox.jsonl" -Value $msg
```

**Example (Python):**
```python
import json
path = Path("runtime/discord_outbox.jsonl")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({"msg": "Confirmation: patch applied."}) + "\n", encoding="utf-8", mode="a")
```

**Requires:** DISCORD_HEARTBEAT_USER_ID set (or first authorized user). Gateway must be running.
