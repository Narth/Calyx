"""
Desktop Hub Runner
Watches telemetry/outbox/intents/ for envelopes, validates against contract,
resolves task_type to deterministic task plan, executes via approved harness mechanisms.

Default deny if:
- unknown task_type
- missing scope
- risk tier high without approval token
- envelope fails schema validation
- touches policy/governance paths without explicit approval
"""
from __future__ import annotations

import json
import hashlib
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
import uuid


class ContractValidator:
    """Validates envelopes against CALYX_CONTRACT.yaml."""
    
    def __init__(self, contract_path: str | Path):
        self.contract_path = Path(contract_path)
        self.contract = self._load_contract()
        self.contract_hash = self._compute_contract_hash()
    
    def _load_contract(self) -> dict:
        """Load CALYX_CONTRACT.yaml."""
        if not self.contract_path.exists():
            raise FileNotFoundError(f"Contract not found: {self.contract_path}")
        
        with open(self.contract_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def _compute_contract_hash(self) -> str:
        """Compute SHA256 of contract file."""
        content = self.contract_path.read_bytes()
        return hashlib.sha256(content).hexdigest()
    
    def validate_task_type(self, task_type: str) -> tuple[bool, Optional[str]]:
        """Check if task_type is in allowed_tasks."""
        allowed = self.contract.get("allowed_tasks", [])
        if task_type not in allowed:
            return False, f"task_type '{task_type}' not in allowed_tasks"
        return True, None
    
    def validate_source(self, source: str, phase: str = "phase_a") -> tuple[bool, Optional[str]]:
        """Check if source is in allowed_sources for current phase."""
        allowed_sources = self.contract.get("allowed_sources", {}).get(phase, [])
        if source not in allowed_sources:
            return False, f"source '{source}' not in allowed_sources for {phase}"
        return True, None
    
    def check_stop_conditions(
        self,
        envelope: dict,
        diff_paths: List[str]
    ) -> tuple[bool, Optional[str]]:
        """Check if any stop conditions are triggered."""
        stop_conditions = self.contract.get("stop_conditions", [])
        
        # Check for policy/governance touches
        governance_paths = ["governance/", "CALYX_CONTRACT.yaml", ".github/workflows/"]
        if any(path.startswith(tuple(governance_paths)) for path in diff_paths):
            if not envelope.get("requires_human_approval") or not envelope.get("approval_token"):
                return True, "policy_governance_edit_without_approval"
        
        # Check for high risk without approval
        risk_hint = envelope.get("risk_hint", "low")
        if risk_hint == "high":
            if not envelope.get("requires_human_approval") or not envelope.get("approval_token"):
                return True, "high_risk_without_approval_token"
        
        return False, None
    
    def get_tool_allowlist(self, task_type: str) -> List[str]:
        """Get allowed tools for task_type."""
        tool_surface = self.contract.get("tool_surface", {})
        task_tools = tool_surface.get(task_type, {}).get("allowed_tools", [])
        return task_tools
    
    def determine_risk_tier(self, envelope: dict, diff_paths: List[str]) -> str:
        """Determine risk tier based on envelope and diff paths."""
        risk_rules = self.contract.get("risk_rules", {})
        
        # Check high risk triggers
        high_triggers = risk_rules.get("high", {}).get("triggers", [])
        for trigger in high_triggers:
            if trigger == "policy_files_changed":
                if any("governance" in p or "CALYX_CONTRACT.yaml" in p for p in diff_paths):
                    return "high"
            elif trigger == "requires_approval_token":
                if envelope.get("requires_human_approval"):
                    return "high"
        
        # Check med risk triggers
        med_triggers = risk_rules.get("med", {}).get("triggers", [])
        for trigger in med_triggers:
            if trigger == "dependency_files_changed":
                dep_files = ["requirements.txt", "pyproject.toml", "package.json", "go.mod"]
                if any(f in str(p) for p in diff_paths for f in dep_files):
                    return "med"
            elif trigger == "task_types":
                if envelope.get("task_type") in ["lint_fix", "test_run", "code_review"]:
                    return "med"
        
        return "low"


class HubRunner:
    """Desktop hub runner - watches outbox and executes envelopes."""
    
    def __init__(self, repo_root: str | Path, contract_path: str | Path = "CALYX_CONTRACT.yaml"):
        self.repo_root = Path(repo_root)
        self.contract_path = self.repo_root / contract_path
        self.contract_validator = ContractValidator(self.contract_path)
        
        self.outbox_path = self.repo_root / "telemetry" / "outbox" / "intents"
        self.results_path = self.repo_root / "runtime" / "benchmarks" / "results"
        self.receipts_path = self.repo_root / "runtime" / "receipts"
        self.manifests_path = self.repo_root / "runtime" / "manifests"
        
        # Ensure directories exist
        self.results_path.mkdir(parents=True, exist_ok=True)
        self.receipts_path.mkdir(parents=True, exist_ok=True)
        self.manifests_path.mkdir(parents=True, exist_ok=True)
        
        self.processed_envelopes = set()
    
    def _load_envelope(self, envelope_path: Path) -> Optional[dict]:
        """Load envelope from JSON file."""
        try:
            with open(envelope_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return None
    
    def _validate_envelope_schema(self, envelope: dict) -> tuple[bool, Optional[str]]:
        """Basic envelope schema validation."""
        required_fields = [
            "envelope_id", "ts_utc", "source", "author", "task_type",
            "scope", "constraints", "requires_human_approval"
        ]
        
        for field in required_fields:
            if field not in envelope:
                return False, f"missing_field: {field}"
        
        # Validate scope has paths
        scope = envelope.get("scope", {})
        if not isinstance(scope, dict) or "paths" not in scope:
            return False, "scope missing paths"
        
        return True, None
    
    def _resolve_task_plan(self, envelope: dict) -> Optional[dict]:
        """Resolve task_type to deterministic task plan."""
        task_type = envelope.get("task_type")
        scope = envelope.get("scope", {})
        constraints = envelope.get("constraints", {})
        
        plan = {
            "task_type": task_type,
            "scope": scope,
            "constraints": constraints,
            "tools": self.contract_validator.get_tool_allowlist(task_type),
            "risk_tier": self.contract_validator.determine_risk_tier(
                envelope, scope.get("paths", [])
            )
        }
        
        return plan
    
    def _execute_task(self, envelope: dict, plan: dict) -> dict:
        """Execute task via approved harness mechanisms."""
        task_type = plan["task_type"]
        run_id = f"{task_type}_{envelope['envelope_id'][:8]}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        # For now, stub execution - actual implementation would call harness
        result = {
            "run_id": run_id,
            "task_type": task_type,
            "status": "executed",
            "outputs": [],
            "errors": []
        }
        
        # Write result to results directory
        result_path = self.results_path / task_type / f"{run_id}.jsonl"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(result_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
        
        return result
    
    def _write_receipt(self, envelope: dict, plan: dict, result: dict, error: Optional[str] = None):
        """Write hub runner receipt."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        receipt = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "envelope_id": envelope.get("envelope_id"),
            "task_type": envelope.get("task_type"),
            "risk_tier": plan.get("risk_tier"),
            "contract_sha256": self.contract_validator.contract_hash,
            "run_id": result.get("run_id"),
            "status": "allowed" if not error else "denied",
            "error": error
        }
        
        receipt_path = self.receipts_path / f"hub_runner__{ts}.jsonl"
        with open(receipt_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(receipt, ensure_ascii=False) + "\n")
    
    def _write_manifest(self, run_id: str, artifacts: List[dict]):
        """Write run manifest with hash list of artifacts."""
        manifest = {
            "run_id": run_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "artifacts": artifacts
        }
        
        manifest_path = self.manifests_path / f"{run_id}_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    def process_envelope(self, envelope_path: Path) -> tuple[bool, Optional[str]]:
        """Process a single envelope."""
        envelope_id = envelope_path.stem
        
        # Skip if already processed
        if envelope_id in self.processed_envelopes:
            return False, "already_processed"
        
        # Load envelope
        envelope = self._load_envelope(envelope_path)
        if not envelope:
            return False, "failed_to_load_envelope"
        
        envelope_id_from_file = envelope.get("envelope_id")
        
        # Validate schema
        is_valid, schema_error = self._validate_envelope_schema(envelope)
        if not is_valid:
            self._write_receipt(envelope, {}, {}, schema_error)
            return False, schema_error
        
        # Validate task_type
        task_type = envelope.get("task_type")
        is_allowed, task_error = self.contract_validator.validate_task_type(task_type)
        if not is_allowed:
            self._write_receipt(envelope, {}, {}, task_error)
            return False, task_error
        
        # Validate source
        source = envelope.get("source", "discord")
        is_allowed, source_error = self.contract_validator.validate_source(source)
        if not is_allowed:
            self._write_receipt(envelope, {}, {}, source_error)
            return False, source_error
        
        # Check stop conditions
        scope_paths = envelope.get("scope", {}).get("paths", [])
        should_stop, stop_reason = self.contract_validator.check_stop_conditions(
            envelope, scope_paths
        )
        if should_stop:
            self._write_receipt(envelope, {}, {}, stop_reason)
            return False, stop_reason
        
        # Resolve task plan
        plan = self._resolve_task_plan(envelope)
        if not plan:
            error = "failed_to_resolve_task_plan"
            self._write_receipt(envelope, {}, {}, error)
            return False, error
        
        # Execute task
        try:
            result = self._execute_task(envelope, plan)
            
            # Write manifest
            artifacts = [
                {"path": str(self.results_path / plan["task_type"] / f"{result['run_id']}.jsonl"), "type": "result"}
            ]
            self._write_manifest(result["run_id"], artifacts)
            
            # Write receipt
            self._write_receipt(envelope, plan, result)
            
            self.processed_envelopes.add(envelope_id_from_file)
            return True, None
            
        except Exception as e:
            error = f"execution_error: {str(e)}"
            self._write_receipt(envelope, plan, {}, error)
            return False, error
    
    def run_once(self):
        """Process all pending envelopes in outbox."""
        if not self.outbox_path.exists():
            return
        
        envelopes = list(self.outbox_path.glob("*.json"))
        processed_count = 0
        denied_count = 0
        
        for envelope_path in envelopes:
            success, error = self.process_envelope(envelope_path)
            if success:
                processed_count += 1
            else:
                denied_count += 1
        
        return {
            "processed": processed_count,
            "denied": denied_count,
            "total": len(envelopes)
        }


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Desktop Hub Runner")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--contract", default="CALYX_CONTRACT.yaml")
    parser.add_argument("--watch", action="store_true", help="Watch mode (not implemented)")
    args = parser.parse_args()
    
    runner = HubRunner(args.repo_root, args.contract)
    stats = runner.run_once()
    
    print(f"Processed: {stats['processed']}, Denied: {stats['denied']}, Total: {stats['total']}")


if __name__ == "__main__":
    main()
