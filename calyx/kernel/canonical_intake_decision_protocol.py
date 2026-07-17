"""WO_CANONICAL_INTAKE_DECISION_PROTOCOL_V1 evaluator."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .experimental_artifacts import experimental_dir, experimental_mode_enabled, write_experimental_json
from .paths import resolve_receipts_dir, resolve_repo_root
from .transport_comparator import evaluate_transport_cycles


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _load_json_files(directory: Path, pattern: str) -> list[dict[str, Any]]:
    items: list[tuple[datetime, dict[str, Any], Path]] = []
    for p in sorted(directory.glob(pattern)):
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")
            rec = json.loads(raw.lstrip("\ufeff"))
        except Exception:
            continue
        ts = _parse_ts(rec.get("ts_utc")) or datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        rec["_path"] = str(p)
        items.append((ts, rec, p))
    items.sort(key=lambda x: x[0], reverse=True)
    return [rec for _, rec, _ in items]


@dataclass
class CycleCheck:
    cycle_ref: str
    boot_evidence_gate_pass: bool
    boot_context_budget_pass: bool
    no_channel_boundary_anomalies: bool
    no_unauthorized_send_attempts: bool
    unexpected_new_remote: bool
    unexpected_new_emitter_authority: bool
    new_listener_unexpected: bool
    channel_widening: bool
    qualifies: bool
    evidence_paths: dict[str, str]


def evaluate_protocol(required_consecutive_boots: int = 3) -> dict[str, Any]:
    repo_root = resolve_repo_root()
    receipts_dir = resolve_receipts_dir(repo_root)
    audit_dir = receipts_dir / "audit"

    sunrise = _load_json_files(receipts_dir, "sunrise_receipt__*.json")
    boot_audits = _load_json_files(audit_dir, "boot_evidence_bundle__*.json")
    noise = _load_json_files(audit_dir, "telemetry_noise_signal_summary__*.json")
    transport_cycles = evaluate_transport_cycles(repo_root, required_count=20)

    cycles: list[CycleCheck] = []
    n = min(len(sunrise), len(boot_audits), len(noise), 20)
    for i in range(n):
        s = sunrise[i]
        b = boot_audits[i]
        z = noise[i]
        t = transport_cycles[i] if i < len(transport_cycles) else None
        boot_evidence_gate_pass = bool(b.get("synchronous_boot_evidence_bundle_before_network", False))
        boot_context_budget_pass = bool(s.get("boot_context_budget_pass", b.get("budget_pass", False)))
        no_channel_boundary_anomalies = (
            int(z.get("emitter_detections", 0)) == 0
            and int(z.get("implicit_channel_expansion_attempts", 0)) == 0
        )
        no_unauthorized_send_attempts = int(z.get("governance_assertion_failures", 0)) == 0
        unexpected_new_remote = bool(t.unexpected_new_remote) if t else bool(z.get("unexpected_new_remote", False))
        unexpected_new_emitter_authority = (
            bool(t.unexpected_new_emitter_authority)
            if t
            else bool(z.get("unexpected_new_emitter_authority", False))
        )
        new_listener_unexpected = bool(t.new_listener_unexpected) if t else bool(z.get("new_listener_unexpected", False))
        channel_widening = bool(t.channel_widening) if t else bool(z.get("channel_widening", False))
        qualifies = (
            boot_evidence_gate_pass
            and boot_context_budget_pass
            and no_channel_boundary_anomalies
            and no_unauthorized_send_attempts
            and not unexpected_new_remote
            and not unexpected_new_emitter_authority
            and not new_listener_unexpected
            and not channel_widening
        )
        cycles.append(
            CycleCheck(
                cycle_ref=f"cycle_{i+1}",
                boot_evidence_gate_pass=boot_evidence_gate_pass,
                boot_context_budget_pass=boot_context_budget_pass,
                no_channel_boundary_anomalies=no_channel_boundary_anomalies,
                no_unauthorized_send_attempts=no_unauthorized_send_attempts,
                unexpected_new_remote=unexpected_new_remote,
                unexpected_new_emitter_authority=unexpected_new_emitter_authority,
                new_listener_unexpected=new_listener_unexpected,
                channel_widening=channel_widening,
                qualifies=qualifies,
                evidence_paths={
                    "sunrise_receipt": s.get("_path", ""),
                    "boot_evidence_bundle": b.get("_path", ""),
                    "noise_signal_summary": z.get("_path", ""),
                },
            )
        )

    consecutive = 0
    for c in cycles:
        if c.qualifies:
            consecutive += 1
        else:
            break

    promotion_eligible = consecutive >= required_consecutive_boots
    dual_confirmation_required = ["CBO", "CGPT"]
    dual_confirmation_present = False
    promote_avatar_cli = promotion_eligible and dual_confirmation_present

    out = {
        "schema": "audit.canonical_intake_decision_protocol.v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "required_consecutive_boots": required_consecutive_boots,
        "consecutive_qualifying_boots": consecutive,
        "promotion_eligible_by_objective_criteria": promotion_eligible,
        "dual_confirmation_required": dual_confirmation_required,
        "dual_confirmation_present": dual_confirmation_present,
        "canonical_intake_default": "cursor_vscode",
        "avatar_cli_promotion": "not_promoted",
        "avatar_cli_promotion_allowed_now": promote_avatar_cli,
        "discord_role": "optional_transport_only",
        "criteria": {
            "boot_evidence_gate_pass": "required",
            "boot_context_budget_pass": "required",
            "no_channel_boundary_anomalies": "required",
            "no_unauthorized_send_attempts": "required",
            "unexpected_new_remote": "must_be_false",
            "unexpected_new_emitter_authority": "must_be_false",
            "new_listener_unexpected": "must_be_false",
            "channel_widening": "must_be_false",
        },
        "cycles": [c.__dict__ for c in cycles],
    }

    cem_mode = experimental_mode_enabled()
    audit_dir = experimental_dir(receipts_dir.parent, "openclaw") if cem_mode else audit_dir
    audit_dir.mkdir(parents=True, exist_ok=True)
    ts_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = audit_dir / f"canonical_intake_decision_receipt__{ts_tag}.json"
    out["receipt_path"] = str(path)
    if cem_mode:
        write_experimental_json(path, out)
    else:
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _main() -> int:
    parser = argparse.ArgumentParser(description="Canonical intake decision protocol evaluator")
    parser.add_argument("--required-consecutive-boots", type=int, default=3)
    args = parser.parse_args()
    out = evaluate_protocol(required_consecutive_boots=args.required_consecutive_boots)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
