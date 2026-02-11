from __future__ import annotations

import hashlib
import hmac
import os
import time
import uuid
from collections import defaultdict, deque
from typing import Deque

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Calyx Gateway MVP", version="0.1.0")

HMAC_SECRET = os.getenv("CALYX_GATEWAY_HMAC_SECRET", "")
MAX_RPM = int(os.getenv("CALYX_GATEWAY_MAX_RPM", "60"))
STATION_BASE_URL = os.getenv("CALYX_STATION_BASE_URL", "http://127.0.0.1:8420")
REQUEST_WINDOW_S = 60

_rate_buckets: dict[str, Deque[int]] = defaultdict(deque)


class ReflectRequest(BaseModel):
    recent: int = Field(default=100, ge=1, le=10_000)
    session_id: str | None = None


def _check_rate_limit(client_key: str) -> None:
    now = int(time.time())
    bucket = _rate_buckets[client_key]

    while bucket and (now - bucket[0]) >= REQUEST_WINDOW_S:
        bucket.popleft()

    if len(bucket) >= MAX_RPM:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    bucket.append(now)


def _verify_hmac(body: bytes, timestamp: str, signature: str) -> None:
    if not HMAC_SECRET:
        raise HTTPException(status_code=503, detail="Gateway HMAC secret not configured")

    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid timestamp") from exc

    now = int(time.time())
    if abs(now - ts) > 60:
        raise HTTPException(status_code=401, detail="Timestamp skew too large")

    payload = timestamp.encode("utf-8") + b"." + body
    expected = hmac.new(HMAC_SECRET.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    normalized_sig = signature.removeprefix("sha256=")
    if not hmac.compare_digest(expected, normalized_sig):
        raise HTTPException(status_code=401, detail="Invalid signature")


@app.post("/gateway/v1/reflect")
async def gateway_reflect(
    body: ReflectRequest,
    x_calyx_key_id: str = Header(default="anonymous", alias="X-Calyx-Key-Id"),
    x_calyx_timestamp: str = Header(..., alias="X-Calyx-Timestamp"),
    x_calyx_signature: str = Header(..., alias="X-Calyx-Signature"),
):
    request_id = str(uuid.uuid4())[:12]
    raw_body = body.model_dump_json().encode("utf-8")

    _verify_hmac(raw_body, x_calyx_timestamp, x_calyx_signature)
    _check_rate_limit(x_calyx_key_id)

    url = f"{STATION_BASE_URL}/v1/reflect"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, json=body.model_dump())

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail="Upstream station error")

    return {
        "request_id": request_id,
        "upstream": "station_calyx",
        "data": response.json(),
    }
