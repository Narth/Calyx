[[[[]]]]#!/usr/bin/env python3
import argparse, json, subprocess, sys, yaml
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / 'config.yaml'
GATE_PATH = ROOT / 'outgoing' / 'gates' / 'bitnet.ok'
HEARTBEAT_PATH = ROOT / 'outgoing' / 'agent_bitnet.lock'

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f).get('bitnet', {})

def check_gate():
    if not GATE_PATH.exists():
        return False, 'Gate not found'
    try:
        with open(GATE_PATH, 'r') as f:
            if not json.load(f).get('enabled', False):
                return False, 'Gate disabled'
        return True, 'Gate OK'
    except Exception as e:
        return False, f'Error: {e}'

def emit_heartbeat(status="running", message=""):
    """Emit SVF heartbeat to agent_bitnet.lock"""
    heartbeat = {
        "agent": "agent_bitnet",
        "status": status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": message,
        "ts": datetime.utcnow().timestamp()
    }
    HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HEARTBEAT_PATH, "w") as f:
        json.dump(heartbeat, f, indent=2)

def run_inference(prompt, cfg):
    dist = cfg.get('wsl_distribution', 'Ubuntu')
    model = cfg.get('model_path')
    binary = cfg.get('binary_path')
    
    # Emit starting heartbeat
    emit_heartbeat(status="inference", message=f"Prompt: {prompt[:50]}...")
    
    cmd = ['wsl', '--distribution', dist, 'bash', '-c',
           f'cd ~/bitnet_build/BitNet && {binary} -m {model} -p "{prompt}" -n 50 -t 4 2>&1']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            emit_heartbeat(status="complete", message="Inference successful")
            return True, result.stdout
        else:
            emit_heartbeat(status="error", message=f"RC: {result.returncode}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        emit_heartbeat(status="timeout", message="120s exceeded")
        return False, "Timeout"
    except Exception as e:
        emit_heartbeat(status="error", message=str(e))
        return False, f"Error: {e}"

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--prompt', required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    print('[Agent_BitNet]: Initializing...')
    cfg = load_config()
    gate_ok, msg = check_gate()
    if not gate_ok:
        print(f'[Agent_BitNet]: ERROR - {msg}')
        sys.exit(1)
    print(f'[Agent_BitNet]: {msg}')
    
    if args.dry_run:
        print('[Agent_BitNet]: Config validated')
        emit_heartbeat(status="ready", message="Dry-run validation complete")
        sys.exit(0)
    
    print('[Agent_BitNet]: Running inference...')
    emit_heartbeat(status="starting", message="Beginning inference")
    success, output = run_inference(args.prompt, cfg)
    print('[Agent_BitNet - Output]:' if success else '[Agent_BitNet]: ERROR')
    print(output)
    sys.exit(0 if success else 1)
