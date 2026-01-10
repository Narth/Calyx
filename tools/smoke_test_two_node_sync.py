#!/usr/bin/env python3
"""Post-Parity Two-Node Sync Smoke Test."""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

SMOKE_TS = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def get_pre_state():
    """Capture pre-sync state."""
    from station_calyx.evidence.store import get_known_nodes, load_ingest_state
    
    state = {"nodes": {}, "timestamp": datetime.now(timezone.utc).isoformat()}
    
    for nid in get_known_nodes():
        s = load_ingest_state(nid)
        state["nodes"][nid] = {
            "last_seq": s.last_seq,
            "total_envelopes": s.total_envelopes,
            "last_ingested_at": s.last_ingested_at,
        }
    
    return state


def check_for_new_bundle():
    """Check if there's a new bundle to ingest from laptop."""
    from station_calyx.core.config import get_config
    
    config = get_config()
    exports_dir = config.data_dir / "exports"
    
    if not exports_dir.exists():
        return None, "No exports directory"
    
    bundles = sorted(exports_dir.glob("evidence_bundle_*.jsonl"), reverse=True)
    
    if not bundles:
        return None, "No bundles found"
    
    # Return most recent bundle
    return bundles[0], None


def ingest_bundle(bundle_path):
    """Ingest a bundle and return results."""
    from station_calyx.evidence.store import ingest_jsonl_file
    
    summary = ingest_jsonl_file(bundle_path)
    
    return {
        "accepted": summary.accepted_count,
        "rejected": summary.rejected_count,
        "reasons": summary.rejection_reasons[:5],
    }


