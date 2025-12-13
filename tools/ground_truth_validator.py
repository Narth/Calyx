#!/usr/bin/env python3
"""
Ground Truth Validator - Fact-check and verify agent actions
Ensures ML models learn from factual, accurate data
"""
from __future__ import annotations
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent


class GroundTruthValidator:
    """Validate against ground truth sources"""
    
    def __init__(self):
        self.facts_cache = ROOT / "logs" / "ground_truth_cache.json"
        self.validation_log = ROOT / "logs" / "ground_truth_validation.jsonl"
        
    def validate_task_result(self, task_result: Dict) -> Dict:
        """Validate a task result against ground truth"""
        validation = {
            "task_id": task_result.get("task_id", "unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "verified": False,
            "checks": {}
        }
        
        # Check 1: Task actually completed
        exit_code = task_result.get("exit_code", -1)
        validation["checks"]["exit_code_valid"] = exit_code == 0
        
        # Check 2: Files changed exist
        files_changed = task_result.get("files_changed", [])
        validation["checks"]["files_exist"] = self._check_files_exist(files_changed)
        
        # Check 3: TES score is reasonable
        tes = task_result.get("tes", 0)
        validation["checks"]["tes_reasonable"] = 0 <= tes <= 100
        
        # Check 4: Duration is realistic
        duration = task_result.get("duration", 0)
        validation["checks"]["duration_realistic"] = 0 < duration < 600
        
        # Check 5: No errors in logs
        has_errors = task_result.get("has_errors", False)
        validation["checks"]["no_errors"] = not has_errors
        
        # Overall verification
        validation["verified"] = all(validation["checks"].values())
        
        # Log validation
        with self.validation_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(validation) + "\n")
        
        return validation
    
    def _check_files_exist(self, files: List[str]) -> bool:
        """Verify files actually exist"""
        if not files:
            return True
        
        for file_path in files[:5]:  # Check first 5 files
            if not (ROOT / file_path).exists():
                return False
        
        return True
    
    def verify_prediction(self, prediction: Dict, actual: Dict) -> Dict:
        """Verify prediction accuracy"""
        pred_tes = prediction.get("forecast", 0)
        actual_tes = actual.get("tes", 0)
        
        error = abs(pred_tes - actual_tes)
        within_tolerance = error <= 5.0  # ±5 TES tolerance
        
        return {
            "prediction": pred_tes,
            "actual": actual_tes,
            "error": error,
            "within_tolerance": within_tolerance,
            "verified": within_tolerance,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class HumanValidator:
    """Human-in-the-loop validation for critical decisions"""
    
    def __init__(self):
        self.pending_validations = ROOT / "logs" / "pending_validations.jsonl"
        self.approved_actions = ROOT / "logs" / "approved_actions.jsonl"
        
    def flag_for_review(self, action: Dict, reason: str):
        """Flag an action for human review"""
        flag = {
            "action": action,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "pending"
        }
        
        with self.pending_validations.open("a", encoding="utf-8") as f:
            f.write(json.dumps(flag) + "\n")
        
        return flag
    
    def get_pending_reviews(self) -> List[Dict]:
        """Get pending validations for human review"""
        pending = []
        
        if self.pending_validations.exists():
            with self.pending_validations.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        flag = json.loads(line)
                        if flag.get("status") == "pending":
                            pending.append(flag)
                    except:
                        continue
        
        return pending


class QualityGate:
    """Enforce quality gates before deploying models"""
    
    def __init__(self):
        self.min_accuracy = 0.75
        self.min_data_quality = 0.80
        self.max_error_rate = 0.10
        
    def check_model_quality(self, model_results: Dict) -> bool:
        """Check if model meets quality gates"""
        checks = {
            "accuracy": model_results.get("accuracy", 0) >= self.min_accuracy,
            "data_quality": model_results.get("data_quality", 0) >= self.min_data_quality,
            "error_rate": model_results.get("error_rate", 1) <= self.max_error_rate
        }
        
        return all(checks.values())


def main():
    """Run ground truth validation"""
    print("=" * 70)
    print("GROUND TRUTH VALIDATION")
    print("=" * 70)
    
    validator = GroundTruthValidator()
    
    # Example validation
    sample_result = {
        "task_id": "test-001",
        "exit_code": 0,
        "files_changed": ["tools/test.py"],
        "tes": 85.0,
        "duration": 120.0,
        "has_errors": False
    }
    
    validation = validator.validate_task_result(sample_result)
    
    print("\nValidation Results:")
    print(f"  Verified: {validation['verified']}")
    print(f"  Checks:")
    for check, result in validation["checks"].items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"    {status} {check}: {result}")
    
    print("\n[INFO] Ground truth validation operational")


if __name__ == "__main__":
    main()

