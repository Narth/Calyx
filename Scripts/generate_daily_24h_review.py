#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = REPO_ROOT / "runtime"
LEDGER_DIR = RUNTIME_DIR / "ledger"
AUDIT_DIR = RUNTIME_DIR / "receipts" / "audit"
SECURITY_DIR = RUNTIME_DIR / "receipts" / "security"
TEMPLATE_PATH = REPO_ROOT / "docs" / "operations" / "DAILY_24H_REVIEW_TEMPLATE_V1.md"
ALLOWED_RUNTIME_SYSTEM_EVENTS = {"heartbeat.tick", "heartbeat.restart.detected"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).astimezone(timezone.utc)
    except ValueError:
        return None


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    try:
        return json.loads(read_text(path))
    except Exception:
        return None


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    except FileNotFoundError:
        pass
    return rows


def run_powershell(script: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def load_window_ledger(start_utc: datetime, end_utc: datetime) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ledger_path in sorted(LEDGER_DIR.glob("station_events__*.jsonl")):
        for row in iter_jsonl(ledger_path):
            ts = parse_dt(str(row.get("ts_utc") or row.get("ts") or ""))
            if ts and start_utc <= ts <= end_utc:
                row["_parsed_ts_utc"] = iso_z(ts)
                rows.append(row)
    rows.sort(key=lambda row: row.get("_parsed_ts_utc", ""))
    return rows


def load_json_receipts(directory: Path, pattern: str, start_utc: datetime, end_utc: datetime) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob(pattern)):
        payload = read_json(path)
        if not isinstance(payload, dict):
            continue
        ts = parse_dt(str(payload.get("ts_utc") or payload.get("timestamp_utc") or ""))
        if ts and start_utc <= ts <= end_utc:
            payload["_path"] = str(path)
            payload["_parsed_ts_utc"] = iso_z(ts)
            rows.append(payload)
    rows.sort(key=lambda row: row.get("_parsed_ts_utc", ""))
    return rows


def compute_heartbeat_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    sends = [row for row in events if row.get("event") == "discord.heartbeat.sent"]
    intervals_min: list[float] = []
    prior_ts: datetime | None = None
    refresh_failures = 0
    for row in sends:
        ts = parse_dt(row.get("_parsed_ts_utc"))
        if not ts:
            continue
        if prior_ts is not None:
            intervals_min.append((ts - prior_ts).total_seconds() / 60.0)
        prior_ts = ts
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        refresh_ok = data.get("refresh_ok")
        refresh_rc = data.get("refresh_rc")
        if refresh_ok is False or (refresh_rc not in (None, 0)):
            refresh_failures += 1
    metrics: dict[str, Any] = {
        "count": len(sends),
        "refresh_failures": refresh_failures,
        "window_has_enough_samples": len(intervals_min) > 0,
    }
    if intervals_min:
        metrics["interval_min_minutes"] = round(min(intervals_min), 2)
        metrics["interval_median_minutes"] = round(statistics.median(intervals_min), 2)
        metrics["interval_max_minutes"] = round(max(intervals_min), 2)
    else:
        metrics["interval_min_minutes"] = None
        metrics["interval_median_minutes"] = None
        metrics["interval_max_minutes"] = None
    return metrics


def compute_health_metrics(start_utc: datetime, end_utc: datetime) -> dict[str, Any]:
    history_path = RUNTIME_DIR / "station_health_history.jsonl"
    samples: list[dict[str, Any]] = []
    for row in iter_jsonl(history_path):
        ts = parse_dt(str(row.get("ts") or row.get("health_ts") or ""))
        if ts and start_utc <= ts <= end_utc:
            samples.append(row)
    peaks = {
        "sample_count": len(samples),
        "health_non_pass_count": sum(1 for row in samples if row.get("health") not in (None, "pass")),
        "memory_pressure_nonzero_count": sum(1 for row in samples if int(row.get("memory_pressure_tier") or 0) > 0),
        "oom_imminent_count": sum(1 for row in samples if bool(row.get("oom_imminent"))),
        "cpu_pct_max": max((int(row.get("cpu_pct") or 0) for row in samples), default=None),
        "ram_pct_max": max((int(row.get("ram_pct") or 0) for row in samples), default=None),
        "gpu_util_pct_max": max((int(row.get("gpu_util_pct") or 0) for row in samples), default=None),
    }
    current = read_json(RUNTIME_DIR / "station_health.json")
    if isinstance(current, dict):
        peaks["current_health"] = current.get("health")
        peaks["current_health_ts"] = current.get("health_ts")
        peaks["current_truth_state"] = current.get("truth_state")
    else:
        peaks["current_health"] = None
        peaks["current_health_ts"] = None
        peaks["current_truth_state"] = None
    return peaks


