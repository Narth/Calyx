"""
WO_CALYX_SIGN_INGRESS_AUTH_V4 — Per-request signature envelope and verification.
Schema: calyx.sign.req.v1
"""
from __future__ import annotations

import base64
import json
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

SCHEMA = "calyx.sign.req.v1"
SCOPE_CHAT = "chat"
TS_WINDOW_SEC = 120


def _resolve_repo_root() -> Path:
    env_root = __import__("os").environ.get("CALYX_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[2]


def canonical_dumps(obj: dict[str, Any]) -> str:
    """Stable JSON for signing (sorted keys, no whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_envelope(
    *,
    normalized_request: str,
    scope: str = SCOPE_CHAT,
    node_id: str | None = None,
    doc_policy: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str]:
    """
    Build signing envelope. Returns (envelope_dict, envelope_json_str).
    Caller hashes normalized_request for normalized_request_sha256.
    WO_GOVERNANCE_SINGULARITY_V3: Optional doc_policy for deprecated-doc override.
    """
    from .canonical_hash import sha256_hex
    ts = datetime.now(timezone.utc).isoformat()
    nonce = uuid.uuid4().hex
    norm_sha = sha256_hex(normalized_request)
    env: dict[str, Any] = {
        "schema": SCHEMA,
        "ts_utc": ts,
        "nonce": nonce,
        "scope": scope,
        "normalized_request_sha256": norm_sha,
    }
    if node_id:
        env["node_id"] = node_id
    if doc_policy is not None and isinstance(doc_policy, dict):
        env["doc_policy"] = doc_policy
    return env, canonical_dumps(env)


def verify_envelope_schema(env: dict[str, Any]) -> str | None:
    """Validate envelope. Returns None if ok, else error string.
    WO_GOVERNANCE_SINGULARITY_V3: Optional doc_policy allowed."""
    if env.get("schema") != SCHEMA:
        return "invalid_schema"
    for k in ("ts_utc", "nonce", "scope", "normalized_request_sha256"):
        if not env.get(k):
            return f"missing_{k}"
    if env.get("scope") != SCOPE_CHAT:
        return "invalid_scope"
    dp = env.get("doc_policy")
    if dp is not None:
        if not isinstance(dp, dict):
            return "doc_policy_not_object"
        inc = dp.get("include_deprecated")
        if inc is not None and not isinstance(inc, bool):
            return "doc_policy_include_deprecated_not_bool"
        scope_val = dp.get("scope")
        if scope_val is not None and scope_val not in ("repo_search_only", "global_doc_reads"):
            return "doc_policy_scope_invalid"
    return None


def verify_timestamp(ts_utc: str) -> str | None:
    """Check ts_utc within ±TS_WINDOW_SEC. Returns None if ok, else error."""
    try:
        ts = datetime.fromisoformat(ts_utc.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = abs((now - ts).total_seconds())
        if delta > TS_WINDOW_SEC:
            return f"timestamp_outside_window_{delta:.0f}s"
    except Exception as e:
        return f"timestamp_parse_error:{str(e)[:50]}"
    return None


def verify_signature(
    envelope_bytes: bytes,
    signature_b64: str,
    key_id: str,
    repo_root: Path | None = None,
) -> tuple[bool, str]:
    """
    Verify SSH signature. Returns (ok, signer_fingerprint_or_error).
    Uses governance/identities/allowed_signers.
    """
    root = repo_root or _resolve_repo_root()
    allowed_signers = root / "governance" / "identities" / "allowed_signers"
    if not allowed_signers.exists():
        return False, "allowed_signers_missing"
    try:
        sig_decoded = base64.b64decode(signature_b64, validate=True)
    except Exception:
        return False, "signature_decode_failed"
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".sig", delete=False) as f:
        sig_path = f.name
        f.write(sig_decoded)
    try:
        result = subprocess.run(
            [
                "ssh-keygen", "-Y", "verify",
                "-f", str(allowed_signers),
                "-I", key_id or "architect",
                "-n", "calyx",
                "-s", sig_path,
            ],
            input=envelope_bytes,
            capture_output=True,
            timeout=5,
            cwd=str(root),
        )
        if result.returncode == 0:
            return True, f"key:{key_id or 'architect'}"
        err = (result.stderr or b"").decode("utf-8", errors="replace").strip()
        return False, f"verify_failed:{err[:150]}"
    except FileNotFoundError:
        return False, "ssh_keygen_not_found"
    except subprocess.TimeoutExpired:
        return False, "verify_timeout"
    except Exception as e:
        return False, f"verify_error:{str(e)[:100]}"
    finally:
        try:
            Path(sig_path).unlink(missing_ok=True)
        except Exception:
            pass
