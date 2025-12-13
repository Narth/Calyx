#!/usr/bin/env python3
"""
Training Validation System - Ensure model accuracy and prevent bad habits
Validates training data, models, and predictions against ground truth
"""
from __future__ import annotations
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent


class TrainingValidator:
    """Validate training data and model quality"""
    
    def __init__(self):
        self.synthetic_file = ROOT / "logs" / "synthetic_training_data.jsonl"
        self.real_file = ROOT / "logs" / "agent_metrics.csv"
        self.validation_results = ROOT / "logs" / "validation_results.jsonl"
        
    def validate_synthetic_data(self) -> Dict:
        """Validate synthetic data against real data patterns"""
        try:
            import csv
            
            # Load real data patterns
            real_patterns = self._extract_real_patterns()
            
            # Load synthetic data
            synthetic_samples = []
            with self.synthetic_file.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        synthetic_samples.append(json.loads(line))
                    except:
                        continue
            
            # Validate each synthetic sample
            validation_results = {
                "total_samples": len(synthetic_samples),
                "valid_samples": 0,
                "invalid_samples": 0,
                "validations": []
            }
            
            for sample in synthetic_samples:
                is_valid = self._validate_sample(sample, real_patterns)
                validation_results["validations"].append({
                    "sample": sample,
                    "valid": is_valid,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                if is_valid:
                    validation_results["valid_samples"] += 1
                else:
                    validation_results["invalid_samples"] += 1
            
            # Calculate validation score
            if validation_results["total_samples"] > 0:
                validation_results["validation_score"] = (
                    validation_results["valid_samples"] / validation_results["total_samples"]
                )
            else:
                validation_results["validation_score"] = 0.0
            
            # Save results
            with self.validation_results.open("a", encoding="utf-8") as f:
                f.write(json.dumps(validation_results) + "\n")
            
            return validation_results
            
        except Exception as e:
            return {"error": str(e), "validation_score": 0.0}
    
    def _extract_real_patterns(self) -> Dict:
        """Extract patterns from real data for validation"""
        patterns = {
            "tes_range": (0, 100),
            "duration_range": (0, 600),
            "memory_range": (0, 100),
            "valid_agents": ["agent1", "agent2", "agent3", "agent4"],
            "valid_task_types": ["docs", "refactoring", "optimization", "debugging"],
            "valid_phases": ["planning", "execution", "verification"]
        }
        
        try:
            import csv
            if self.real_file.exists():
                with self.real_file.open("r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    
                    if rows:
                        tes_values = [float(r.get("tes", 0) or 0) for r in rows]
                        if tes_values:
                            patterns["tes_range"] = (min(tes_values), max(tes_values))
                        
                        durations = [float(r.get("duration_s", 0) or 0) for r in rows]
                        if durations:
                            patterns["duration_range"] = (min(durations), max(durations))
        except:
            pass
        
        return patterns
    
    def _validate_sample(self, sample: Dict, patterns: Dict) -> bool:
        """Validate a single synthetic sample"""
        checks = []
        
        # Check TES is in valid range
        tes = sample.get("tes", 0)
        tes_min, tes_max = patterns["tes_range"]
        checks.append(tes_min <= tes <= tes_max)
        
        # Check duration is realistic
        duration = sample.get("duration", 0)
        dur_min, dur_max = patterns["duration_range"]
        checks.append(dur_min <= duration <= dur_max)
        
        # Check memory is in valid range
        memory = sample.get("memory_usage", 0)
        mem_min, mem_max = patterns["memory_range"]
        checks.append(mem_min <= memory <= mem_max)
        
        # Check agent_id is valid
        agent_id = sample.get("agent_id", "")
        checks.append(agent_id in patterns["valid_agents"])
        
        # Check task_type is valid
        task_type = sample.get("task_type", "")
        checks.append(task_type in patterns["valid_task_types"])
        
        # Check phase is valid
        phase = sample.get("phase", "")
        checks.append(phase in patterns["valid_phases"])
        
        # Check success is boolean
        success = sample.get("success", False)
        checks.append(isinstance(success, bool))
        
        # Require all checks to pass
        return all(checks)


class ModelValidator:
    """Validate model predictions against ground truth"""
    
    def __init__(self):
        self.predictions_file = ROOT / "logs" / "predictive_forecasts.jsonl"
        self.validation_results = ROOT / "logs" / "model_validation.jsonl"
        
    def validate_predictions(self) -> Dict:
        """Compare predictions to actual outcomes"""
        try:
            # Load predictions
            predictions = []
            with self.predictions_file.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        predictions.append(json.loads(line))
                    except:
                        continue
            
            # Load actual outcomes (from recent metrics)
            actuals = self._load_actual_outcomes()
            
            # Validate each prediction
            validation = {
                "total_predictions": len(predictions),
                "accurate_predictions": 0,
                "mean_error": 0.0,
                "max_error": 0.0,
                "accuracy_score": 0.0
            }
            
            errors = []
            for pred in predictions[-10:]:  # Check last 10 predictions
                pred_tes = pred.get("tes_forecast", {}).get("forecast", 0)
                
                # Find matching actual
                actual_tes = actuals.get("tes", 0)
                
                # Calculate error
                error = abs(pred_tes - actual_tes)
                errors.append(error)
                
                # Check if within acceptable range (±5%)
                if error <= 5.0:
                    validation["accurate_predictions"] += 1
            
            if errors:
                validation["mean_error"] = statistics.mean(errors)
                validation["max_error"] = max(errors)
            
            if validation["total_predictions"] > 0:
                validation["accuracy_score"] = (
                    validation["accurate_predictions"] / validation["total_predictions"]
                )
            
            # Save validation
            with self.validation_results.open("a", encoding="utf-8") as f:
                f.write(json.dumps(validation) + "\n")
            
            return validation
            
        except Exception as e:
            return {"error": str(e), "accuracy_score": 0.0}
    
    def _load_actual_outcomes(self) -> Dict:
        """Load actual system outcomes"""
        try:
            import csv
            metrics_file = ROOT / "logs" / "agent_metrics.csv"
            if metrics_file.exists():
                with metrics_file.open("r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    if rows:
                        latest = rows[-1]
                        return {
                            "tes": float(latest.get("tes", 0) or 0),
                            "timestamp": latest.get("timestamp", "")
                        }
        except:
            pass
        
        return {"tes": 0}


class CrossValidator:
    """Cross-validate models against multiple data sources"""
    
    def __init__(self):
        self.validation_threshold = 0.75  # 75% minimum accuracy
        
    def cross_validate(self) -> Dict:
        """Cross-validate against multiple validation methods"""
        results = {
            "data_validation": None,
            "prediction_validation": None,
            "overall_score": 0.0,
            "pass": False
        }
        
        # Validate training data
        data_validator = TrainingValidator()
        results["data_validation"] = data_validator.validate_synthetic_data()
        
        # Validate predictions
        model_validator = ModelValidator()
        results["prediction_validation"] = model_validator.validate_predictions()
        
        # Calculate overall score
        data_score = results["data_validation"].get("validation_score", 0.0)
        pred_score = results["prediction_validation"].get("accuracy_score", 0.0)
        
        results["overall_score"] = (data_score + pred_score) / 2
        results["pass"] = results["overall_score"] >= self.validation_threshold
        
        return results


def main():
    """Run validation checks"""
    print("=" * 70)
    print("TRAINING VALIDATION SYSTEM")
    print("=" * 70)
    
    # Run cross-validation
    validator = CrossValidator()
    results = validator.cross_validate()
    
    print("\nValidation Results:")
    print(f"  Overall Score: {results['overall_score']*100:.1f}%")
    print(f"  Pass Threshold: {results['pass']}")
    
    if results["data_validation"]:
        dv = results["data_validation"]
        print(f"\nData Validation:")
        print(f"  Total Samples: {dv.get('total_samples', 0)}")
        print(f"  Valid Samples: {dv.get('valid_samples', 0)}")
        print(f"  Validation Score: {dv.get('validation_score', 0)*100:.1f}%")
    
    if results["prediction_validation"]:
        pv = results["prediction_validation"]
        print(f"\nPrediction Validation:")
        print(f"  Total Predictions: {pv.get('total_predictions', 0)}")
        print(f"  Accurate Predictions: {pv.get('accurate_predictions', 0)}")
        print(f"  Mean Error: {pv.get('mean_error', 0):.2f}")
        print(f"  Accuracy Score: {pv.get('accuracy_score', 0)*100:.1f}%")
    
    if results["pass"]:
        print("\n[SUCCESS] Validation passed - training data quality verified")
    else:
        print("\n[WARNING] Validation below threshold - review training data")
    
    print("\n[INFO] Validation complete")


if __name__ == "__main__":
    main()

