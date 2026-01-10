# -*- coding: utf-8 -*-
"""
Station Calyx API Client
========================

Thin client for communicating with Station Calyx API.

ROLE: presentation_layer/api_client
SCOPE: HTTP communication with local API only

CONSTRAINTS:
- Read-only where possible
- All writes go through API
- No direct file/evidence access
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin

COMPONENT_ROLE = "api_client"
COMPONENT_SCOPE = "HTTP communication with local API"

DEFAULT_BASE_URL = "http://127.0.0.1:8420"


@dataclass
class APIResponse:
    """Response from API call."""
    success: bool
    status_code: int
    data: Optional[dict[str, Any]]
    error: Optional[str]


class CalyxAPIClient:
    """
    Client for Station Calyx API.
    
    All interactions with the service go through this client.
    The UI layer never directly accesses files or evidence.
    """
    
    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self._timeout = 10
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
    ) -> APIResponse:
        """Make HTTP request to API."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            headers = {"Content-Type": "application/json"}
            body = json.dumps(data).encode() if data else None
            
            req = Request(url, data=body, headers=headers, method=method)
            
            with urlopen(req, timeout=self._timeout) as response:
                response_data = json.loads(response.read().decode())
                return APIResponse(
                    success=True,
                    status_code=response.status,
                    data=response_data,
                    error=None,
                )
        except HTTPError as e:
            try:
                error_body = json.loads(e.read().decode())
                error_msg = error_body.get("detail", str(e))
            except:
                error_msg = str(e)
            return APIResponse(
                success=False,
                status_code=e.code,
                data=None,
                error=error_msg,
            )
        except URLError as e:
            return APIResponse(
                success=False,
                status_code=0,
                data=None,
                error=f"Connection failed: {e.reason}",
            )
        except Exception as e:
            return APIResponse(
                success=False,
                status_code=0,
                data=None,
                error=str(e),
            )
    
    def _get(self, endpoint: str) -> APIResponse:
        return self._request("GET", endpoint)
    
    def _post(self, endpoint: str, data: Optional[dict[str, Any]] = None) -> APIResponse:
        return self._request("POST", endpoint, data or {})
    
    # --- Health & Status ---
    
    def health_check(self) -> APIResponse:
        """Check if API is reachable."""
        return self._get("/v1/health")
    
    def get_status(self) -> APIResponse:
        """Get technical service status."""
        return self._get("/v1/status")
    
    def get_human_status(self) -> APIResponse:
        """Get human-readable status."""
        return self._get("/v1/status/human")
    
    # --- Intent ---
    
    def get_intent(self) -> APIResponse:
        """Get current user intent."""
        return self._get("/v1/intent")
    
    def set_intent(self, profile: str, description: str = "") -> APIResponse:
        """Set user intent."""
        return self._post("/v1/intent", {
            "profile": profile,
            "description": description,
        })
    
    # --- Actions (Triggers) ---
    
    def capture_snapshot(self) -> APIResponse:
        """Trigger snapshot capture."""
        return self._post("/v1/snapshot")
    
    def run_reflection(self, recent: int = 100) -> APIResponse:
        """Trigger reflection generation."""
        return self._post("/v1/reflect", {"recent": recent})
    
    def generate_advisory(self, recent: int = 100) -> APIResponse:
        """Trigger advisory generation."""
        return self._post("/v1/advise", {"recent": recent})
    
    def run_temporal_analysis(self, recent: int = 1000) -> APIResponse:
        """Trigger temporal analysis."""
        return self._post("/v1/analyze/temporal", {"recent": recent})
    
    def get_assessment(self, recent: int = 500) -> APIResponse:
        """Get human-readable system assessment."""
        return self._get(f"/v1/assess?recent={recent}")
    
    # --- Data Retrieval ---
    
    def get_trends(self) -> APIResponse:
        """Get recent trends."""
        return self._get("/v1/trends")
    
    def get_notifications(self) -> APIResponse:
        """Get recent notifications."""
        return self._get("/v1/notifications/recent")
    
    def get_events(self, recent: int = 50) -> APIResponse:
        """Get recent events."""
        return self._get(f"/v1/events?recent={recent}")


# Global client instance
_client: Optional[CalyxAPIClient] = None


def get_client(base_url: str = DEFAULT_BASE_URL) -> CalyxAPIClient:
    """Get or create API client."""
    global _client
    if _client is None or _client.base_url != base_url:
        _client = CalyxAPIClient(base_url)
    return _client


def is_service_running(base_url: str = DEFAULT_BASE_URL) -> bool:
    """Quick check if service is running."""
    client = get_client(base_url)
    response = client.health_check()
    return response.success


if __name__ == "__main__":
    print(f"[{COMPONENT_ROLE}] Role: {COMPONENT_SCOPE}")
    print(f"Service running: {is_service_running()}")
