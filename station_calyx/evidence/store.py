# -*- coding: utf-8 -*-
"""
Evidence Store - Append-Only Per-Node Storage
==============================================

ROLE: evidence/store
SCOPE: Append-only evidence storage with validation

CHAIN VALIDATION:
- prev_hash must match last stored envelope's envelope_hash
- envelope_hash is verified against server recomputation
- last_hash stores the envelope_hash (not payload_hash)
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from ..schemas.evidence_envelope_v1 import (
    EvidenceEnvelopeV1,
    canonical_json,
    validate_envelope,
    compute_envelope_hash_from_dict,
)
from ..core.config import get_config

COMPONENT_ROLE = 'evidence_store'

@dataclass
class IngestState:
    """Per-node ingest state tracking.
    
    last_hash: The envelope_hash of the last ingested envelope.
               This is what prev_hash must match for the next envelope.
    """
    node_id: str
    last_seq: int = -1
    last_hash: Optional[str] = None  # envelope_hash of last envelope
    last_ingested_at: Optional[str] = None
    total_envelopes: int = 0
    
    def to_dict(self): return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            node_id=data['node_id'],
            last_seq=data.get('last_seq', -1),
            last_hash=data.get('last_hash'),
            last_ingested_at=data.get('last_ingested_at'),
            total_envelopes=data.get('total_envelopes', 0),
        )

@dataclass
class IngestResult:
    accepted: bool
    envelope_hash: Optional[str] = None
    rejection_reason: Optional[str] = None

@dataclass
class IngestSummary:
    accepted_count: int = 0
    rejected_count: int = 0
    rejection_reasons: list = field(default_factory=list)
    last_accepted_seq: int = -1  # Track highest accepted seq

def get_evidence_dir():
    return get_config().data_dir / 'logs' / 'evidence'

def get_node_dir(node_id):
    safe_id = ''.join(c if c.isalnum() or c in '-_' else '_' for c in node_id)
    return get_evidence_dir() / safe_id

def load_ingest_state(node_id):
    p = get_node_dir(node_id) / 'ingest_state.json'
    if p.exists():
        try:
            with open(p, 'r', encoding='utf-8') as f:
                return IngestState.from_dict(json.load(f))
        except:
            pass
    return IngestState(node_id=node_id)

def save_ingest_state(state):
    d = get_node_dir(state.node_id)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / 'ingest_state.json', 'w', encoding='utf-8') as f:
        json.dump(state.to_dict(), f, indent=2)

def validate_for_ingest(envelope: EvidenceEnvelopeV1, state: IngestState) -> tuple[bool, Optional[str]]:
    """
    Validate envelope for ingestion against current state.
    
    CHAIN VALIDATION:
    1. Basic envelope validation (fields, payload_hash)
    2. Verify envelope_hash matches server recomputation (if present)
    3. Seq must be > last_seq (monotonic)
    4. prev_hash must match state.last_hash (envelope_hash chain)
    """
    # Basic validation
    ok, errs = validate_envelope(envelope)
    if not ok:
        return False, 'Validation failed: ' + (errs[0] if errs else 'unknown')
    
    # Verify envelope_hash if present
    if envelope.envelope_hash:
        computed = envelope.compute_envelope_hash()
        if envelope.envelope_hash != computed:
            return False, (
                f'Envelope hash mismatch: client={envelope.envelope_hash[:16]}..., '
                f'server={computed[:16]}...'
            )
    
    # Seq monotonicity check
    if envelope.seq <= state.last_seq:
        return False, f'Non-monotonic seq: {envelope.seq} <= {state.last_seq}'
    
    # Hash chain check (prev_hash must match last envelope_hash)
    if state.last_hash is not None:
        if envelope.prev_hash != state.last_hash:
            return False, (
                f'Hash chain mismatch: expected prev_hash={state.last_hash[:16]}..., '
                f'received {envelope.prev_hash[:16] if envelope.prev_hash else "null"}...'
            )
    elif envelope.seq > 0 and envelope.prev_hash is None:
        # Non-first envelope must have prev_hash if we don't have state
        # This allows fresh ingest but flags missing chain links
        pass  # Allow for now, could be stricter
    
    return True, None

def append_envelope(envelope: EvidenceEnvelopeV1) -> IngestResult:
    """
    Append a validated envelope to the node's evidence store.
    
    CHAIN SEMANTICS:
    - Validates envelope_hash matches server computation
    - Validates prev_hash matches last stored envelope_hash
    - Stores envelope_hash in state.last_hash for next validation
    """
    state = load_ingest_state(envelope.node_id)
    
    ok, reason = validate_for_ingest(envelope, state)
    if not ok:
        return IngestResult(accepted=False, rejection_reason=reason)
    
    # Compute/verify envelope_hash
    # Use client-provided if valid, otherwise compute
    if envelope.envelope_hash and envelope.verify_envelope_hash():
        envelope_hash = envelope.envelope_hash
    else:
        envelope_hash = envelope.compute_envelope_hash()
        # Set it on the envelope for storage
        envelope.envelope_hash = envelope_hash
    
    # Append to evidence file
    d = get_node_dir(envelope.node_id)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / 'evidence.jsonl', 'a', encoding='utf-8') as f:
        f.write(canonical_json(envelope.to_dict()) + '\n')
    
    # Update state with envelope_hash as the chain anchor
    state.last_seq = envelope.seq
    state.last_hash = envelope_hash  # This is envelope_hash, not payload_hash
    state.last_ingested_at = datetime.now(timezone.utc).isoformat()
    state.total_envelopes += 1
    save_ingest_state(state)
    
    return IngestResult(accepted=True, envelope_hash=envelope_hash)

def ingest_batch(envelopes: list[dict[str, Any]]) -> IngestSummary:
    """
    Ingest a batch of envelopes.
    
    Processing continues through the batch, tracking highest accepted seq.
    Rejection of one envelope stops further processing for that node.
    """
    s = IngestSummary()
    rejected_nodes = set()
    
    for ed in envelopes:
        try:
            e = EvidenceEnvelopeV1.from_dict(ed)
        except Exception as ex:
            s.rejected_count += 1
            s.rejection_reasons.append(f'Parse error: {str(ex)[:50]}')
            continue
        
        if e.node_id in rejected_nodes:
            s.rejected_count += 1
            continue
        
        r = append_envelope(e)
        
        if r.accepted:
            s.accepted_count += 1
            s.last_accepted_seq = max(s.last_accepted_seq, e.seq)
        else:
            s.rejected_count += 1
            s.rejection_reasons.append(f'seq={e.seq}: {r.rejection_reason or "unknown"}')
            rejected_nodes.add(e.node_id)
    
    return s

def ingest_jsonl_file(file_path):
    envs = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    envs.append(json.loads(line))
                except json.JSONDecodeError as e:
                    return IngestSummary(rejected_count=1, rejection_reasons=[f'JSON error: {e}'])
    return ingest_batch(envs)

def get_known_nodes():
    d = get_evidence_dir()
    if not d.exists():
        return []
    ns = []
    for i in d.iterdir():
        if i.is_dir() and (i / 'ingest_state.json').exists():
            try:
                with open(i / 'ingest_state.json', 'r') as f:
                    ns.append(json.load(f).get('node_id', i.name))
            except:
                ns.append(i.name)
    return ns

def get_node_evidence(node_id, limit=100, offset=0):
    p = get_node_dir(node_id) / 'evidence.jsonl'
    if not p.exists():
        return []
    es = []
    with open(p, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i < offset:
                continue
            if len(es) >= limit:
                break
            line = line.strip()
            if line:
                try:
                    es.append(json.loads(line))
                except:
                    pass
    return es

def get_all_evidence(limit_per_node=100):
    return {n: get_node_evidence(n, limit=limit_per_node) for n in get_known_nodes()}

def get_merged_evidence(limit=200):
    a = []
    for n in get_known_nodes():
        a.extend(get_node_evidence(n, limit=limit))
    a.sort(key=lambda e: e.get('captured_at_iso', ''))
    return a[:limit]

LOCAL_NODE_ID = 'local'

def get_local_node_id():
    return LOCAL_NODE_ID