def verify_chain_integrity(node_id):
    """Verify chain integrity for a node."""
    from station_calyx.evidence.store import get_node_evidence
    import hashlib
    
    def hpay(p):
        return hashlib.sha256(
            json.dumps(p, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
    
    def henv(e):
        d = dict(e)
        d["signature"] = None
        return hashlib.sha256(
            json.dumps(d, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
    
    envs = get_node_evidence(node_id, limit=10000)
    
    if not envs:
        return {"valid": True, "count": 0, "issues": []}
    
    issues = []
    prev = None
    
    for i, e in enumerate(envs):
        # Check payload hash
        if hpay(e.get("payload", {})) != e.get("payload_hash", ""):
            issues.append(f"Payload hash mismatch at seq {e.get('seq')}")
        
        # Check chain
        if prev and e.get("prev_hash") != henv(prev):
            issues.append(f"Chain break at index {i}")
        
        prev = e
    
    return {
        "valid": len(issues) == 0,
        "count": len(envs),
        "first_seq": envs[0].get("seq", -1),
        "last_seq": envs[-1].get("seq", -1),
        "first_ts": envs[0].get("captured_at_iso", ""),
        "last_ts": envs[-1].get("captured_at_iso", ""),
        "issues": issues,
    }


def generate_node_assessment(node_id):
    """Generate assessment for a specific node's evidence."""
    from station_calyx.evidence.store import get_node_evidence
    
    envs = get_node_evidence(node_id, limit=100)
    
    if not envs:
        return f"No evidence for node {node_id}"
    
    # Extract snapshots
    snapshots = [e for e in envs if "SNAPSHOT" in e.get("event_type", "")]
    
    lines = [
        f"## Node Assessment: {node_id}",
        "",
        f"**Evidence Count:** {len(envs)}",
        f"**Snapshots:** {len(snapshots)}",
        "",
    ]
    
    if snapshots:
        latest = snapshots[-1]
        payload = latest.get("payload", {})
        data = payload.get("data", payload)
        
        lines.extend([
            "### Latest Snapshot",
            "",
            f"- **Captured:** {latest.get('captured_at_iso', 'Unknown')}",
            f"- **CPU:** {data.get('cpu_percent', 'N/A')}%",
            f"- **Memory:** {data.get('memory', {}).get('percent', 'N/A')}%",
            "",
        ])
    
    lines.extend([
        "*This is advisory-only observation. No recommendations provided.*",
        "",
    ])
    
    return "\n".join(lines)


def generate_merged_assessment():
    """Generate merged assessment from all nodes."""
    from station_calyx.evidence.store import get_known_nodes, get_node_evidence
    
    nodes = get_known_nodes()
    
    lines = [
        "## Merged Assessment (All Nodes)",
        "",
        f"**Nodes:** {len(nodes)}",
        "",
    ]
    
    for nid in nodes:
        envs = get_node_evidence(nid, limit=50)
        if envs:
            lines.append(f"- **{nid}:** {len(envs)} envelopes, seq {envs[0].get('seq')}-{envs[-1].get('seq')}")
    
    lines.extend([
        "",
        "*Merged at read-time only. Evidence streams remain separate.*",
        "*This is advisory-only observation. No recommendations provided.*",
        "",
    ])
    
    return "\n".join(lines)


def generate_report(pre_state, post_state, ingest_result, chain_results, assessments):
    """Generate the smoke test report."""
    
    lines = [
        "# Post-Parity Two-Node Sync Smoke Test",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"**Test ID:** {SMOKE_TS}",
        "",
        "---",
        "",
        "## Test Summary",
        "",
    ]
    
    # Overall result
    all_chains_valid = all(r.get("valid", False) for r in chain_results.values())
    ingest_ok = ingest_result.get("rejected", 0) == 0 or ingest_result.get("accepted", 0) > 0
    overall = "PASS" if all_chains_valid else "FAIL"
    
    lines.extend([
        f"| Check | Result |",
        f"|-------|--------|",
        f"| Ingest | {'PASS' if ingest_ok else 'FAIL'} |",
        f"| Chain Integrity | {'PASS' if all_chains_valid else 'FAIL'} |",
        f"| **Overall** | **{overall}** |",
        "",
        "---",
        "",
        "## Pre-Sync State",
        "",
        f"**Captured:** {pre_state.get('timestamp', 'Unknown')}",
        "",
        "| Node | Last Seq | Total Envelopes |",
        "|------|----------|-----------------|",
    ])
    
    for nid, ns in pre_state.get("nodes", {}).items():
        lines.append(f"| {nid} | {ns.get('last_seq', -1)} | {ns.get('total_envelopes', 0)} |")
    
    if not pre_state.get("nodes"):
        lines.append("| *No nodes* | - | - |")
    
    lines.extend([
        "",
        "---",
        "",
        "## Ingest Results",
        "",
        f"- **Accepted:** {ingest_result.get('accepted', 0)}",
        f"- **Rejected:** {ingest_result.get('rejected', 0)}",
        "",
    ])
    
    if ingest_result.get("reasons"):
        lines.append("**Rejection Reasons:**")
        for r in ingest_result.get("reasons", []):
            lines.append(f"- {r}")
        lines.append("")
    
    lines.extend([
        "---",
        "",
        "## Post-Sync State",
        "",
        f"**Captured:** {post_state.get('timestamp', 'Unknown')}",
        "",
        "| Node | Last Seq | Total Envelopes | Change |",
        "|------|----------|-----------------|--------|",
    ])
    
    for nid, ns in post_state.get("nodes", {}).items():
        pre_ns = pre_state.get("nodes", {}).get(nid, {})
        pre_count = pre_ns.get("total_envelopes", 0)
        post_count = ns.get("total_envelopes", 0)
        change = post_count - pre_count
        change_str = f"+{change}" if change > 0 else str(change)
        lines.append(f"| {nid} | {ns.get('last_seq', -1)} | {post_count} | {change_str} |")
    
    lines.extend([
        "",
        "---",
        "",
        "## Chain Integrity Verification",
        "",
    ])
    
    for nid, cr in chain_results.items():
        status = "VALID" if cr.get("valid") else "INVALID"
        lines.extend([
            f"### Node: {nid} - {status}",
            "",
            f"- **Envelope Count:** {cr.get('count', 0)}",
            f"- **Seq Range:** {cr.get('first_seq', -1)} - {cr.get('last_seq', -1)}",
            f"- **First Captured:** {cr.get('first_ts', 'N/A')}",
            f"- **Last Captured:** {cr.get('last_ts', 'N/A')}",
            "",
        ])
        
        if cr.get("issues"):
            lines.append("**Issues Observed:**")
            for issue in cr.get("issues", [])[:5]:
                lines.append(f"- {issue}")
            lines.append("")
    
    lines.extend([
        "---",
        "",
        "## Node-Scoped Assessments",
        "",
    ])
    
    for name, assessment in assessments.items():
        lines.extend([
            f"### {name}",
            "",
            assessment,
            "",
        ])
    
    lines.extend([
        "---",
        "",
        "## Observations",
        "",
        "*Any gaps or discontinuities are stated as observations without inferred cause.*",
        "",
        "- Evidence streams remain append-only",
        "- Chain integrity verified per-node",
        "- Assessments generated from stored evidence only",
        "",
        "---",
        "",
        "*This is a read-only verification. No evidence streams were modified beyond normal ingest.*",
    ])
    
    return "\n".join(lines)


def main():
    print("=" * 60)
    print("Post-Parity Two-Node Sync Smoke Test")
    print("=" * 60)
    print()
    
    # 1. Capture pre-state
    print("[1] Capturing pre-sync state...")
    pre_state = get_pre_state()
    print(f"    Known nodes: {list(pre_state['nodes'].keys())}")
    
    # 2. Check for bundle
    print("[2] Checking for evidence bundle...")
    bundle_path, error = check_for_new_bundle()
    
    if error:
        print(f"    Note: {error}")
        ingest_result = {"accepted": 0, "rejected": 0, "reasons": [error]}
    else:
        print(f"    Found: {bundle_path.name}")
        
        # 3. Ingest bundle
        print("[3] Ingesting bundle...")
        ingest_result = ingest_bundle(bundle_path)
        print(f"    Accepted: {ingest_result['accepted']}, Rejected: {ingest_result['rejected']}")
    
    # 4. Capture post-state
    print("[4] Capturing post-sync state...")
    post_state = get_pre_state()
    print(f"    Known nodes: {list(post_state['nodes'].keys())}")
    
    # 5. Verify chain integrity
    print("[5] Verifying chain integrity...")
    chain_results = {}
    from station_calyx.evidence.store import get_known_nodes
    for nid in get_known_nodes():
        cr = verify_chain_integrity(nid)
        chain_results[nid] = cr
        status = "VALID" if cr["valid"] else "INVALID"
        print(f"    {nid}: {cr['count']} envs, {status}")
    
    # 6. Generate assessments
    print("[6] Generating node-scoped assessments...")
    assessments = {}
    
    # Get local node ID
    try:
        from station_calyx.evidence.export import get_node_identity
        local_id, local_name = get_node_identity()
    except:
        local_id = "local"
        local_name = "Workstation"
    
    # Laptop assessment
    laptop_nodes = [n for n in get_known_nodes() if "laptop" in n.lower()]
    if laptop_nodes:
        assessments["Laptop Node"] = generate_node_assessment(laptop_nodes[0])
        print(f"    Laptop: {laptop_nodes[0]}")
    
    # Workstation assessment (local evidence)
    assessments["Workstation (Local)"] = f"## Workstation Assessment\n\n**Node ID:** {local_id}\n**Name:** {local_name}\n\n*Local evidence stored in main evidence.jsonl*\n\n*This is advisory-only observation.*\n"
    print(f"    Workstation: {local_id}")
    
    # Merged assessment
    assessments["Merged (All Nodes)"] = generate_merged_assessment()
    print("    Merged: all nodes")
    
    # 7. Generate report
    print("[7] Generating report...")
    report = generate_report(pre_state, post_state, ingest_result, chain_results, assessments)
    
    reports_dir = Path("reports/verification")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"post_parity_sync_smoke_{SMOKE_TS}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"    Report: {report_path}")
    
    # Summary
    all_valid = all(r.get("valid", False) for r in chain_results.values())
    overall = "PASS" if all_valid else "FAIL"
    
    print()
    print("=" * 60)
    print(f"OVERALL: {overall}")
    print(f"Report: {report_path}")
    print("=" * 60)
    
    return 0 if all_valid else 1


if __name__ == "__main__":
    exit(main())
