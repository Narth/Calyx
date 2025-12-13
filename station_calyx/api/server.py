"""
Station Calyx API Server
========================

Local-only FastAPI server for the Ops Reflector service.

INVARIANTS:
- LOCAL-ONLY: Binds to 127.0.0.1 only
- NO_HIDDEN_CHANNELS: All requests logged
- EXECUTION_GATE: Deny-all (no execution endpoints in v1)

Role: api/server
Scope: HTTP server lifecycle management

Usage:
    uvicorn station_calyx.api.server:app --host 127.0.0.1 --port 8420
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..core.config import get_config
from ..core.evidence import append_event, create_event
from .routes import router

# Role declaration
COMPONENT_ROLE = "api_server"
COMPONENT_SCOPE = "HTTP server lifecycle and middleware"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("station_calyx.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    config = get_config()
    
    # Startup
    logger.info(f"Starting {config.station_name} v{config.version}")
    logger.info(f"Advisory-only mode: {config.advisory_only}")
    logger.info(f"Execution enabled: {config.execution_enabled}")
    logger.info(f"Data directory: {config.data_dir}")
    
    # Log startup event
    try:
        event = create_event(
            event_type="SERVICE_STARTED",
            node_role=COMPONENT_ROLE,
            summary=f"{config.station_name} API server started",
            payload={
                "version": config.version,
                "host": config.api_host,
                "port": config.api_port,
                "advisory_only": config.advisory_only,
            },
            tags=["lifecycle", "startup"],
        )
        append_event(event)
    except Exception as e:
        logger.warning(f"Failed to log startup event: {e}")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {config.station_name}")
    
    try:
        event = create_event(
            event_type="SERVICE_STOPPED",
            node_role=COMPONENT_ROLE,
            summary=f"{config.station_name} API server stopped",
            payload={"version": config.version},
            tags=["lifecycle", "shutdown"],
        )
        append_event(event)
    except Exception:
        pass


# Create FastAPI app
app = FastAPI(
    title="Station Calyx Ops Reflector",
    description="Local-first, governance-first advisory service. v1: Advisory-only, deny-all execution.",
    version="1.0.0-alpha",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware (local-only, permissive for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:*", "http://localhost:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests (INVARIANT: NO_HIDDEN_CHANNELS)."""
    start_time = datetime.now(timezone.utc)
    
    response = await call_next(request)
    
    # Log request (skip health checks to reduce noise)
    if request.url.path not in ["/health", "/v1/health"]:
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} ({duration_ms:.1f}ms)"
        )
    
    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Log error event
    try:
        event = create_event(
            event_type="ERROR",
            node_role=COMPONENT_ROLE,
            summary=f"Unhandled exception: {type(exc).__name__}",
            payload={
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "path": str(request.url.path),
                "method": request.method,
            },
            tags=["error", "exception"],
        )
        append_event(event)
    except Exception:
        pass
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


# Include routes
app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service info."""
    config = get_config()
    return {
        "service": config.station_name,
        "version": config.version,
        "status": "operational",
        "advisory_only": config.advisory_only,
        "execution_enabled": config.execution_enabled,
        "docs": "/docs",
        "endpoints": {
            "status": "/v1/status",
            "ingest": "/v1/ingest",
            "snapshot": "/v1/snapshot",
            "reflect": "/v1/reflect",
        },
        "invariants": [
            "HUMAN_PRIMACY: Advisory-only by default",
            "EXECUTION_GATE: Deny-all; no command execution in v1",
            "NO_HIDDEN_CHANNELS: All meaningful activity is logged",
            "APPEND_ONLY_EVIDENCE: JSONL event log for every event",
            "ROLE_DECLARATION: Every component declares role + scope",
        ],
    }


def run_server(host: str = "127.0.0.1", port: int = 8420):
    """Run the server programmatically."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