def compute_truth_metrics(start_utc: datetime, end_utc: datetime) -> dict[str, Any]:
    transitions = load_json_receipts(SECURITY_DIR, "runtime_truth_transition__*.json", start_utc, end_utc)
    ttl_expired = [
        row for row in transitions
        if row.get("transition") == "fresh_to_stale" and row.get("reason") == "ttl_expired"
    ]
    graceful_shutdowns = [
        row for row in transitions
        if row.get("reason") == "graceful_shutdown"
    ]
    restarts = [
        row for row in transitions
        if str(row.get("reason") or "").startswith("restart") or str(row.get("transition") or "").startswith("restart")
    ]
    contradictions = 0
    for artifact_name in ("STATE.md", "station_heartbeat.json", "service_runtime_snapshot.json", "runtime_topology_snapshot.json"):
        if artifact_name == "STATE.md":
            text = read_text(REPO_ROOT / "STATE.md")
            marker = "runtime_truth_expires_ts:"
            state_marker = "runtime_truth_state:"
            expires_raw = ""
            state_raw = ""
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith(marker):
                    expires_raw = stripped.split(":", 1)[1].strip()
                elif stripped.startswith(state_marker):
                    state_raw = stripped.split(":", 1)[1].strip()
            expires_dt = parse_dt(expires_raw)
            if expires_dt and expires_dt < utc_now() and state_raw == "fresh":
                contradictions += 1
        else:
            artifact = read_json(RUNTIME_DIR / artifact_name)
            if isinstance(artifact, dict):
                expires_dt = parse_dt(str(artifact.get("expires_ts_utc") or ""))
                if expires_dt and expires_dt < utc_now() and artifact.get("truth_state") == "fresh":
                    contradictions += 1
    return {
        "self_demotion_count": len(ttl_expired),
        "graceful_shutdown_count": len(graceful_shutdowns),
        "restart_count": len(restarts),
        "contradiction_count": contradictions,
        "latest_transition_path": transitions[-1]["_path"] if transitions else None,
    }


def compute_lifecycle_metrics(start_utc: datetime, end_utc: datetime) -> dict[str, Any]:
    sunrise_receipts = load_json_receipts(RUNTIME_DIR / "receipts", "sunrise_receipt__*.json", start_utc, end_utc)
    truth_metrics = compute_truth_metrics(start_utc, end_utc)
    return {
        "sunrise_count": len(sunrise_receipts),
        "sunset_count": truth_metrics["graceful_shutdown_count"],
        "restart_count": truth_metrics["restart_count"],
        "latest_sunrise_path": sunrise_receipts[-1]["_path"] if sunrise_receipts else None,
        "latest_sunrise_ts_utc": sunrise_receipts[-1].get("ts_utc") if sunrise_receipts else None,
    }


def compute_causal_integrity(events: list[dict[str, Any]]) -> dict[str, Any]:
    audit_context_missing = sum(1 for row in events if row.get("event") == "audit.context.missing")
    runtime_misuse = 0
    for row in events:
        if row.get("causal_kind") != "system":
            continue
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        system_phase = data.get("system_phase") or row.get("system_phase")
        if system_phase == "runtime" and row.get("event") not in ALLOWED_RUNTIME_SYSTEM_EVENTS:
            runtime_misuse += 1
    return {
        "audit_context_missing_count": audit_context_missing,
        "runtime_system_misuse_count": runtime_misuse,
    }


