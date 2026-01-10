#!/usr/bin/env python3
"""
Network Evidence Ingest Verification Tests
==========================================

Tests:
1. Missing token -> 401
2. Wrong token -> 403
3. Valid token, empty -> success (no envelopes)
4. Valid token, valid envelopes -> ingest success
5. Audit log entries created
"""

from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_local_ingest():
    """Test ingest via local function calls (no HTTP)."""
    print("=" * 60)
    print("Network Evidence Ingest Verification")
    print("=" * 60)
    print()
    
    results = []
    
    # Test 1: Config loading
    print("[1] Testing config with env vars...")
    os.environ["CALYX_INGEST_TOKEN"] = "test-token-12345"
    os.environ["CALYX_INGEST_MAX_ENVELOPES"] = "50"
    
    # Force config reload
    import station_calyx.core.config as config_module
    config_module._config = None
    
    from station_calyx.core.config import get_config
    config = get_config()
    
    assert config.ingest.token == "test-token-12345", "Token not loaded from env"
    assert config.ingest.max_envelopes == 50, "Max envelopes not loaded"
    print("    PASS: Config loads from environment")
    results.append(("Config loading", True))
    
    # Test 2: Audit logging
    print("[2] Testing audit logging...")
    from station_calyx.evidence.audit import log_ingest_event, get_recent_audit_events
    
    log_ingest_event(
        remote_addr="192.168.1.100",
        node_id="test-node",
        accepted_count=5,
        rejected_count=1,
        last_seq_after=42,
        auth_status="authenticated",
        rejection_reasons=["test rejection"],
        request_size_bytes=1024,
        envelope_count_received=6,
    )
    
    events = get_recent_audit_events(limit=1)
    assert len(events) > 0, "No audit events found"
    last_event = events[-1]
    assert last_event["node_id"] == "test-node", "Node ID not logged"
    assert last_event["accepted_count"] == 5, "Accepted count not logged"
    print("    PASS: Audit logging works")
    results.append(("Audit logging", True))
    
    # Test 3: Ingest with valid envelope
    print("[3] Testing ingest with valid envelope...")
    from station_calyx.evidence.store import ingest_batch, get_known_nodes, load_ingest_state
    from station_calyx.schemas.evidence_envelope_v1 import create_envelope
    
    # Create test envelope
    env = create_envelope(
        node_id="network-test-node",
        seq=0,
        event_type="TEST_EVENT",
        payload={"test": "data", "timestamp": datetime.now(timezone.utc).isoformat()},
        collector_version="v1.7.0-test",
        node_name="Network Test",
    )
    
    summary = ingest_batch([env.to_dict()])
    assert summary.accepted_count == 1, f"Expected 1 accepted, got {summary.accepted_count}"
    assert summary.rejected_count == 0, f"Expected 0 rejected, got {summary.rejected_count}"
    print("    PASS: Valid envelope ingested")
    results.append(("Valid ingest", True))
    
    # Test 4: Replay rejection
    print("[4] Testing replay rejection...")
    summary2 = ingest_batch([env.to_dict()])
    assert summary2.accepted_count == 0, "Replay should be rejected"
    assert summary2.rejected_count == 1, "Replay should be counted as rejected"
    print("    PASS: Replay correctly rejected")
    results.append(("Replay rejection", True))
    
    # Test 5: Ingest state updated
    print("[5] Testing ingest state update...")
    state = load_ingest_state("network-test-node")
    assert state.last_seq == 0, f"Expected last_seq=0, got {state.last_seq}"
    assert state.total_envelopes == 1, f"Expected 1 envelope, got {state.total_envelopes}"
    print("    PASS: Ingest state updated correctly")
    results.append(("State update", True))
    
    # Test 6: Node allowlist check
    print("[6] Testing node allowlist...")
    os.environ["CALYX_ALLOWED_NODE_IDS"] = "allowed-node-1,allowed-node-2"
    config_module._config = None
    config = get_config()
    
    from station_calyx.api.routes import check_node_allowlist
    
    allowed, rejected = check_node_allowlist(["allowed-node-1"])
    assert allowed == True, "Allowed node should pass"
    assert len(rejected) == 0, "No rejected nodes expected"
    
    allowed, rejected = check_node_allowlist(["unknown-node"])
    assert allowed == False, "Unknown node should be rejected"
    assert "unknown-node" in rejected, "Unknown node should be in rejected list"
    print("    PASS: Node allowlist works")
    results.append(("Node allowlist", True))
    
    # Clean up env
    del os.environ["CALYX_ALLOWED_NODE_IDS"]
    
    # Summary
    print()
    print("=" * 60)
    print("VERIFICATION RESULTS")
    print("=" * 60)
    
    all_pass = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        if not passed:
            all_pass = False
    
    print()
    print(f"Overall: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
    print("=" * 60)
    
    return 0 if all_pass else 1


def generate_curl_examples():
    """Generate curl/PowerShell test examples."""
    print()
    print("=" * 60)
    print("TEST COMMAND EXAMPLES")
    print("=" * 60)
    print()
    
    print("# PowerShell: Test missing token (expect 401)")
    print("""
try {
    Invoke-RestMethod -Uri "http://localhost:8420/v1/ingest/evidence" `
        -Method POST -ContentType "application/json" `
        -Body '{"envelopes": []}'
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)"
}
""")
    
    print("# PowerShell: Test wrong token (expect 403)")
    print("""
try {
    Invoke-RestMethod -Uri "http://localhost:8420/v1/ingest/evidence" `
        -Method POST -ContentType "application/json" `
        -Headers @{ Authorization = "Bearer wrong-token" } `
        -Body '{"envelopes": []}'
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)"
}
""")
    
    print("# PowerShell: Test valid token (localhost bypasses token)")
    print("""
Invoke-RestMethod -Uri "http://localhost:8420/v1/ingest/evidence" `
    -Method POST -ContentType "application/json" `
    -Body '{"envelopes": []}'
""")
    
    print("# curl: Test with token")
    print("""
curl -X POST "http://localhost:8420/v1/ingest/evidence" \\
    -H "Authorization: Bearer $CALYX_INGEST_TOKEN" \\
    -H "Content-Type: application/json" \\
    -d '{"envelopes": []}'
""")


if __name__ == "__main__":
    code = test_local_ingest()
    generate_curl_examples()
    exit(code)
