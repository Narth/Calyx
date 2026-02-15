#!/usr/bin/env python3
"""Collect artifacts from completed benchmark runs."""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from benchmarks.harness.metrics import load_receipts, compute_metrics

def compute_parse_success_rate(receipts: list[dict]) -> float:
    """Compute parse_success_rate from receipts."""
    if not receipts:
        return 0.0
    parse_ok_true = sum(1 for r in receipts if r.get("llm_parse_ok") is True)
    return round(parse_ok_true / len(receipts), 4)

def compute_duration_seconds(start_ts: str, end_ts: str) -> float:
    """Compute duration in seconds from ISO timestamps."""
    start = datetime.fromisoformat(start_ts.replace('Z', '+00:00'))
    end = datetime.fromisoformat(end_ts.replace('Z', '+00:00'))
    return (end - start).total_seconds()

def main():
    results_dir = Path("runtime/benchmarks/results/prompt_injection_v0_2")
    envelopes = list(results_dir.glob("*.run.json"))
    
    # Get latest envelope per model/seed
    runs = {}
    for env_path in envelopes:
        with open(env_path, 'r', encoding='utf-8') as f:
            env = json.load(f)
        key = f"{env['model_id']}|{env['seed']}"
        if key not in runs or env_path.stat().st_mtime > runs[key]['mtime']:
            runs[key] = {'path': env_path, 'mtime': env_path.stat().st_mtime}
    
    # Collect artifacts
    artifacts = []
    for key, run_info in sorted(runs.items()):
        env_path = run_info['path']
        with open(env_path, 'r', encoding='utf-8') as f:
            envelope = json.load(f)
        
        # Load receipts
        receipt_path = Path(envelope['receipt_path'])
        if not receipt_path.is_absolute():
            receipt_path = Path(".") / receipt_path
        receipts = load_receipts(str(receipt_path))
        metrics = compute_metrics(receipts)
        parse_success_rate = compute_parse_success_rate(receipts)
        duration_seconds = compute_duration_seconds(
            envelope['run_start_ts_utc'],
            envelope['run_end_ts_utc']
        )
        
        artifact = {
            'envelope_path': str(env_path),
            'schema_version': envelope['schema_version'],
            'run_id': envelope['run_id'],
            'run_instance_id': envelope['run_instance_id'],
            'suite': envelope['suite'],
            'suite_sha256': envelope['suite_sha256'],
            'model_id': envelope['model_id'],
            'backend': envelope['backend'],
            'seed': envelope['seed'],
            'lane': envelope['lane'],
            'variant': envelope['variant'],
            'llm_config_sha256': envelope['llm_config_sha256'],
            'timeout_per_case': envelope['timeout_per_case'],
            'total_cases_expected': envelope['total_cases_expected'],
            'total_cases_completed': envelope['total_cases_completed'],
            'run_start_ts_utc': envelope['run_start_ts_utc'],
            'run_end_ts_utc': envelope['run_end_ts_utc'],
            'exit_status': envelope['exit_status'],
            'determinism_hash': envelope['determinism_hash'],
            'receipt_path': envelope['receipt_path'],
            'receipt_sha256': envelope['receipt_sha256'],
            'duration_seconds': round(duration_seconds, 2),
            'containment_rate': metrics['containment_rate'],
            'attack_success_rate': metrics['attack_success_rate'],
            'unauthorized_tool_invocation_rate': metrics['unauthorized_tool_invocation_rate'],
            'parse_success_rate': parse_success_rate,
            'forbidden_tool_attempt_rate': metrics['forbidden_tool_attempt_rate'],
            'forbidden_tool_attempt_count': metrics['forbidden_tool_attempt_count'],
            'forbidden_tool_attempt_by_tool': metrics['forbidden_tool_attempt_by_tool'],
        }
        artifacts.append(artifact)
    
    # Output JSON
    output_path = Path("runtime/benchmarks/artifacts_collected.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(artifacts, f, indent=2, ensure_ascii=False)
    
    print(f"Collected {len(artifacts)} artifacts")
    print(f"Output: {output_path}")
    
    # Print summary table
    print("\n=== Summary ===")
    print(f"{'Model':<20} {'Seed':<10} {'Status':<10} {'Completed':<12} {'Parse':<8} {'Contain':<8} {'Forbid':<8}")
    print("-" * 90)
    for a in sorted(artifacts, key=lambda x: (x['model_id'], x['seed'])):
        print(f"{a['model_id']:<20} {a['seed']:<10} {a['exit_status']:<10} "
              f"{a['total_cases_completed']}/{a['total_cases_expected']:<8} "
              f"{a['parse_success_rate']:<8.4f} {a['containment_rate']:<8.4f} "
              f"{a['forbidden_tool_attempt_rate']:<8.4f}")

if __name__ == "__main__":
    main()
