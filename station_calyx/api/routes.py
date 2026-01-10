"""
Station Calyx API Routes
========================

Local-only API endpoints for the Ops Reflector service.

INVARIANT: LOCAL-ONLY
- API binds to 127.0.0.1 only
- No external access permitted in v1

Role: api/routes
Scope: HTTP endpoint definitions
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..core.config import get_config
from ..core.evidence import (
    append_event,
    create_event,
    load_recent_events,
    get_last_event_ts,
    compute_sha256,
    generate_session_id,
)
from ..core.policy import get_policy_gate, request_execution
from ..core.intent import (
    UserIntent,
    AdvisoryProfile,
    load_current_intent,
    save_intent,
    create_intent,
    get_or_create_default_intent,
)
from ..connectors.sys_telemetry import collect_snapshot, format_snapshot_summary
from ..agents.reflector import reflect, save_reflection, log_reflection_event
from ..agents.advisor import generate_advisory, save_advisory, log_advisory_event
from ..agents.temporal import (
    run_temporal_analysis,
    save_temporal_analysis,
    log_temporal_event,
    log_finding_events,
)
from ..ui.status_surface import generate_status_surface, format_status_markdown, save_status_surface
from ..core.notifications import get_notifications_from_evidence

# Role declaration
COMPONENT_ROLE = "api_routes"
COMPONENT_SCOPE = "HTTP endpoint request handling"

# Create router
router = APIRouter(prefix="/v1", tags=["v1"])


# --- Request/Response Models ---

class StatusResponse(BaseModel):
    """Service status response."""
    station_name: str
    version: str
    status: str = "operational"
    last_event_ts: Optional[str] = None
    events_total: int = 0
    policy: dict[str, Any] = Field(default_factory=dict)
    advisory_only: bool = True
    execution_enabled: bool = False


class IngestRequest(BaseModel):
    """Event ingestion request."""
    event_type: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    session_id: Optional[str] = None


class IngestResponse(BaseModel):
    """Event ingestion response."""
    success: bool
    event_id: str
    timestamp: str
    message: str


class SnapshotResponse(BaseModel):
    """System snapshot response."""
    success: bool
    timestamp: str
    snapshot: dict[str, Any]
    summary: str
    event_logged: bool


class ReflectRequest(BaseModel):
    """Reflection request."""
    recent: int = Field(default=100, ge=1, le=10000)
    session_id: Optional[str] = None


class ReflectResponse(BaseModel):
    """Reflection response."""
    success: bool
    session_id: str
    events_analyzed: int
    reflection: dict[str, Any]
    artifacts: dict[str, str]
    message: str


# --- Endpoints ---

@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """
    GET /v1/status
    
    Returns basic service info and last event timestamp.
    """
    config = get_config()
    policy_gate = get_policy_gate()
    
    # Count events
    events = load_recent_events(10000)
    
    return StatusResponse(
        station_name=config.station_name,
        version=config.version,
        status="operational",
        last_event_ts=get_last_event_ts(),
        events_total=len(events),
        policy=policy_gate.get_stats(),
        advisory_only=config.advisory_only,
        execution_enabled=config.execution_enabled,
    )


@router.post("/ingest", response_model=IngestResponse)
async def ingest_event(request: IngestRequest) -> IngestResponse:
    """
    POST /v1/ingest
    
    Accept event payload and write to evidence.jsonl.
    """
    session_id = request.session_id or generate_session_id()
    
    try:
        event = create_event(
            event_type=request.event_type,
            node_role="api_ingest",
            summary=request.summary,
            payload=request.payload,
            tags=request.tags,
            session_id=session_id,
        )
        
        append_event(event)
        
        return IngestResponse(
            success=True,
            event_id=event.get("_hash", "unknown")[:16],
            timestamp=event["ts"],
            message=f"Event ingested: {request.event_type}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest event: {e}")


@router.post("/snapshot", response_model=SnapshotResponse)
async def capture_snapshot() -> SnapshotResponse:
    """
    POST /v1/snapshot
    
    Capture system snapshot (read-only) and log event.
    """
    try:
        snapshot = collect_snapshot()
        summary = format_snapshot_summary(snapshot)
        
        # Log snapshot event
        event = create_event(
            event_type="SYSTEM_SNAPSHOT",
            node_role="sys_telemetry",
            summary=f"System snapshot: {snapshot.get('hostname', 'unknown')} @ {snapshot.get('timestamp', 'unknown')}",
            payload=snapshot,
            tags=["snapshot", "telemetry"],
        )
        append_event(event)
        
        return SnapshotResponse(
            success=True,
            timestamp=snapshot["timestamp"],
            snapshot=snapshot,
            summary=summary,
            event_logged=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to capture snapshot: {e}")


@router.post("/reflect", response_model=ReflectResponse)
async def run_reflection(request: ReflectRequest) -> ReflectResponse:
    """
    POST /v1/reflect
    
    Run reflector over recent events and output reflection artifact.
    """
    session_id = request.session_id or generate_session_id()
    
    try:
        # Load recent events
        events = load_recent_events(request.recent)
        
        # Run reflection
        reflection = reflect(events, session_id=session_id)
        
        # Save artifacts
        md_path, json_path = save_reflection(reflection)
        
        # Log reflection event
        log_reflection_event(reflection, md_path, json_path)
        
        return ReflectResponse(
            success=True,
            session_id=session_id,
            events_analyzed=len(events),
            reflection=reflection,
            artifacts={
                "markdown": str(md_path),
                "json": str(json_path),
            },
            message=f"Reflection complete: {len(reflection.get('highlights', []))} highlights, {len(reflection.get('anomalies', []))} anomalies",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run reflection: {e}")


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "station-calyx-ops-reflector"}


# --- Intent Endpoints (Milestone 2) ---

class IntentSetRequest(BaseModel):
    """Request to set user intent."""
    profile: str = Field(..., description="Advisory profile: STABILITY_FIRST, PERFORMANCE_SENSITIVE, RESOURCE_CONSTRAINED, DEVELOPER_WORKSTATION")
    description: str = Field(..., description="Free text description of intent")


class IntentResponse(BaseModel):
    """User intent response."""
    intent_id: str
    description: str
    advisory_profile: str
    created_at: str
    framing: dict[str, Any]


class AdviseRequest(BaseModel):
    """Request to generate advisory."""
    recent: int = Field(default=100, ge=1, le=10000)
    session_id: Optional[str] = None


class AdviseResponse(BaseModel):
    """Advisory response."""
    success: bool
    session_id: str
    events_analyzed: int
    intent_profile: str
    advisory_notes_count: int
    advisory: dict[str, Any]
    artifacts: dict[str, str]
    guardrail_passed: bool
    message: str


@router.get("/intent", response_model=IntentResponse)
async def get_intent() -> IntentResponse:
    """
    GET /v1/intent
    
    Return current user intent.
    """
    intent = get_or_create_default_intent()
    
    return IntentResponse(
        intent_id=intent.intent_id,
        description=intent.description,
        advisory_profile=intent.advisory_profile.value,
        created_at=intent.created_at.isoformat(),
        framing=intent.get_framing(),
    )


@router.post("/intent", response_model=IntentResponse)
async def set_intent(request: IntentSetRequest) -> IntentResponse:
    """
    POST /v1/intent
    
    Set or update current user intent.
    Logs INTENT_SET event to evidence.
    """
    try:
        profile = AdvisoryProfile.from_string(request.profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    intent = create_intent(
        description=request.description,
        profile=profile,
    )
    
    save_intent(intent, log_event=True)
    
    return IntentResponse(
        intent_id=intent.intent_id,
        description=intent.description,
        advisory_profile=intent.advisory_profile.value,
        created_at=intent.created_at.isoformat(),
        framing=intent.get_framing(),
    )


@router.post("/advise", response_model=AdviseResponse)
async def run_advisory(request: AdviseRequest) -> AdviseResponse:
    """
    POST /v1/advise
    
    Run advisor using latest reflection and current intent.
    
    GUARDRAILS:
    - Never proposes commands
    - Never suggests execution
    - All statements reference evidence
    """
    session_id = request.session_id or generate_session_id()
    
    try:
        # Load events
        events = load_recent_events(request.recent)
        
        # Get current intent
        intent = get_or_create_default_intent()
        
        # Run reflection first
        reflection = reflect(events, session_id=session_id)
        
        # Generate advisory
        advisory = generate_advisory(events, reflection, intent, session_id=session_id)
        
        # Save artifacts
        md_path, json_path = save_advisory(advisory)
        
        # Log event
        log_advisory_event(advisory, md_path, json_path)
        
        notes_count = len(advisory.get("advisory_notes", []))
        guardrail_passed = advisory.get("guardrail_check", {}).get("passed", True)
        
        return AdviseResponse(
            success=True,
            session_id=session_id,
            events_analyzed=len(events),
            intent_profile=intent.advisory_profile.value,
            advisory_notes_count=notes_count,
            advisory=advisory,
            artifacts={
                "markdown": str(md_path),
                "json": str(json_path),
            },
            guardrail_passed=guardrail_passed,
            message=f"Advisory complete: {notes_count} note(s) generated for {intent.advisory_profile.value} profile",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate advisory: {e}")


# --- Temporal Endpoints (Milestone 3) ---

class TemporalRequest(BaseModel):
    """Request for temporal analysis."""
    recent: int = Field(default=1000, ge=10, le=100000, description="Number of recent events to analyze")
    session_id: Optional[str] = None


class TemporalResponse(BaseModel):
    """Temporal analysis response."""
    success: bool
    session_id: str
    events_analyzed: int
    snapshots_analyzed: int
    time_span_hours: float
    trends_count: int
    drifts_count: int
    patterns_count: int
    total_findings: int
    analysis: dict[str, Any]
    artifacts: dict[str, str]
    guardrails_passed: bool
    message: str


class TrendsResponse(BaseModel):
    """Recent trends response."""
    trends_detected: list[dict[str, Any]]
    drift_warnings: list[dict[str, Any]]
    recurring_patterns: list[dict[str, Any]]
    last_analysis_ts: Optional[str]


@router.post("/analyze/temporal", response_model=TemporalResponse)
async def run_temporal(request: TemporalRequest) -> TemporalResponse:
    """
    POST /v1/analyze/temporal
    
    Run temporal analyzer to detect trends, drift, and recurring patterns.
    
    GUARDRAILS:
    - Never predicts failure dates
    - Never recommends execution
    - Explicitly states uncertainty
    - References historical evidence for every claim
    """
    session_id = request.session_id or generate_session_id()
    
    try:
        # Load events
        events = load_recent_events(request.recent)
        
        # Run temporal analysis
        analysis = run_temporal_analysis(events, session_id=session_id)
        
        # Save artifacts
        md_path, json_path = save_temporal_analysis(analysis)
        
        # Log completion event
        log_temporal_event(analysis, md_path, json_path)
        
        # Log individual findings as events
        all_findings = (
            analysis.get("trends_detected", []) +
            analysis.get("drift_warnings", []) +
            analysis.get("recurring_patterns", [])
        )
        if all_findings:
            log_finding_events(all_findings, session_id)
        
        guardrails = analysis.get("guardrails", {})
        guardrails_passed = all(guardrails.values()) if guardrails else True
        
        return TemporalResponse(
            success=True,
            session_id=session_id,
            events_analyzed=analysis.get("events_analyzed", 0),
            snapshots_analyzed=analysis.get("snapshots_analyzed", 0),
            time_span_hours=analysis.get("time_span_hours", 0),
            trends_count=len(analysis.get("trends_detected", [])),
            drifts_count=len(analysis.get("drift_warnings", [])),
            patterns_count=len(analysis.get("recurring_patterns", [])),
            total_findings=analysis.get("total_findings", 0),
            analysis=analysis,
            artifacts={
                "markdown": str(md_path),
                "json": str(json_path),
            },
            guardrails_passed=guardrails_passed,
            message=f"Temporal analysis complete: {analysis.get('total_findings', 0)} findings over {analysis.get('time_span_hours', 0)}h",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run temporal analysis: {e}")


@router.get("/trends", response_model=TrendsResponse)
async def get_trends() -> TrendsResponse:
    """
    GET /v1/trends
    
    Returns most recent temporal findings from evidence log.
    """
    events = load_recent_events(1000)
    
    # Find most recent TEMPORAL_ANALYSIS_COMPLETED event
    temporal_events = [e for e in events if e.get("event_type") == "TEMPORAL_ANALYSIS_COMPLETED"]
    
    if not temporal_events:
        return TrendsResponse(
            trends_detected=[],
            drift_warnings=[],
            recurring_patterns=[],
            last_analysis_ts=None,
        )
    
    latest = temporal_events[-1]
    last_ts = latest.get("ts")
    
    # Find individual finding events after this analysis
    trends = []
    drifts = []
    patterns = []
    
    for e in events:
        if e.get("event_type") == "TREND_DETECTED":
            trends.append({
                "metric_name": e.get("payload", {}).get("metric_name"),
                "direction": e.get("payload", {}).get("direction"),
                "confidence": e.get("payload", {}).get("confidence"),
                "values_summary": e.get("payload", {}).get("values_summary"),
                "timestamp": e.get("ts"),
            })
        elif e.get("event_type") == "DRIFT_WARNING":
            drifts.append({
                "metric_name": e.get("payload", {}).get("metric_name"),
                "direction": e.get("payload", {}).get("direction"),
                "confidence": e.get("payload", {}).get("confidence"),
                "values_summary": e.get("payload", {}).get("values_summary"),
                "timestamp": e.get("ts"),
            })
        elif e.get("event_type") == "PATTERN_RECURRING":
            patterns.append({
                "metric_name": e.get("payload", {}).get("metric_name"),
                "confidence": e.get("payload", {}).get("confidence"),
                "values_summary": e.get("payload", {}).get("values_summary"),
                "timestamp": e.get("ts"),
            })
    
    return TrendsResponse(
        trends_detected=trends[-10:],
        drift_warnings=drifts[-10:],
        recurring_patterns=patterns[-10:],
        last_analysis_ts=last_ts,
    )


# --- Trust Surface Endpoints (Milestone 4) ---

class HumanStatusResponse(BaseModel):
    """Human-readable status response."""
    system_state: dict[str, Any]
    intent: Optional[dict[str, Any]]
    latest_snapshot: Optional[dict[str, Any]]
    recent_advisories: list[dict[str, Any]]
    active_findings: dict[str, Any]
    generated_at: str
    markdown: str


class NotificationsResponse(BaseModel):
    """Recent notifications response."""
    notifications: list[dict[str, Any]]
    total_count: int


@router.get("/status/human", response_model=HumanStatusResponse)
async def get_human_status() -> HumanStatusResponse:
    """
    GET /v1/status/human
    
    Returns human-friendly status summary.
    
    Philosophy: Gentle presence - inform without alarming.
    """
    status = generate_status_surface()
    markdown = format_status_markdown(status)
    
    # Also save to file
    save_status_surface(status)
    
    return HumanStatusResponse(
        system_state=status.get("system_state", {}),
        intent=status.get("intent"),
        latest_snapshot=status.get("latest_snapshot"),
        recent_advisories=status.get("recent_advisories", []),
        active_findings=status.get("active_findings", {}),
        generated_at=status.get("generated_at", ""),
        markdown=markdown,
    )


# --- Human Assessment Endpoint (Human Translation Layer) ---

class AssessmentResponse(BaseModel):
    """Human-readable system assessment response."""
    success: bool
    generated_at: str
    environment: dict[str, Any]
    settling: dict[str, Any]
    trajectories: list[dict[str, Any]]
    readiness: dict[str, Any]
    plain_language: str


@router.get("/assess", response_model=AssessmentResponse)
async def get_assessment(recent: int = 500) -> AssessmentResponse:
    """
    GET /v1/assess
    
    Returns human-readable system assessment using the Human Translation Layer.
    
    This endpoint converts evidence into plain-language assessments for human understanding.
    
    CALYX AGENT CONTRACT:
    - Describes observed behavior only
    - No recommendations or action items
    - No implied intelligence or authority
    """
    from ..agents.human_translation import generate_human_assessment
    
    events = load_recent_events(min(recent, 2000))
    assessment = generate_human_assessment(events, recent)
    
    return AssessmentResponse(
        success=True,
        generated_at=assessment.generated_at.isoformat(),
        environment=assessment.to_dict()["environment"],
        settling=assessment.to_dict()["settling"],
        trajectories=assessment.to_dict()["trajectories"],
        readiness=assessment.to_dict()["readiness"],
        plain_language=assessment.to_plain_language(),
    )


@router.get("/notifications/recent", response_model=NotificationsResponse)
async def get_recent_notifications_endpoint() -> NotificationsResponse:
    """
    GET /v1/notifications/recent
    
    Returns recent notifications from evidence log.
    """
    notifications = get_notifications_from_evidence(limit=20)
    
    return NotificationsResponse(
        notifications=notifications,
        total_count=len(notifications),
    )


# --- Evidence Relay Endpoints (Node Evidence Relay v0) ---

class EvidenceIngestRequest(BaseModel):
    """Request for evidence ingest."""
    envelopes: list[dict[str, Any]] = Field(
        default=[],
        description="List of evidence envelopes to ingest"
    )
    # Also accept single envelope at root level
    envelope_version: Optional[str] = None
    node_id: Optional[str] = None
    

class EvidenceIngestResponse(BaseModel):
    """Response from evidence ingest."""
    success: bool
    accepted_count: int
    rejected_count: int
    rejection_reasons: list[str] = Field(
        default=[],
        description="Bounded list of rejection reasons (max 10)"
    )
    message: str


@router.post("/ingest/evidence", response_model=EvidenceIngestResponse)
async def ingest_evidence(request: EvidenceIngestRequest) -> EvidenceIngestResponse:
    """
    POST /v1/ingest/evidence
    
    Ingest evidence envelopes from remote nodes.
    
    Accepts either:
    - { "envelopes": [ ... ] } — batch of envelopes
    - Single envelope object at root level
    
    CONSTRAINTS:
    - Evidence ingest only (no commands)
    - Deterministic validation
    - Append-only storage
    - Receiver never "trusts conclusions"
    
    VALIDATION:
    - Required fields must be present
    - seq must be > last_seq for node
    - payload_hash must match computed
    - prev_hash must match last_hash
    """
    from ..evidence.store import ingest_batch
    from ..schemas.evidence_envelope_v1 import REQUIRED_FIELDS
    
    # Collect envelopes from request
    envelopes = []
    
    # Check for batch format
    if request.envelopes:
        envelopes.extend(request.envelopes)
    
    # Check for single envelope at root
    if request.envelope_version and request.node_id:
        # Reconstruct single envelope from request fields
        single_envelope = request.model_dump(exclude_none=True)
        if "envelopes" in single_envelope:
            del single_envelope["envelopes"]
        envelopes.append(single_envelope)
    
    if not envelopes:
        return EvidenceIngestResponse(
            success=False,
            accepted_count=0,
            rejected_count=0,
            rejection_reasons=["No envelopes provided"],
            message="No envelopes to ingest",
        )
    
    # Ingest batch
    summary = ingest_batch(envelopes)
    
    success = summary.accepted_count > 0 or summary.rejected_count == 0
    
    return EvidenceIngestResponse(
        success=success,
        accepted_count=summary.accepted_count,
        rejected_count=summary.rejected_count,
        rejection_reasons=summary.rejection_reasons[:10],
        message=f"Ingested {summary.accepted_count} envelope(s), rejected {summary.rejected_count}",
    )


class NodeStatusResponse(BaseModel):
    """Status of evidence for a specific node."""
    node_id: str
    last_seq: int
    last_hash: Optional[str]
    last_ingested_at: Optional[str]
    total_envelopes: int


class NodesListResponse(BaseModel):
    """List of known nodes."""
    nodes: list[str]
    node_statuses: dict[str, NodeStatusResponse]


@router.get("/nodes", response_model=NodesListResponse)
async def list_nodes() -> NodesListResponse:
    """
    GET /v1/nodes
    
    List all known nodes that have evidence stored.
    """
    from ..evidence.store import get_known_nodes, load_ingest_state
    
    nodes = get_known_nodes()
    statuses = {}
    
    for node_id in nodes:
        state = load_ingest_state(node_id)
        statuses[node_id] = NodeStatusResponse(
            node_id=state.node_id,
            last_seq=state.last_seq,
            last_hash=state.last_hash,
            last_ingested_at=state.last_ingested_at,
            total_envelopes=state.total_envelopes,
        )
    
    return NodesListResponse(
        nodes=nodes,
        node_statuses=statuses,
    )


@router.get("/nodes/{node_id}/evidence")
async def get_node_evidence_endpoint(
    node_id: str,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """
    GET /v1/nodes/{node_id}/evidence
    
    Get evidence from a specific node.
    """
    from ..evidence.store import get_node_evidence, get_known_nodes
    
    if node_id not in get_known_nodes():
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
    
    envelopes = get_node_evidence(node_id, limit=limit, offset=offset)
    
    return {
        "node_id": node_id,
        "count": len(envelopes),
        "offset": offset,
        "envelopes": envelopes,
    }
