#!/usr/bin/env python3
"""
Gated Claude Code CLI (Anthropic) - operator-invoked only.
Requirements:
 - Gate files: outgoing/gates/network.ok and outgoing/gates/llm.ok (unless --mock)
 - API key via environment variable: ANTHROPIC_API_KEY
 - Enable via config/config/claude.yaml `enabled: true` or use --enable

Usage:
  py -3 tools/claude_code_cli.py --prompt "Write a helper..." [--model claude-code-lite] [--mock]

This tool is intentionally opt-in and conservative; it will refuse network calls unless gates+config allow it.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import textwrap
import urllib.request
import urllib.error
from pathlib import Path
from tools.agent_api import check_gates, read_config_enabled, atomic_write_json

ROOT = Path(__file__).resolve().parents[1]
GATES_DIR = ROOT / 'outgoing' / 'gates'
NETWORK_GATE = GATES_DIR / 'network.ok'
LLM_GATE = GATES_DIR / 'llm.ok'
CONFIG_FILE = ROOT / 'config' / 'claude.yaml'

DEFAULT_MODEL = 'claude-code-lite'


def read_config_enabled() -> bool:
    try:
        if not CONFIG_FILE.exists():
            return False
        txt = CONFIG_FILE.read_text(encoding='utf-8')
        for line in txt.splitlines():
            s = line.strip().lower()
            if s.startswith('enabled:'):
                val = s.split(':', 1)[1].strip()
                return val in ('true', '1', 'yes', 'on')
    except Exception:
        pass
    return False


def check_gates() -> bool:
    return NETWORK_GATE.exists() and LLM_GATE.exists()


def call_anthropic(api_key: str, model: str, prompt: str, max_tokens: int, temperature: float):
    # Minimal HTTP call to Anthropic completion endpoint. Operator must ensure model name is valid.
    url = 'https://api.anthropic.com/v1/complete'
    data = {
        'model': model,
        'prompt': prompt,
        'max_tokens_to_sample': max_tokens,
        'temperature': temperature,
    }
    body = json.dumps(data).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key,
    }
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            err = e.read().decode('utf-8')
            return {'error': f'HTTPError {e.code}: {err}'}
        except Exception:
            return {'error': f'HTTPError {e.code}'}
    except Exception as e:
        return {'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description='Gated Claude Code CLI (operator must enable gates and config)')
    parser.add_argument('--prompt', '-p', type=str, required=True)
    parser.add_argument('--model', '-m', type=str, default=DEFAULT_MODEL)
    parser.add_argument('--max-tokens', type=int, default=256)
    parser.add_argument('--temperature', type=float, default=0.0)
    parser.add_argument('--mock', action='store_true')
    parser.add_argument('--enable', action='store_true')
    args = parser.parse_args()

    if not check_gates() and not args.mock:
        print('[claude-code-cli] ERROR: required gates missing. Create', NETWORK_GATE, 'and', LLM_GATE)
        sys.exit(2)
    enabled = read_config_enabled(CONFIG_FILE)
    if not enabled and not args.enable and not args.mock:
        print('[claude-code-cli] ERROR: Claude disabled in config. Edit', CONFIG_FILE, 'or run with --enable')
        sys.exit(3)

    if args.mock:
        print('[claude-code-cli] Running in mock mode. No network call will be made.')
        print('\n[Anthropic • mock] Prompt:')
        print(args.prompt)
        print('\n[Anthropic • mock] Response:')
        print('def mocked_example():\n    pass')
        return

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print('[claude-code-cli] ERROR: ANTHROPIC_API_KEY not set in environment')
        sys.exit(4)

    print(f'[claude-code-cli] Calling Anthropic model {args.model} (prompt len={len(args.prompt)})')
    resp = call_anthropic(api_key, args.model, args.prompt, args.max_tokens, args.temperature)
    if isinstance(resp, dict) and 'error' in resp:
        print('[claude-code-cli] Error:', resp['error'])
        sys.exit(5)

    try:
        # The Anthropic response format may vary; try common fields
        if isinstance(resp, dict) and 'completion' in resp:
            print('[claude-code-cli] Completion:')
            print(resp.get('completion'))
        else:
            print('[claude-code-cli] Raw response:')
            print(json.dumps(resp, indent=2))
    except Exception as e:
        print('[claude-code-cli] Failed to parse response:', e)
        print(resp)


if __name__ == '__main__':
    main()
