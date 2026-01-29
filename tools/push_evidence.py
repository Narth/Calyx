#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evidence Push Client - Push evidence envelopes to home workstation.

[CBO Governance]: This client sends evidence envelopes to a remote
Station Calyx node (home workstation) over LAN. It is:
- Explicit user action only (no background pushing)
- Token-authenticated (CALYX_INGEST_TOKEN)
- Bounded (max envelopes/payload per request)
- Failure-tolerant (reports plainly, no infinite retry)

CONSTRAINTS:
- Sends evidence envelopes only
- No autonomous background operation
- On failure: report and stop, do not retry indefinitely

Usage:
    python -u tools/push_evidence.py --to http://192.168.1.100:8420
    python -u tools/push_evidence.py --to http://192.168.1.100:8420 --limit 100
    python -u tools/push_evidence.py --dry-run

Environment:
    CALYX_HOME_INGEST_URL - Default target URL
    CALYX_INGEST_TOKEN - Authentication token (required)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from station_calyx.evidence.journal import EvidenceJournal
from station_calyx.evidence.schemas import EvidenceEnvelopeV1
from station_calyx.node.node_identity import get_node_identity

# Constants
DEFAULT_MAX_ENVELOPES = 250
DEFAULT_MAX_PAYLOAD_BYTES = 1 * 1024 * 1024  # 1 MB
PUSH_LOG_DIR = ROOT / "logs" / "push"
PUSH_INDEX_FILE = ROOT / "outgoing" / "node" / "push_index.json"

COMPONENT_ROLE = "push_client"


@dataclass
class PushResult:
    """Result of a push operation."""
    success: bool
    accepted_count: int = 0
    rejected_count: int = 0
    error: Optional[str] = None
    http_status: Optional[int] = None
    response_data: Optional[Dict[str, Any]] = None


@dataclass
class PushLog:
    """Push operation log entry."""
    timestamp: str
    node_id: str
    target_url: str
    envelopes_sent: int
    accepted_count: int
    rejected_count: int
    success: bool
    error: Optional[str] = None
    seq_range: Optional[Tuple[int, int]] = None
    duration_ms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "target_url": self.target_url,
            "envelopes_sent": self.envelopes_sent,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "success": self.success,
            "error": self.error,
            "seq_range": list(self.seq_range) if self.seq_range else None,
            "duration_ms": self.duration_ms,
        }


def load_push_offset() -> int:
    """Load last pushed sequence number."""
    if not PUSH_INDEX_FILE.exists():
        return 0
    try:
        data = json.loads(PUSH_INDEX_FILE.read_text(encoding="utf-8"))
        return int(data.get("last_pushed_seq", 0))
    except Exception as e:
        print(f"[WARN] Failed to load push index: {e}")
        return 0


def save_push_offset(seq: int, target_url: str) -> None:
    """Persist last pushed sequence number."""
    PUSH_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    history: List[Dict] = []
    if PUSH_INDEX_FILE.exists():
        try:
            data = json.loads(PUSH_INDEX_FILE.read_text(encoding="utf-8"))
            history = data.get("history", [])
        except Exception:
            pass
    
    history.append({
        "seq": seq,
        "target": target_url,
        "pushed_at": datetime.now().isoformat(),
    })
    
    data = {
        "last_pushed_seq": seq,
        "updated_at": datetime.now().isoformat(),
        "history": history[-100:],
    }
    
    temp_path = PUSH_INDEX_FILE.with_suffix(".tmp")
    temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp_path.replace(PUSH_INDEX_FILE)


def append_push_log(log_entry: PushLog) -> None:
    """Append push log entry to JSONL file."""
    PUSH_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = PUSH_LOG_DIR / "push_log.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry.to_dict()) + "\n")


def get_unpushed_envelopes(limit: Optional[int] = None) -> List[EvidenceEnvelopeV1]:
    """Get envelopes that have not been pushed yet."""
    node = get_node_identity()
    journal = EvidenceJournal(node_id=node.node_id)
    last_pushed = load_push_offset()
    all_envelopes = journal.read_all()
    unpushed = [e for e in all_envelopes if e.seq > last_pushed]
    if limit and limit > 0:
        unpushed = unpushed[:limit]
    return unpushed


