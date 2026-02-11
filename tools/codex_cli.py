#!/usr/bin/env python3
"""
Opt-in Codex CLI (gated).
Requirements:
 - A gate file at `outgoing/gates/network.ok` and `outgoing/gates/llm.ok` must exist to allow network/LLM usage.
 - Operator must set `OPENAI_API_KEY` environment variable.
 - Operator must enable Codex via `config/codex.yaml` (set `enabled: true`) or pass `--enable`.

Usage:
  py -3 tools/codex_cli.py --prompt "Write a helper function to ..." [--model gpt-3.5-turbo] [--mock]

This tool is intentionally opt-in and conservative: it will refuse to run unless gates/config allow it.
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
CONFIG_FILE = ROOT / 'config' / 'codex.yaml'

DEFAULT_MODEL = 'gpt-3.5-turbo'


def read_config_enabled() -> bool:
    # lightweight parser: look for `enabled: true` (case-insensitive)
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


def call_openai_completions(api_key: str, model: str, prompt: str, max_tokens: int, temperature: float):
    # Use Chat Completions API for gpt-* models, fall back to legacy completions for others
    if model.startswith('gpt-'):
        url = 'https://api.openai.com/v1/chat/completions'
        data = {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': temperature,
            'n': 1,
        }
    else:
        url = f'https://api.openai.com/v1/engines/{model}/completions'
        data = {
            'prompt': prompt,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'n': 1,
            'stop': None,
        }
    body = json.dumps(data).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode('utf-8')
            return json.loads(resp_body)
    except urllib.error.HTTPError as e:
        try:
            err = e.read().decode('utf-8')
            return {'error': f'HTTPError {e.code}: {err}'}
        except Exception:
            return {'error': f'HTTPError {e.code}'}
    except Exception as e:
        return {'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description='Gated Codex CLI (operator must enable gates and config)')
    parser.add_argument('--prompt', '-p', type=str, required=True)
    parser.add_argument('--model', '-m', type=str, default=DEFAULT_MODEL)
    parser.add_argument('--max-tokens', type=int, default=256)
    parser.add_argument('--temperature', type=float, default=0.0)
    parser.add_argument('--mock', action='store_true', help='Run in mock mode (no network)')
    parser.add_argument('--enable', action='store_true', help='Temporarily enable Codex without editing config')
    args = parser.parse_args()

    # Check gates and config using shared helpers
    if not check_gates() and not args.mock:
        print('[codex-cli] ERROR: required gates not present. Create both:', str(NETWORK_GATE), 'and', str(LLM_GATE))
        sys.exit(2)
    enabled = read_config_enabled(CONFIG_FILE)
    if not enabled and not args.enable and not args.mock:
        print('[codex-cli] ERROR: Codex disabled in config. Edit', str(CONFIG_FILE), 'and set `enabled: true` or run with --enable')
        sys.exit(3)

    if args.mock:
        print('[codex-cli] Running in mock mode. No network call will be made.')
        sample = textwrap.dedent('''
        [mocked-codex] — Completion (mock)
        Prompt: {}

        Response:
        def example():
            '''.format(args.prompt))
        print(sample)
        return

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print('[codex-cli] ERROR: OPENAI_API_KEY not set in environment')
        sys.exit(4)

    print(f'[codex-cli] Calling OpenAI Codex model {args.model} (prompt len={len(args.prompt)})')
    resp = call_openai_completions(api_key, args.model, args.prompt, args.max_tokens, args.temperature)
    if isinstance(resp, dict) and 'error' in resp:
        print('[codex-cli] Error:', resp['error'])
        sys.exit(5)

    # Extract the chosen text
    try:
        choices = resp.get('choices')
        if not choices:
            print('[codex-cli] No choices in response. Raw response:')
            print(json.dumps(resp, indent=2))
            return
        text = choices[0].get('text') or choices[0].get('message', {}).get('content')
        print('[codex-cli] Completion:')
        print(text)
    except Exception as e:
        print('[codex-cli] Failed to parse response:', e)
        print(json.dumps(resp))


if __name__ == '__main__':
    main()
