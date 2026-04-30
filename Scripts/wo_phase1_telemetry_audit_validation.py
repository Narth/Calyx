from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ts_tag() -> str:
    return now_utc().strftime("%Y%m%d_%H%M%S")


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def emit_result(path: Path, payload: dict[str, Any]) -> None:
    try:
        dump_json(path, payload)
    except PermissionError:
        print(f"RECEIPT_PATH {path}")
        print("VALIDATION_PAYLOAD_BEGIN")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print("VALIDATION_PAYLOAD_END")
    else:
        print(path)


@contextmanager
def isolated_gateway_module() -> Any:
    root = REPO_ROOT / "_validation_tmp" / f"calyx_tg_phase1_{uuid.uuid4().hex}"
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        runtime_dir = root / "runtime"
        boot_session_id = f"boot-{uuid.uuid4()}"
        marker = {
            "boot_evidence_bundle_committed": True,
            "boot_session_id": boot_session_id,
            "ts_utc": now_utc().isoformat(),
            "receipt_path": str(runtime_dir / "receipts" / "audit" / "boot_evidence_bundle__test.json"),
            "source": "wo_phase1_telemetry_audit_validation",
        }
        dump_json(runtime_dir / "boot_evidence_marker.json", marker)

        env_backup = {
            "CALYX_REPO_ROOT": os.environ.get("CALYX_REPO_ROOT"),
            "CALYX_RUNTIME_DIR": os.environ.get("CALYX_RUNTIME_DIR"),
            "CALYX_BOOT_SESSION_ID": os.environ.get("CALYX_BOOT_SESSION_ID"),
            "CBO_CHAT_URL": os.environ.get("CBO_CHAT_URL"),
        }
        os.environ["CALYX_REPO_ROOT"] = str(root)
        os.environ["CALYX_RUNTIME_DIR"] = str(runtime_dir)
        os.environ["CALYX_BOOT_SESSION_ID"] = boot_session_id
        os.environ["CBO_CHAT_URL"] = "http://127.0.0.1:7778/chat"

        sys.modules.pop("cbo_hub.telemetry_gateway.app", None)
        module = importlib.import_module("cbo_hub.telemetry_gateway.app")
        try:
            yield module, root
        finally:
            sys.modules.pop("cbo_hub.telemetry_gateway.app", None)
            for key, value in env_backup.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    finally:
        shutil.rmtree(root, ignore_errors=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def latest_receipt(receipts_dir: Path, prefix: str) -> Path | None:
    matches = sorted(receipts_dir.glob(f"{prefix}__*.json"))
    return matches[-1] if matches else None


def assert_required_fields(entry: dict[str, Any]) -> None:
    for key in (
        "ts_utc",
        "request_id",
        "phase",
        "client_id",
        "path",
        "audit_outcome",
        "body_sha256_16",
        "forwarded_for",
    ):
        if key not in entry:
            raise AssertionError(f"Missing required audit field: {key}")


def validate_success_case() -> dict[str, Any]:
    with isolated_gateway_module() as (module, root):
        downstream_calls: list[dict[str, Any]] = []

        async def fake_forward(body: dict[str, Any], request_id: str) -> tuple[dict[str, Any], int]:
            downstream_calls.append({"request_id": request_id, "body": body})
            return {"reply_text": "ok", "request_id": request_id}, 200

        module._forward_to_cbo = fake_forward
        with TestClient(module.app) as client:
            response = client.post(
                "/chat",
                json={"user_text": "hi", "session_id": "home"},
                headers={"X-Telemetry-Client-ID": "validator"},
            )
            if response.status_code != 200:
                raise AssertionError(f"Expected 200, got {response.status_code}: {response.text}")

            audit_lines = read_jsonl(root / "cbo_hub" / "logs" / "telemetry_gateway_audit.jsonl")
            if len(downstream_calls) != 1:
                raise AssertionError(f"Expected one downstream call, got {len(downstream_calls)}")
            request_id = downstream_calls[0]["request_id"]
            request_lines = [line for line in audit_lines if line.get("request_id") == request_id]
            phases = {line.get("phase") for line in request_lines}
            if phases != {"pre_forward", "post_forward"}:
                raise AssertionError(f"Expected pre/post forward lines, got phases={sorted(phases)}")
            for line in request_lines:
                assert_required_fields(line)
            status = read_json(root / "runtime" / "telemetry_gateway_audit_status.json")
            if status.get("trust_state") != "trusted":
                raise AssertionError(f"Expected trusted status, got {status}")
            readiness_receipt = latest_receipt(root / "runtime" / "receipts" / "security", "telemetry_gateway_audit_readiness")
            if readiness_receipt is None:
                raise AssertionError("Missing startup readiness receipt")

        shutdown_receipt = latest_receipt(root / "runtime" / "receipts" / "security", "telemetry_gateway_audit_shutdown")
        if shutdown_receipt is None:
            raise AssertionError("Missing shutdown receipt")
        final_status = read_json(root / "runtime" / "telemetry_gateway_audit_status.json")
        if final_status.get("trust_state") != "untrusted":
            raise AssertionError(f"Expected untrusted after shutdown, got {final_status}")
        return {
            "request_id": request_id,
            "audit_line_count": len(request_lines),
            "shutdown_receipt": str(shutdown_receipt),
        }


def validate_startup_failure_case() -> dict[str, Any]:
    with isolated_gateway_module() as (module, root):
        original_append = module._append_audit_entry

        def fail_startup(entry: dict[str, Any]) -> tuple[bool, str, str]:
            if entry.get("phase") == "startup_readiness":
                return False, "", "simulated_startup_append_failure"
            return original_append(entry)

        module._append_audit_entry = fail_startup
        startup_failed = False
        try:
            with TestClient(module.app):
                pass
        except RuntimeError as exc:
            startup_failed = "telemetry_audit_untrusted" in str(exc)
        if not startup_failed:
            raise AssertionError("Expected startup readiness failure to raise RuntimeError")
        status = read_json(root / "runtime" / "telemetry_gateway_audit_status.json")
        if status.get("trust_state") != "untrusted":
            raise AssertionError(f"Expected untrusted startup status, got {status}")
        readiness_receipt = latest_receipt(root / "runtime" / "receipts" / "security", "telemetry_gateway_audit_readiness")
        if readiness_receipt is None:
            raise AssertionError("Missing failed readiness receipt")
        return {"readiness_receipt": str(readiness_receipt)}


def validate_pre_forward_failure_case() -> dict[str, Any]:
    with isolated_gateway_module() as (module, root):
        downstream_calls: list[dict[str, Any]] = []

        async def fake_forward(body: dict[str, Any], request_id: str) -> tuple[dict[str, Any], int]:
            downstream_calls.append({"request_id": request_id, "body": body})
            return {"reply_text": "ok", "request_id": request_id}, 200

        module._forward_to_cbo = fake_forward
        with TestClient(module.app) as client:
            original_append = module._append_audit_entry

            def fail_pre_forward(entry: dict[str, Any]) -> tuple[bool, str, str]:
                if entry.get("phase") == "pre_forward":
                    return False, "", "simulated_pre_forward_append_failure"
                return original_append(entry)

            module._append_audit_entry = fail_pre_forward
            response = client.post(
                "/chat",
                json={"user_text": "fail closed", "session_id": "home"},
                headers={"X-Telemetry-Client-ID": "validator"},
            )
            if response.status_code != 503:
                raise AssertionError(f"Expected 503, got {response.status_code}: {response.text}")
            failure_receipt = latest_receipt(root / "runtime" / "receipts" / "security", "telemetry_gateway_audit_failure")
            if failure_receipt is None:
                raise AssertionError("Missing failure receipt for pre-forward append failure")
            failure = read_json(failure_receipt)
            request_id = failure.get("request_id")
            if not request_id:
                raise AssertionError("Failure receipt missing request_id")
            if any(call["request_id"] == request_id for call in downstream_calls):
                raise AssertionError(f"Request {request_id} should not have been forwarded downstream")
            status = read_json(root / "runtime" / "telemetry_gateway_audit_status.json")
            if status.get("trust_state") != "untrusted":
                raise AssertionError(f"Expected untrusted after pre-forward failure, got {status}")
            return {"request_id": request_id, "failure_receipt": str(failure_receipt)}


def validate_post_forward_failure_case() -> dict[str, Any]:
    with isolated_gateway_module() as (module, root):
        downstream_calls: list[dict[str, Any]] = []

        async def fake_forward(body: dict[str, Any], request_id: str) -> tuple[dict[str, Any], int]:
            downstream_calls.append({"request_id": request_id, "body": body})
            return {"reply_text": "ok", "request_id": request_id}, 200

        module._forward_to_cbo = fake_forward
        with TestClient(module.app) as client:
            original_append = module._append_audit_entry

            def fail_post_forward(entry: dict[str, Any]) -> tuple[bool, str, str]:
                if entry.get("phase") == "post_forward":
                    return False, "", "simulated_post_forward_append_failure"
                return original_append(entry)

            module._append_audit_entry = fail_post_forward
            response = client.post(
                "/chat",
                json={"user_text": "post forward", "session_id": "home"},
                headers={"X-Telemetry-Client-ID": "validator"},
            )
            if response.status_code != 200:
                raise AssertionError(f"Expected first request to complete, got {response.status_code}: {response.text}")
            if len(downstream_calls) != 1:
                raise AssertionError(f"Expected one downstream call before downgrade, got {len(downstream_calls)}")

            failure_receipt = latest_receipt(root / "runtime" / "receipts" / "security", "telemetry_gateway_audit_failure")
            if failure_receipt is None:
                raise AssertionError("Missing failure receipt for post-forward append failure")
            failure = read_json(failure_receipt)
            request_id = failure.get("request_id")
            if request_id != downstream_calls[0]["request_id"]:
                raise AssertionError("Post-forward failure receipt request_id does not match downstream call request_id")

            status = read_json(root / "runtime" / "telemetry_gateway_audit_status.json")
            if status.get("trust_state") != "untrusted":
                raise AssertionError(f"Expected untrusted after post-forward failure, got {status}")

            second = client.post(
                "/chat",
                json={"user_text": "blocked after downgrade", "session_id": "home"},
                headers={"X-Telemetry-Client-ID": "validator"},
            )
            if second.status_code != 503:
                raise AssertionError(f"Expected second request to fail closed, got {second.status_code}: {second.text}")

            return {"request_id": request_id, "failure_receipt": str(failure_receipt)}


def main() -> int:
    audit_dir = REPO_ROOT / "runtime" / "receipts" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    stamp = ts_tag()

    checks: dict[str, dict[str, Any]] = {}
    overall_ok = True
    for name, fn in (
        ("startup_and_success", validate_success_case),
        ("startup_failure", validate_startup_failure_case),
        ("pre_forward_failure", validate_pre_forward_failure_case),
        ("post_forward_failure", validate_post_forward_failure_case),
    ):
        try:
            checks[name] = {"status": "ok", "details": fn()}
        except Exception as exc:
            overall_ok = False
            checks[name] = {"status": "failed", "error": str(exc)}

    payload = {
        "schema": "audit.wo_phase1_telemetry_audit_validation.v1",
        "receipt_type": "audit.wo_phase1_telemetry_audit_validation",
        "phase": "validation",
        "status": "ok" if overall_ok else "failed",
        "timestamp_utc": now_utc().isoformat(),
        "checks": checks,
    }
    receipt_path = audit_dir / f"wo_phase1_telemetry_audit_validation__{stamp}.json"
    emit_result(receipt_path, payload)
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