def translate_to_server_format(envelope: EvidenceEnvelopeV1) -> Dict[str, Any]:
    """
    Translate Node Evidence Relay v0 envelope to server ingest format.
    
    The server's EvidenceEnvelopeV1 schema uses different field names.
    This function bridges the two formats.
    """
    payload_canonical = json.dumps(envelope.payload, sort_keys=True, separators=(",", ":"))
    payload_hash = hashlib.sha256(payload_canonical.encode("utf-8")).hexdigest()
    
    return {
        "envelope_version": "v1",
        "node_id": envelope.node_id,
        "node_name": None,
        "captured_at_iso": envelope.timestamp,
        "seq": envelope.seq,
        "event_type": envelope.evidence_type,
        "payload": envelope.payload,
        "payload_hash": payload_hash,
        "prev_hash": envelope.prev_hash,
        "signature": None,
        "collector_version": "node-evidence-relay-v0",
    }


def chunk_envelopes(
    envelopes: List[EvidenceEnvelopeV1],
    max_count: int = DEFAULT_MAX_ENVELOPES,
    max_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
) -> List[List[EvidenceEnvelopeV1]]:
    """Split envelopes into chunks respecting count and size limits."""
    chunks: List[List[EvidenceEnvelopeV1]] = []
    current_chunk: List[EvidenceEnvelopeV1] = []
    current_size = 0
    
    for envelope in envelopes:
        envelope_json = envelope.to_json()
        envelope_size = len(envelope_json.encode("utf-8"))
        
        would_exceed_count = len(current_chunk) >= max_count
        would_exceed_size = (current_size + envelope_size) > max_bytes and len(current_chunk) > 0
        
        if would_exceed_count or would_exceed_size:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = [envelope]
            current_size = envelope_size
        else:
            current_chunk.append(envelope)
            current_size += envelope_size
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def push_envelopes(
    envelopes: List[EvidenceEnvelopeV1],
    target_url: str,
    token: str,
    timeout: int = 30,
) -> PushResult:
    """Push envelopes to target URL."""
    if not envelopes:
        return PushResult(success=True, accepted_count=0)
    
    translated = [translate_to_server_format(e) for e in envelopes]
    payload = {"envelopes": translated}
    payload_json = json.dumps(payload)
    payload_bytes = payload_json.encode("utf-8")

    url = target_url.rstrip("/") + "/v1/ingest/evidence"

    req = urllib.request.Request(
        url,
        data=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "StationCalyx-PushClient/0.1",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            response_body = response.read().decode("utf-8")
            response_data = json.loads(response_body)

        if status == 200:
            accepted = response_data.get("accepted_count", 0)
            rejected = response_data.get("rejected_count", 0)
            # Consider success if any were accepted, or if none were rejected
            is_success = accepted > 0 or rejected == 0
            # Build error message from rejection reasons if all failed
            error_msg = None
            if not is_success and rejected > 0:
                reasons = response_data.get("rejection_reasons", [])
                error_msg = reasons[0] if reasons else "All envelopes rejected"

            return PushResult(
                success=is_success,
                accepted_count=accepted,
                rejected_count=rejected,
                http_status=status,
                response_data=response_data,
                error=error_msg,
            )
        else:
            return PushResult(
                success=False,
                error=f"HTTP {status}: {response_data.get('detail', 'Unknown error')}",
                http_status=status,
                response_data=response_data,
            )

    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
            error_data = json.loads(error_body)
            error_detail = error_data.get("detail", str(e))
        except Exception:
            error_detail = error_body or str(e)

        return PushResult(
            success=False,
            error=f"HTTP {e.code}: {error_detail}",
            http_status=e.code,
        )
    
    except urllib.error.URLError as e:
        return PushResult(
            success=False,
            error=f"Connection failed: {e.reason}",
        )
    
    except Exception as e:
        return PushResult(
            success=False,
            error=f"Unexpected error: {str(e)}",
        )


def run_push(
    target_url: str,
    token: str,
    limit: Optional[int] = None,
    max_envelopes: int = DEFAULT_MAX_ENVELOPES,
    max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
    dry_run: bool = False,
) -> Tuple[bool, int, int]:
    """Run the push operation."""
    node = get_node_identity()
    
    print(f"\n{'='*60}")
    print("Station Calyx Evidence Push Client")
    print(f"{'='*60}")
    print(f"Node: {node.node_id}")
    print(f"Target: {target_url}")
    print(f"Dry run: {dry_run}")
    print()
    
    unpushed = get_unpushed_envelopes(limit=limit)
    
    if not unpushed:
        print("[INFO] No unpushed envelopes")
        return True, 0, 0
    
    print(f"[INFO] Found {len(unpushed)} unpushed envelopes")
    print(f"[INFO] Sequence range: {unpushed[0].seq} -> {unpushed[-1].seq}")
    
    if dry_run:
        print(f"\n[DRY-RUN] Would push {len(unpushed)} envelopes to {target_url}")
        chunks = chunk_envelopes(unpushed, max_envelopes, max_payload_bytes)
        print(f"[DRY-RUN] Would send in {len(chunks)} chunk(s)")
        for i, chunk in enumerate(chunks):
            print(f"  Chunk {i+1}: {len(chunk)} envelopes, seq {chunk[0].seq}-{chunk[-1].seq}")
        return True, 0, 0
    
    chunks = chunk_envelopes(unpushed, max_envelopes, max_payload_bytes)
    print(f"[INFO] Sending in {len(chunks)} chunk(s)")
    
    total_accepted = 0
    total_rejected = 0
    last_accepted_seq = load_push_offset()
    
    for i, chunk in enumerate(chunks):
        chunk_start = time.time()
        seq_start = chunk[0].seq
        seq_end = chunk[-1].seq
        
        print(f"\n[PUSH] Chunk {i+1}/{len(chunks)}: {len(chunk)} envelopes (seq {seq_start}-{seq_end})")
        
        result = push_envelopes(chunk, target_url, token)
        
        chunk_duration = int((time.time() - chunk_start) * 1000)
        
        log_entry = PushLog(
            timestamp=datetime.now().isoformat(),
            node_id=node.node_id,
            target_url=target_url,
            envelopes_sent=len(chunk),
            accepted_count=result.accepted_count,
            rejected_count=result.rejected_count,
            success=result.success,
            error=result.error,
            seq_range=(seq_start, seq_end),
            duration_ms=chunk_duration,
        )
        append_push_log(log_entry)
        
        if result.success:
            total_accepted += result.accepted_count
            total_rejected += result.rejected_count
            
            if result.accepted_count > 0:
                last_accepted_seq = seq_end
                save_push_offset(last_accepted_seq, target_url)
            
            print(f"  [OK] Accepted: {result.accepted_count}, Rejected: {result.rejected_count}")
            
            if result.rejected_count > 0 and result.response_data:
                rejections = result.response_data.get("rejection_reasons", [])
                for rej in rejections[:5]:
                    print(f"    - {rej}")
                if len(rejections) > 5:
                    print(f"    ... and {len(rejections) - 5} more")
        else:
            print(f"  [FAIL] {result.error}")
            print(f"\n[ABORT] Push failed at chunk {i+1}. Not retrying.")
            return False, total_accepted, total_rejected
    
    print(f"\n{'='*60}")
    print("PUSH COMPLETE")
    print(f"{'='*60}")
    print(f"Total accepted: {total_accepted}")
    print(f"Total rejected: {total_rejected}")
    print(f"Last pushed seq: {last_accepted_seq}")
    
    return True, total_accepted, total_rejected


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Push evidence envelopes to home workstation"
    )
    parser.add_argument(
        "--to",
        type=str,
        default=os.environ.get("CALYX_HOME_INGEST_URL"),
        help="Target URL (e.g., http://192.168.1.100:8420). Default: CALYX_HOME_INGEST_URL env var",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=os.environ.get("CALYX_INGEST_TOKEN"),
        help="Auth token. Default: CALYX_INGEST_TOKEN env var",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum total envelopes to push",
    )
    parser.add_argument(
        "--max-per-request",
        type=int,
        default=DEFAULT_MAX_ENVELOPES,
        help=f"Maximum envelopes per request (default: {DEFAULT_MAX_ENVELOPES})",
    )
    parser.add_argument(
        "--max-payload-kb",
        type=int,
        default=DEFAULT_MAX_PAYLOAD_BYTES // 1024,
        help=f"Maximum payload KB per request (default: {DEFAULT_MAX_PAYLOAD_BYTES // 1024})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be pushed without sending",
    )
    
    args = parser.parse_args(argv)
    
    if not args.to:
        print("[ERROR] Target URL required. Use --to or set CALYX_HOME_INGEST_URL")
        return 1
    
    if not args.dry_run and not args.token:
        print("[ERROR] Auth token required. Use --token or set CALYX_INGEST_TOKEN")
        return 1
    
    try:
        success, accepted, rejected = run_push(
            target_url=args.to,
            token=args.token or "",
            limit=args.limit,
            max_envelopes=args.max_per_request,
            max_payload_bytes=args.max_payload_kb * 1024,
            dry_run=args.dry_run,
        )
        return 0 if success else 1
    
    except KeyboardInterrupt:
        print("\n[ABORT] Interrupted by user")
        return 130
    
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
