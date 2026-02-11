#!/usr/bin/env python3
"""
Dashboard Authentication
Ed25519 key-based authentication
Phase A - Backend Skeleton (Placeholder for Phase D)
"""
from __future__ import annotations

import os
from typing import Optional, Tuple


def _dev_mode_enabled() -> bool:
    return os.getenv("CALYX_DEV_MODE", "false").lower() == "true"


def verify_signature(signature: str, public_key: str) -> bool:
    """
    Verify Ed25519 signature.

    Hard-fails outside explicit developer mode until real verification is wired.
    """
    if _dev_mode_enabled():
        return bool(signature and public_key)
    raise PermissionError(
        "Dashboard auth verification backend is not configured. "
        "Set CALYX_DEV_MODE=true for local development only."
    )


def authenticate_request(request_data: dict, signature: str) -> Tuple[bool, Optional[str]]:
    """
    Authenticate API request.

    In non-dev mode this fails closed so public deployments cannot run with placeholder auth.
    """
    if _dev_mode_enabled():
        if not signature:
            return False, None
        return True, "user1"

    raise PermissionError(
        "Authentication is required but production auth backend is not configured. "
        "Refusing request by default."
    )


def get_user_permissions(human_id: str) -> list[str]:
    """Get user permissions."""
    if _dev_mode_enabled():
        return ["read", "write", "approve", "admin"]
    return ["read"]
