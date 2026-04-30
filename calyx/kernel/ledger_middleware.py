"""
Request-scoped corr_id middleware for Station Event Ledger.
WO_NERVOUS_SYSTEM_PHASE1. Attach corr_id to request context; emit station.smoke at boundary.
"""
from __future__ import annotations

import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .event_ledger import emit, set_corr_id, clear_human_auth_context


def _emit_safe(level: str, component: str, event: str, msg: str, data: dict | None = None) -> None:
    """Emit to ledger. Never throws."""
    try:
        emit(level=level, component=component, event=event, msg=msg, data=data or {})
    except Exception:
        pass


class LedgerCorrIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware: generate corr_id per request, set in context, emit station.smoke (DEBUG).
    Downstream emit() calls reuse corr_id when not provided.
    """

    def __init__(self, app: object, service_name: str = "cbo"):
        super().__init__(app)
        self._service_name = (service_name or "cbo").strip()[:32]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        corr_id = str(uuid.uuid4())
        set_corr_id(corr_id)
        request.state.corr_id = corr_id
        try:
            _emit_safe(
                "DEBUG",
                self._service_name,
                "station.smoke",
                f"Request {request.method} {request.url.path}",
                data={"path": request.url.path, "method": request.method},
            )
            response = await call_next(request)
            return response
        finally:
            set_corr_id(None)
            clear_human_auth_context()