def compute_experimental_boundary(start_utc: datetime, end_utc: datetime) -> dict[str, Any]:
    experimental_receipts = load_json_receipts(RUNTIME_DIR / "receipts" / "experimental", "*.json", start_utc, end_utc)
    baseline_paths = [
        REPO_ROOT / "STATE.md",
        RUNTIME_DIR / "station_health.json",
        RUNTIME_DIR / "station_heartbeat.json",
        RUNTIME_DIR / "service_runtime_snapshot.json",
        RUNTIME_DIR / "runtime_topology_snapshot.json",
    ]
    contamination_hits = 0
    for path in baseline_paths:
        if path.exists() and "experimental" in read_text(path).lower():
            contamination_hits += 1
    sessions_opened = sum(1 for row in experimental_receipts if Path(str(row.get("_path", ""))).name.startswith("cem.session.start__"))
    sessions_closed = sum(1 for row in experimental_receipts if Path(str(row.get("_path", ""))).name.startswith("cem.session.close__"))
    sessions_aborted = sum(1 for row in experimental_receipts if Path(str(row.get("_path", ""))).name.startswith("cem.session.abort__"))
    return {
        "baseline_contamination_count": contamination_hits,
        "cem_sessions_opened": sessions_opened,
        "cem_sessions_closed": sessions_closed,
        "cem_sessions_aborted": sessions_aborted,
    }


def current_probe_summary() -> str:
    code, out, _ = run_powershell("& 'Scripts/check_calyx_core_services.ps1' | Select-Object -First 1")
    if code != 0 and not out:
        return "dev_harness=fail,cbo_core=fail,avatar_web=fail,telemetry_gateway=fail"
    return out.strip() or "dev_harness=fail,cbo_core=fail,avatar_web=fail,telemetry_gateway=fail"


