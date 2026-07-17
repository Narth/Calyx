#!/usr/bin/env python3
"""Generate sample ledger with 10-20 events for WO_STATION_EVENT_LEDGER_V1."""
from __future__ import annotations

import sys
from pathlib import Path

_repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_repo))

from calyx.kernel.event_ledger import emit

def main() -> None:
    emit("INFO", "kernel", "station.boot", "CBO Core started successfully")
    emit("DEBUG", "heartbeat", "heartbeat.tick", "heartbeat tick", data={"inflight": 2, "cpu": "8%"})
    emit("INFO", "heartbeat", "heartbeat.tick", "heartbeat tick", data={"checks": "dev_harness=ok,cbo_core=ok", "health": "pass"})
    emit("WARN", "ollama_gate", "ollama_gate.slow", "Request exceeded threshold", data={"req": "R9abc", "threshold": 5})
    emit("INFO", "cbo", "cbo.discord.outbound", "Outbound response sent", data={"corr": "H7K", "size": "1.2kb"})
    emit("ERROR", "router", "mail.ingest.reject", "Rejected: replay", data={"reason": "replay", "envelope_id": "env_abc123"})
    emit("INFO", "router", "mail.ingest.accept", "Accepted envelope", data={"envelope_id": "env_def456"})
    emit("INFO", "router", "router.deliver.atomic_write", "Atomic write complete", data={"envelope_id": "env_def456"})
    emit("INFO", "router", "router.deliver.success", "Delivered to CBO ingest", data={"envelope_id": "env_def456"})
    emit("INFO", "cbo", "cbo.discord.inbound", "Inbound message received", data={"channel_id": "123", "message_id": "456"})
    emit("INFO", "cbo", "toolcall.requested", "Tool requested: fs_read", data={"tool": "fs_read"})
    emit("INFO", "cbo", "toolcall.allowed", "Tool allowed: fs_read", data={"tool": "fs_read"})
    emit("WARN", "kernel", "toolcall.denied", "Forbidden tool: exec", data={"tool": "exec", "reason": "forbidden_tool"})
    emit("ERROR", "cbo", "toolcall.error", "Tool error: fs_read", data={"tool": "fs_read", "error": "file_not_found"})
    emit("INFO", "cbo", "toolcall.requested", "Tool requested: repo_grep", data={"tool": "repo_grep"})
    emit("INFO", "cbo", "toolcall.allowed", "Tool allowed: repo_grep", data={"tool": "repo_grep"})
    emit("INFO", "heartbeat", "heartbeat.recovered", "Heartbeat recovered after stall")
    emit("WARN", "heartbeat", "heartbeat.anomaly", "CPU spike detected", data={"cpu": "95%"})
    emit("INFO", "cbo", "destructive.preflight", "Preflight check before destructive op", data={"op": "fs_write"})
    emit("INFO", "cbo", "destructive.commit", "Destructive op committed", data={"op": "fs_write"})


if __name__ == "__main__":
    main()
    print("Sample ledger generated. Run: python Scripts/ledger_tail.py --n 25")
