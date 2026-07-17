#!/usr/bin/env python3
"""
WO_CALYX_SIGN_INGRESS_AUTH_V4 — Sign a /chat request for direct governed ingress.
Output: headers to paste into Curl/Postman/Cursor.
Usage: python Scripts/calyx_sign_request.py "Produce the latest Station heartbeat." [--key-path PATH] [--key-id architect]
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _resolve_repo_root() -> Path:
    env_root = os.environ.get("CALYX_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Sign a /chat request for Calyx Sign ingress auth")
    ap.add_argument("request_text", help="The user request text (will be normalized: stripped)")
    ap.add_argument("--key-path", default=os.environ.get("CALYX_SIGN_KEY_PATH", "V:/calyx_identity/architect_ed25519"), help="Path to private key")
    ap.add_argument("--key-id", default="architect", help="Key identity (must match allowed_signers)")
    ap.add_argument("--scope", default="chat", help="Scope (chat)")
    ap.add_argument("--node-id", default="", help="Optional node_id for envelope")
    args = ap.parse_args()

    repo_root = _resolve_repo_root()
    norm_req = (args.request_text or "").strip()
    if not norm_req:
        print("Error: request text is empty", file=sys.stderr)
        return 1

    from calyx.kernel.canonical_hash import sha256_hex
    norm_sha = sha256_hex(norm_req)
    ts = datetime.now(timezone.utc).isoformat()
    nonce = uuid.uuid4().hex
    envelope = {
        "schema": "calyx.sign.req.v1",
        "ts_utc": ts,
        "nonce": nonce,
        "scope": args.scope,
        "normalized_request_sha256": norm_sha,
    }
    if args.node_id:
        envelope["node_id"] = args.node_id
    envelope_json = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    envelope_bytes = envelope_json.encode("utf-8")

    key_path = Path(args.key_path).expanduser()
    if not key_path.exists():
        print(f"Error: Key not found: {key_path}", file=sys.stderr)
        print("Set CALYX_SIGN_KEY_PATH or use --key-path. Key is typically on mounted VHD: V:\\calyx_identity\\architect_ed25519", file=sys.stderr)
        return 1

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".sig", delete=False) as f:
        sig_path = f.name
    try:
        result = subprocess.run(
            ["ssh-keygen", "-Y", "sign", "-f", str(key_path), "-n", "calyx", "-I", args.key_id],
            input=envelope_bytes,
            capture_output=True,
            timeout=10,
            cwd=str(repo_root),
        )
        if result.returncode != 0:
            err = (result.stderr or b"").decode("utf-8", errors="replace")
            print(f"Error: ssh-keygen sign failed: {err}", file=sys.stderr)
            return 1
        sig_bytes = result.stdout
    finally:
        Path(sig_path).unlink(missing_ok=True)

    envelope_b64 = base64.b64encode(envelope_bytes).decode("ascii")
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")

    print("# Paste these headers into your request:")
    print("# X-Calyx-Key-Id:", args.key_id)
    print("# X-Calyx-Sign-Envelope: (base64)")
    print("# X-Calyx-Signature: (base64)")
    print()
    print("X-Calyx-Key-Id:", args.key_id)
    print("X-Calyx-Sign-Envelope:", envelope_b64)
    print("X-Calyx-Signature:", sig_b64)
    print()
    body = json.dumps({"user_text": norm_req, "session_id": "signed"})
    print("# Curl example (request body must match signed envelope):")
    print(f'curl -X POST http://127.0.0.1:7778/chat \\')
    print(f'  -H "Content-Type: application/json" \\')
    print(f'  -H "X-Calyx-Key-Id: {args.key_id}" \\')
    print(f'  -H "X-Calyx-Sign-Envelope: {envelope_b64}" \\')
    print(f'  -H "X-Calyx-Signature: {sig_b64}" \\')
    print(f"  -d '{body}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