def current_truth_summary() -> dict[str, Any]:
    state_text = read_text(REPO_ROOT / "STATE.md")
    state_truth = {"runtime_truth_state": "unknown", "runtime_truth_expires_ts": "", "status": ""}
    for line in state_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("runtime_truth_state:"):
            state_truth["runtime_truth_state"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("runtime_truth_expires_ts:"):
            state_truth["runtime_truth_expires_ts"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Status:"):
            state_truth["status"] = stripped.split(":", 1)[1].strip()
    return state_truth


def telemetry_trust_summary() -> dict[str, Any]:
    status_path = RUNTIME_DIR / "telemetry_gateway_audit_status.json"
    payload = read_json(status_path)
    if not isinstance(payload, dict):
        return {"trust_state": "unknown", "append_health": "unknown", "path": str(status_path)}
    append_health = "ok" if not payload.get("last_error") else "issue"
    return {
        "trust_state": payload.get("trust_state") or "unknown",
        "append_health": append_health,
        "path": str(status_path),
    }


def load_previous_review() -> dict[str, Any] | None:
    candidates = sorted(AUDIT_DIR.glob("daily_24h_review__*.json"))
    if not candidates:
        return None
    payload = read_json(candidates[-1])
    return payload if isinstance(payload, dict) else None


def render_metrics_payload(start_utc: datetime, end_utc: datetime) -> dict[str, Any]:
    events = load_window_ledger(start_utc, end_utc)
    return {
        "window": {"start_ts_utc": iso_z(start_utc), "end_ts_utc": iso_z(end_utc)},
        "heartbeat": compute_heartbeat_metrics(events),
        "lifecycle": compute_lifecycle_metrics(start_utc, end_utc),
        "current_probe": current_probe_summary(),
        "health": compute_health_metrics(start_utc, end_utc),
        "truth": compute_truth_metrics(start_utc, end_utc),
        "telemetry": telemetry_trust_summary(),
        "causal_integrity": compute_causal_integrity(events),
        "experimental_boundary": compute_experimental_boundary(start_utc, end_utc),
        "current_truth": current_truth_summary(),
        "source_paths": [
            str(REPO_ROOT / "STATE.md"),
            str(RUNTIME_DIR / "station_health.json"),
            str(RUNTIME_DIR / "station_health_history.jsonl"),
            str(RUNTIME_DIR / "station_heartbeat.json"),
            str(RUNTIME_DIR / "service_runtime_snapshot.json"),
            str(RUNTIME_DIR / "runtime_topology_snapshot.json"),
            str(LEDGER_DIR),
            str(RUNTIME_DIR / "receipts"),
            str(TEMPLATE_PATH),
        ],
    }


def build_operational_summary(metrics: dict[str, Any]) -> list[str]:
    hb = metrics["heartbeat"]
    lifecycle = metrics["lifecycle"]
    health = metrics["health"]
    truth = metrics["truth"]
    telemetry = metrics["telemetry"]
    cadence = "insufficient window data"
    if hb["window_has_enough_samples"]:
        cadence = f"{hb['interval_min_minutes']}/{hb['interval_median_minutes']}/{hb['interval_max_minutes']}m"
    pressure_note = (
        f"CPU max {health['cpu_pct_max']}%, RAM max {health['ram_pct_max']}%, GPU max {health['gpu_util_pct_max']}%"
        if health["sample_count"] > 0
        else "no recent health samples"
    )
    truth_result = "fresh when needed"
    if truth["self_demotion_count"] > 0:
        truth_result += ", self-demotion worked"
    else:
        truth_result += ", no passive self-demotion observed"
    return [
        f"Heartbeats: {hb['count']} sends, cadence {cadence}, failures {hb['refresh_failures']}",
        f"Lifecycle: sunrise {lifecycle['sunrise_count']}, sunset {lifecycle['sunset_count']}, restarts {lifecycle['restart_count']}",
        f"Runtime: {metrics['current_probe']}",
        f"Health: {health['current_health'] or 'unknown'}, {pressure_note}, oom events {health['oom_imminent_count']}",
        f"Truth discipline: {truth_result}, contradictions {truth['contradiction_count']}",
        f"Telemetry trust: {telemetry['trust_state']}, append health {telemetry['append_health']}",
    ]


def build_watchpoints(metrics: dict[str, Any]) -> list[str]:
    watchpoints: list[str] = []
    if metrics["causal_integrity"]["audit_context_missing_count"] > 0:
        watchpoints.append(
            f"audit.context.missing appeared {metrics['causal_integrity']['audit_context_missing_count']} times in the window"
        )
    if metrics["causal_integrity"]["runtime_system_misuse_count"] > 0:
        watchpoints.append(
            f"system_phase=runtime misuse count {metrics['causal_integrity']['runtime_system_misuse_count']}"
        )
    if metrics["truth"]["contradiction_count"] > 0:
        watchpoints.append(f"derived truth contradiction count {metrics['truth']['contradiction_count']}")
    if metrics["experimental_boundary"]["baseline_contamination_count"] > 0:
        watchpoints.append(
            f"experimental contamination markers found on {metrics['experimental_boundary']['baseline_contamination_count']} baseline surface(s)"
        )
    if metrics["telemetry"]["trust_state"] != "trusted":
        watchpoints.append(f"telemetry trust_state is {metrics['telemetry']['trust_state']}")
    if not watchpoints:
        watchpoints.append("no active governance watchpoint exceeded threshold in this cycle")
    return watchpoints[:3]


def build_changes(metrics: dict[str, Any], previous_review: dict[str, Any] | None) -> list[str]:
    changes: list[str] = []
    current_probe = metrics["current_probe"]
    prev_probe = None
    if previous_review and isinstance(previous_review.get("metrics"), dict):
        prev_probe = previous_review["metrics"].get("current_probe")
    if not previous_review:
        changes.append("initial automated daily review; no prior cycle artifact available for comparison")
    elif prev_probe and prev_probe != current_probe:
        changes.append(f"runtime probe changed from {prev_probe} to {current_probe}")
    if metrics["truth"]["self_demotion_count"] > 0:
        changes.append("derived runtime truth self-demotion remained active in the review window")
    if metrics["experimental_boundary"]["cem_sessions_opened"] > 0:
        changes.append(
            f"CEM sessions observed: opened {metrics['experimental_boundary']['cem_sessions_opened']}, closed {metrics['experimental_boundary']['cem_sessions_closed']}, aborted {metrics['experimental_boundary']['cem_sessions_aborted']}"
        )
    if metrics["telemetry"]["trust_state"] == "trusted":
        changes.append("telemetry audit boundary remained trusted")
    return changes[:3] or ["no material shift detected against the prior cycle"]


def build_operator_context_note() -> list[str]:
    return []


def pick_local_model() -> tuple[str | None, str]:
    env_model = (os.getenv("LOCAL_LLM_MODEL_ID") or "").strip()
    if env_model:
        return env_model, "env:LOCAL_LLM_MODEL_ID"
    try:
        proc = subprocess.run(
            ["ollama", "list"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if proc.returncode == 0 and proc.stdout:
            lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
            if len(lines) > 1:
                model_name = lines[1].split()[0].strip()
                if model_name:
                    return model_name, "ollama:list:first"
    except Exception:
        pass
    return None, "unavailable"


def strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        if len(parts) >= 3:
            inner = parts[1]
            return inner.split("\n", 1)[1] if "\n" in inner else inner
    return cleaned


def parse_sectioned_response(text: str) -> dict[str, list[str]] | None:
    mapping = {
        "OPERATIONAL_SUMMARY": "operational_summary",
        "WATCHPOINTS_RETAINED": "watchpoints_retained",
        "CHANGES_SINCE_LAST_CYCLE": "changes_since_last_cycle",
        "OPERATOR_CONTEXT_NOTE": "operator_context_note",
    }
    sections = {value: [] for value in mapping.values()}
    current_key: str | None = None
    for raw_line in strip_code_fence(text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line in mapping:
            current_key = mapping[line]
            continue
        if current_key is None:
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        sections[current_key].append(line)
    if not any(sections.values()):
        return None
    return sections


def generate_with_local_llm(metrics: dict[str, Any], previous_review: dict[str, Any] | None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    model_id, model_source = pick_local_model()
    base_url = (os.getenv("LOCAL_LLM_BASE_URL") or "http://127.0.0.1:11434").strip().rstrip("/")
    info = {
        "provider": "local",
        "base_url": base_url,
        "model_id": model_id,
        "model_id_source": model_source,
        "called": False,
        "http_status": None,
        "error_snippet": None,
        "response_snippet": None,
    }
    if not model_id:
        info["error_snippet"] = "No local model configured or discoverable."
        return None, info
    prompt_payload = {
        "template_path": str(TEMPLATE_PATH),
        "metrics": metrics,
        "previous_review_summary": (previous_review or {}).get("sections") if previous_review else None,
        "instructions": {
            "output_format": [
                "OPERATIONAL_SUMMARY",
                "- line 1",
                "WATCHPOINTS_RETAINED",
                "- line 1",
                "CHANGES_SINCE_LAST_CYCLE",
                "- line 1",
                "OPERATOR_CONTEXT_NOTE",
                "- optional line",
            ],
            "tone": "calm, precise, post-sunrise memory artifact",
            "constraints": [
                "Prefer signal over completeness.",
                "Do not invent metrics.",
                "Do not claim live authority.",
                "Operational summary must remain concise and operator-readable.",
                "If there is no meaningful operator context note, include the OPERATOR_CONTEXT_NOTE header and no bullets under it.",
            ],
        },
    }
    prompt = (
        "You are generating Station Calyx's DAILY_24H_REVIEW_TEMPLATE_V1 artifact.\n"
        "Return plain text only using exactly these uppercase section headers in this order:\n"
        "OPERATIONAL_SUMMARY\nWATCHPOINTS_RETAINED\nCHANGES_SINCE_LAST_CYCLE\nOPERATOR_CONTEXT_NOTE\n"
        "Under each header, use short '- ' bullet lines only.\n"
        "No markdown fences. No prose before or after the four sections.\n\n"
        f"{json.dumps(prompt_payload, indent=2, ensure_ascii=False)}"
    )
    body = json.dumps(
        {
            "model": model_id,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 700, "temperature": 0.2},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        info["called"] = True
        with urllib.request.urlopen(request, timeout=90) as response:
            info["http_status"] = response.status
            payload = json.loads(response.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        info["http_status"] = exc.code
        info["error_snippet"] = exc.read().decode("utf-8", "replace")[:500]
        return None, info
    except Exception as exc:
        info["error_snippet"] = str(exc)[:500]
        return None, info
    raw_text = str(payload.get("response") or "").strip()
    parsed = parse_sectioned_response(raw_text)
    if parsed is None:
        info["error_snippet"] = raw_text[:500] or "LLM response was not parseable."
        info["response_snippet"] = raw_text[:500] or None
        return None, info
    return parsed, info


def build_fallback_sections(metrics: dict[str, Any], previous_review: dict[str, Any] | None) -> dict[str, list[str]]:
    return {
        "operational_summary": build_operational_summary(metrics),
        "watchpoints_retained": build_watchpoints(metrics),
        "changes_since_last_cycle": build_changes(metrics, previous_review),
        "operator_context_note": build_operator_context_note(),
    }


def normalize_sections(candidate: dict[str, Any] | None, fallback: dict[str, list[str]]) -> dict[str, list[str]]:
    sections = dict(fallback)
    if not isinstance(candidate, dict):
        return sections
    for key, limit in (
        ("operational_summary", 6),
        ("watchpoints_retained", 3),
        ("changes_since_last_cycle", 3),
        ("operator_context_note", 2),
    ):
        value = candidate.get(key)
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            if cleaned:
                sections[key] = cleaned[:limit]
            elif key == "operator_context_note":
                sections[key] = []
    return sections


def build_rendered_text(sections: dict[str, list[str]]) -> str:
    lines: list[str] = []
    labels = [
        ("SECTION I - Operational Summary", "operational_summary"),
        ("SECTION II - Watchpoints Retained", "watchpoints_retained"),
        ("SECTION III - Changes Since Last Cycle", "changes_since_last_cycle"),
        ("SECTION IV - Operator Context Note", "operator_context_note"),
    ]
    for title, key in labels:
        lines.append(title)
        values = sections.get(key) or []
        if values:
            lines.extend(f"- {value}" for value in values)
        else:
            lines.append("- none")
        lines.append("")
    return "\n".join(lines).strip()


def write_receipt(payload: dict[str, Any]) -> Path:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    ts = utc_now().strftime("%Y%m%d_%H%M%S")
    path = AUDIT_DIR / f"daily_24h_review__{ts}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Station Calyx daily 24h review via local LLM.")
    parser.add_argument("--window-hours", type=int, default=24)
    parser.add_argument("--automatic", action="store_true")
    parser.add_argument("--required-post-sunrise-minutes", type=int, default=240)
    args = parser.parse_args()

    end_utc = utc_now()
    start_utc = end_utc - timedelta(hours=args.window_hours)
    metrics = render_metrics_payload(start_utc, end_utc)
    previous_review = load_previous_review()
    llm_sections, llm_info = generate_with_local_llm(metrics, previous_review)
    fallback_sections = build_fallback_sections(metrics, previous_review)
    sections = normalize_sections(llm_sections, fallback_sections)
    rendered_text = build_rendered_text(sections)

    latest_sunrise_ts = parse_dt(metrics["lifecycle"]["latest_sunrise_ts_utc"])
    latest_sunrise_age_minutes = None
    if latest_sunrise_ts:
        latest_sunrise_age_minutes = round((end_utc - latest_sunrise_ts).total_seconds() / 60.0, 2)
    post_sunrise_ready = bool(
        latest_sunrise_ts
        and latest_sunrise_age_minutes is not None
        and latest_sunrise_age_minutes <= args.required_post_sunrise_minutes
    )

    payload = {
        "schema": "station.daily_24h_review.v1",
        "ts_utc": iso_z(end_utc),
        "template_id": "DAILY_24H_REVIEW_TEMPLATE_V1",
        "generation_mode": "automatic" if args.automatic else "manual",
        "generator": {
            "provider": "local_llm",
            "script": str(Path(__file__).relative_to(REPO_ROOT)),
            "template_path": str(TEMPLATE_PATH.relative_to(REPO_ROOT)),
            "llm": llm_info,
        },
        "window": metrics["window"],
        "post_sunrise_validation": {
            "ready": post_sunrise_ready,
            "latest_sunrise_ts_utc": metrics["lifecycle"]["latest_sunrise_ts_utc"],
            "latest_sunrise_age_minutes": latest_sunrise_age_minutes,
            "required_post_sunrise_minutes": args.required_post_sunrise_minutes,
            "latest_sunrise_path": metrics["lifecycle"]["latest_sunrise_path"],
        },
        "metrics": metrics,
        "sections": sections,
        "rendered_text": rendered_text,
        "prompt_template_sha256": sha256_text(read_text(TEMPLATE_PATH)),
        "rendered_text_sha256": sha256_text(rendered_text),
        "source_paths": metrics["source_paths"],
    }
    output_path = write_receipt(payload)
    print(str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
