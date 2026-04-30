"""WO_OPENCLAW_REINTRO_GUARDRAILS_V1: OpenClaw quarantine intake guard."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .experimental_artifacts import experimental_dir, experimental_mode_enabled, write_experimental_json
from .paths import resolve_repo_root, resolve_runtime_dir


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ts_tag(dt: datetime | None = None) -> str:
    return (dt or _utc_now()).strftime("%Y%m%d_%H%M%S")


def _to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


@dataclass
class EvalContext:
    ts_tag: str
    requests_in_last_minute_by_lane: dict[str, list[datetime]] = field(default_factory=dict)
    actions_per_boot_by_lane: dict[str, int] = field(default_factory=dict)
    actions_per_boot_total: int = 0


class OpenClawIntakeGuard:
    def __init__(self, repo_root: Path | None = None):
        self.repo_root = (repo_root or resolve_repo_root()).resolve()
        self.runtime_dir = resolve_runtime_dir(self.repo_root)
        self.cem_mode = experimental_mode_enabled()
        self.audit_dir = experimental_dir(self.runtime_dir, "openclaw") if self.cem_mode else (self.runtime_dir / "receipts" / "audit")
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.policy = self._load_policy()
        self._compiled_deny = [re.compile(pat, re.IGNORECASE) for pat in self.policy.get("hard_deny_patterns", [])]
        self.context = EvalContext(ts_tag=_ts_tag())
        self.denied_actions_path = self.audit_dir / f"openclaw_denied_actions__{self.context.ts_tag}.jsonl"
        self._evaluations: list[dict[str, Any]] = []

    def _load_policy(self) -> dict[str, Any]:
        policy_path = self.repo_root / "policy" / "openclaw_intake_policy.json"
        return json.loads(policy_path.read_text(encoding="utf-8"))

    def _classify_command(self, command: str) -> tuple[str, str]:
        cmd = (command or "").strip()
        if not cmd:
            return "denied", "empty_command"
        for pat in self._compiled_deny:
            if pat.search(cmd):
                return "denied", f"matched_hard_deny_pattern:{pat.pattern}"
        verb = cmd.split()[0]
        if verb not in set(self.policy.get("command_allowlist", [])):
            return "denied", "command_not_allowlisted"
        return "allowlisted", "allowlist_match"

    def _rate_and_budget(self, lane: str, now: datetime) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        rpm_limits = ((self.policy.get("rate_limits") or {}).get("requests_per_minute_by_lane") or {})
        lane_limit = int(rpm_limits.get(lane, 0))
        window = self.context.requests_in_last_minute_by_lane.setdefault(lane, [])
        one_min_ago = now - timedelta(minutes=1)
        window[:] = [t for t in window if t >= one_min_ago]
        if lane_limit <= 0 or len(window) >= lane_limit:
            reasons.append("rate_limit_exceeded")

        budgets = self.policy.get("budgets") or {}
        max_total = int(budgets.get("max_actions_per_boot_total", 0))
        lane_budgets = budgets.get("max_actions_per_boot_by_lane") or {}
        lane_budget = int(lane_budgets.get(lane, 0))
        lane_used = int(self.context.actions_per_boot_by_lane.get(lane, 0))
        if max_total <= 0 or self.context.actions_per_boot_total >= max_total:
            reasons.append("budget_total_exceeded")
        if lane_budget <= 0 or lane_used >= lane_budget:
            reasons.append("budget_lane_exceeded")
        return len(reasons) == 0, reasons

    def _append_denied_log(self, rec: dict[str, Any]) -> None:
        with self.denied_actions_path.open("a", encoding="utf-8") as f:
            if self.cem_mode:
                rec = dict(rec)
                rec["surface_label"] = "experimental"
                rec["execution_surface"] = "experimental"
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def evaluate_request(self, request: dict[str, Any]) -> dict[str, Any]:
        now = _utc_now()
        corr_id = request.get("corr_id") or ""
        task_corr_id = request.get("task_corr_id") or ""
        sender_identity = request.get("sender_identity") or ""
        sender_authenticated = bool(request.get("sender_authenticated", False))
        lane = str(request.get("lane", "")).upper()
        command = str(request.get("command", "")).strip()
        requested_mode = str(request.get("requested_mode", "execute")).lower()

        decision = "deny"
        decision_reason = "default_deny"
        lane_info = (self.policy.get("lanes") or {}).get(lane) or {}
        lane_allowed = bool(lane_info.get("allow", False))
        classification = str(self.policy.get("classification", "unknown"))
        dry_run_only = bool(self.policy.get("dry_run_only", True))
        allow_execute_reachable = False

        auth_status = "authenticated" if (sender_identity and sender_authenticated) else "missing_or_unverified"
        command_classification, command_reason = self._classify_command(command)

        # Sender identity must be explicit and authenticated.
        if not sender_identity or not sender_authenticated:
            decision = "deny"
            decision_reason = "missing_authenticated_sender_identity"
        elif lane not in ("A", "B", "C", "D"):
            decision = "deny"
            decision_reason = "invalid_lane"
        elif not lane_allowed:
            decision = "deny"
            decision_reason = "lane_denied_by_policy"
        elif command_classification != "allowlisted":
            decision = "deny"
            decision_reason = command_reason
        else:
            within_budget, budget_reasons = self._rate_and_budget(lane, now)
            if not within_budget:
                decision = "deny"
                decision_reason = ",".join(budget_reasons)
            else:
                if dry_run_only or requested_mode == "execute":
                    decision = "allow_dry_run"
                    decision_reason = "dry_run_only_enforced"
                else:
                    # Keep unreachable under default policy.
                    decision = "allow_dry_run"
                    decision_reason = "dry_run_default"
                self.context.requests_in_last_minute_by_lane.setdefault(lane, []).append(now)
                self.context.actions_per_boot_by_lane[lane] = int(self.context.actions_per_boot_by_lane.get(lane, 0)) + 1
                self.context.actions_per_boot_total += 1

        rec = {
            "schema": "audit.openclaw.intake_eval.v1",
            "ts_utc": _to_iso(now),
            "corr_id": corr_id,
            "task_corr_id": task_corr_id,
            "sender_identity": sender_identity,
            "sender_auth_status": auth_status,
            "classification": classification,
            "dry_run_only": dry_run_only,
            "lane": lane,
            "lane_policy_name": lane_info.get("name", ""),
            "lane_allowed": lane_allowed,
            "command": command,
            "command_classification": command_classification,
            "command_classification_reason": command_reason,
            "rate_limit_status": "active",
            "budget_status": "active",
            "budget_usage": {
                "actions_per_boot_total": self.context.actions_per_boot_total,
                "actions_per_boot_by_lane": dict(self.context.actions_per_boot_by_lane),
            },
            "decision": decision,
            "decision_reason": decision_reason,
            "allow_execute_reachable": allow_execute_reachable,
            "transport_rule_no_fallback_broadcast": bool(
                ((self.policy.get("transport_rules") or {}).get("no_fallback_broadcast", True))
            ),
        }
        self._evaluations.append(rec)
        if decision == "deny":
            self._append_denied_log(rec)
        return rec

    def write_receipts(self) -> dict[str, str]:
        ts = self.context.ts_tag
        intake_path = self.audit_dir / f"openclaw_intake_receipt__{ts}.json"
        policy_eval_path = self.audit_dir / f"openclaw_policy_eval__{ts}.json"
        denied_path = self.denied_actions_path

        intake_payload = {
            "schema": "audit.openclaw_intake_receipt.v1",
            "ts_utc": _to_iso(_utc_now()),
            "corr_id": f"openclaw-{uuid.uuid4()}",
            "task_corr_id": "",
            "classification": self.policy.get("classification", ""),
            "dry_run_only": bool(self.policy.get("dry_run_only", True)),
            "evaluated_count": len(self._evaluations),
            "decisions": {
                "deny": sum(1 for r in self._evaluations if r["decision"] == "deny"),
                "allow_dry_run": sum(1 for r in self._evaluations if r["decision"] == "allow_dry_run"),
                "allow_execute": sum(1 for r in self._evaluations if r["decision"] == "allow_execute"),
            },
            "requests": self._evaluations,
            "denied_actions_log_path": str(denied_path),
        }
        if self.cem_mode:
            write_experimental_json(intake_path, intake_payload)
        else:
            intake_path.write_text(json.dumps(intake_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        policy_hash = hashlib.sha256(
            json.dumps(self.policy, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        policy_payload = {
            "schema": "audit.openclaw_policy_eval.v1",
            "ts_utc": _to_iso(_utc_now()),
            "corr_id": intake_payload["corr_id"],
            "task_corr_id": "",
            "policy_sha256": policy_hash,
            "classification": self.policy.get("classification", ""),
            "dry_run_only": bool(self.policy.get("dry_run_only", True)),
            "lanes": self.policy.get("lanes", {}),
            "command_allowlist": self.policy.get("command_allowlist", []),
            "hard_deny_patterns": self.policy.get("hard_deny_patterns", []),
            "rate_limits": self.policy.get("rate_limits", {}),
            "budgets": self.policy.get("budgets", {}),
            "transport_rules": self.policy.get("transport_rules", {}),
            "no_fallback_broadcast": bool(
                (self.policy.get("transport_rules") or {}).get("no_fallback_broadcast", True)
            ),
            "final_decision_defaults": {
                "allow_execute_reachable": False,
                "default_decision": "deny_or_allow_dry_run",
            },
            "receipt_ref": str(intake_path),
        }
        if self.cem_mode:
            write_experimental_json(policy_eval_path, policy_payload)
        else:
            policy_eval_path.write_text(json.dumps(policy_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "openclaw_intake_receipt": str(intake_path),
            "openclaw_policy_eval": str(policy_eval_path),
            "openclaw_denied_actions": str(denied_path),
        }


def _simulated_requests() -> list[dict[str, Any]]:
    return [
        {
            "corr_id": "ocw-sim-001",
            "task_corr_id": "",
            "sender_identity": "",
            "sender_authenticated": False,
            "lane": "A",
            "command": "fs_list docs",
            "requested_mode": "execute",
        },
        {
            "corr_id": "ocw-sim-002",
            "task_corr_id": "",
            "sender_identity": "openclaw-node-1",
            "sender_authenticated": True,
            "lane": "C",
            "command": "fs_read README.md",
            "requested_mode": "execute",
        },
        {
            "corr_id": "ocw-sim-003",
            "task_corr_id": "",
            "sender_identity": "openclaw-node-1",
            "sender_authenticated": True,
            "lane": "A",
            "command": "git push origin main",
            "requested_mode": "execute",
        },
        {
            "corr_id": "ocw-sim-004",
            "task_corr_id": "",
            "sender_identity": "openclaw-node-1",
            "sender_authenticated": True,
            "lane": "A",
            "command": "fs_read AGENTS.md",
            "requested_mode": "execute",
        },
        {
            "corr_id": "ocw-sim-005",
            "task_corr_id": "",
            "sender_identity": "openclaw-node-1",
            "sender_authenticated": True,
            "lane": "B",
            "command": "patch_preview README.md",
            "requested_mode": "execute",
        },
    ]


def _main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw intake guard evaluator")
    parser.add_argument("--simulate", action="store_true", help="Run local simulation and write receipts")
    parser.add_argument("--request-json", default="", help="Single request JSON file to evaluate")
    args = parser.parse_args()

    guard = OpenClawIntakeGuard()
    if args.simulate:
        for req in _simulated_requests():
            guard.evaluate_request(req)
        # Rate-limit proof: exceed lane A RPM in a tight burst.
        for i in range(25):
            guard.evaluate_request(
                {
                    "corr_id": f"ocw-sim-ratelimit-{i+1:02d}",
                    "task_corr_id": "",
                    "sender_identity": "openclaw-node-1",
                    "sender_authenticated": True,
                    "lane": "A",
                    "command": "fs_read STATE.md",
                    "requested_mode": "execute",
                }
            )
        # Budget proof: seed usage to max then evaluate one more request.
        budgets = guard.policy.get("budgets") or {}
        guard.context.actions_per_boot_total = int(budgets.get("max_actions_per_boot_total", 0))
        lane_budgets = budgets.get("max_actions_per_boot_by_lane") or {}
        guard.context.actions_per_boot_by_lane["B"] = int(lane_budgets.get("B", 0))
        guard.evaluate_request(
            {
                "corr_id": "ocw-sim-budget-001",
                "task_corr_id": "",
                "sender_identity": "openclaw-node-1",
                "sender_authenticated": True,
                "lane": "B",
                "command": "patch_preview README.md",
                "requested_mode": "execute",
            }
        )
        out = guard.write_receipts()
        print(json.dumps({"mode": "simulate", "receipts": out}, ensure_ascii=False))
        return 0

    if args.request_json:
        req = json.loads(Path(args.request_json).read_text(encoding="utf-8"))
        result = guard.evaluate_request(req)
        out = guard.write_receipts()
        print(json.dumps({"result": result, "receipts": out}, ensure_ascii=False))
        return 0 if result["decision"] != "deny" else 2

    print(json.dumps({"error": "provide --simulate or --request-json"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(_main())
