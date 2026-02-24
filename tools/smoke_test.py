#!/usr/bin/env python3
"""
Deployment smoke test — Lane 0: does Station Calyx boot and respond?
Validates CBO API, Dev Harness, and CBO Core. Writes receipt to runtime/deployment/smoke_receipt.jsonl.
Usage: python tools/smoke_test.py [--cbo-api-url URL] [--dev-harness-url URL] [--cbo-core-url URL]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = REPO_ROOT / "runtime" / "deployment" / "smoke_receipt.jsonl"


def _url(base: str, path: str) -> str:
    return base.rstrip("/") + path


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    msg = f"  {name}: {status}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Station Calyx deployment smoke test")
    parser.add_argument(
        "--cbo-api-url",
        default="http://127.0.0.1:8080",
        help="CBO API base URL (default: http://127.0.0.1:8080)",
    )
    parser.add_argument(
        "--dev-harness-url",
        default="http://127.0.0.1:7777",
        help="Dev Harness base URL (default: http://127.0.0.1:7777)",
    )
    parser.add_argument(
        "--cbo-core-url",
        default="http://127.0.0.1:7778",
        help="CBO Core base URL (default: http://127.0.0.1:7778)",
    )
    args = parser.parse_args()

    results: list[dict] = []
    all_ok = True

    # 1. GET /heartbeat on CBO API
    try:
        r = httpx.get(_url(args.cbo_api_url, "/heartbeat"), timeout=10.0)
        ok = r.status_code == 200 and isinstance(r.json(), dict)
        results.append({"check": "cbo_api_heartbeat", "ok": ok, "status_code": r.status_code})
        if not check("CBO API /heartbeat", ok, f"status={r.status_code}"):
            all_ok = False
    except Exception as e:
        results.append({"check": "cbo_api_heartbeat", "ok": False, "error": str(e)[:200]})
        check("CBO API /heartbeat", False, str(e))
        all_ok = False

    # 2. GET /docs on Dev Harness
    try:
        r = httpx.get(_url(args.dev_harness_url, "/docs"), timeout=10.0)
        ok = r.status_code == 200
        results.append({"check": "dev_harness_docs", "ok": ok, "status_code": r.status_code})
        if not check("Dev Harness /docs", ok, f"status={r.status_code}"):
            all_ok = False
    except Exception as e:
        results.append({"check": "dev_harness_docs", "ok": False, "error": str(e)[:200]})
        check("Dev Harness /docs", False, str(e))
        all_ok = False

    # 3. GET /docs on CBO Core
    try:
        r = httpx.get(_url(args.cbo_core_url, "/docs"), timeout=10.0)
        ok = r.status_code == 200
        results.append({"check": "cbo_core_docs", "ok": ok, "status_code": r.status_code})
        if not check("CBO Core /docs", ok, f"status={r.status_code}"):
            all_ok = False
    except Exception as e:
        results.append({"check": "cbo_core_docs", "ok": False, "error": str(e)[:200]})
        check("CBO Core /docs", False, str(e))
        all_ok = False

    # 4. POST /objective on CBO API, verify in GET /report (objectives_pending incremented)
    obj_before = -1
    try:
        r_report = httpx.get(_url(args.cbo_api_url, "/report"), timeout=10.0)
        if r_report.status_code == 200:
            data = r_report.json()
            obj_before = data.get("objectives_pending", -1)
    except Exception:
        pass

    try:
        r_post = httpx.post(
            _url(args.cbo_api_url, "/objective"),
            json={"description": "smoke_test_objective", "priority": 1},
            timeout=10.0,
        )
        if r_post.status_code != 200:
            results.append({"check": "cbo_api_objective", "ok": False, "status_code": r_post.status_code})
            check("CBO API POST /objective", False, f"status={r_post.status_code}")
            all_ok = False
        else:
            r_report2 = httpx.get(_url(args.cbo_api_url, "/report"), timeout=10.0)
            obj_after = r_report2.json().get("objectives_pending", -1) if r_report2.status_code == 200 else -1
            ok = obj_after >= obj_before + 1
            results.append({
                "check": "cbo_api_objective",
                "ok": ok,
                "objectives_before": obj_before,
                "objectives_after": obj_after,
            })
            if not check("CBO API POST /objective → /report", ok, f"pending {obj_before}→{obj_after}"):
                all_ok = False
    except Exception as e:
        results.append({"check": "cbo_api_objective", "ok": False, "error": str(e)[:200]})
        check("CBO API POST /objective", False, str(e))
        all_ok = False

    # 5. POST /chat (no-model) on CBO Core, verify receipt_sha256
    try:
        r = httpx.post(
            _url(args.cbo_core_url, "/chat"),
            json={"user_text": "smoke test", "model_role": "none"},
            timeout=30.0,
        )
        if r.status_code != 200:
            results.append({"check": "cbo_core_chat", "ok": False, "status_code": r.status_code})
            check("CBO Core POST /chat", False, f"status={r.status_code}")
            all_ok = False
        else:
            data = r.json()
            sha = data.get("receipt_sha256") or ""
            ok = bool(sha and len(sha) >= 32)
            results.append({"check": "cbo_core_chat", "ok": ok, "receipt_sha256": sha[:64] if sha else None})
            if not check("CBO Core POST /chat (receipt_sha256)", ok, sha[:16] + "..." if sha else "missing"):
                all_ok = False
    except Exception as e:
        results.append({"check": "cbo_core_chat", "ok": False, "error": str(e)[:200]})
        check("CBO Core POST /chat", False, str(e))
        all_ok = False

    # Write receipt
    receipt = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "tool": "smoke_test",
        "cbo_api_url": args.cbo_api_url,
        "dev_harness_url": args.dev_harness_url,
        "cbo_core_url": args.cbo_core_url,
        "all_pass": all_ok,
        "results": results,
    }
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RECEIPT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(receipt, sort_keys=True) + "\n")

    print()
    print("PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
