#!/usr/bin/env python3
"""
Gated interactive chat for Anthropic Claude models.
Usage:
  py -3 tools/claude_chat.py [--model claude-code-lite] [--mock] [--enable]

Type '/exit' to quit.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from tools.agent_api import check_gates, read_config_enabled

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
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', '-m', default=DEFAULT_MODEL)
    parser.add_argument('--max-tokens', type=int, default=256)
    parser.add_argument('--temperature', type=float, default=0.0)
    parser.add_argument('--mock', action='store_true')
    parser.add_argument('--enable', action='store_true')
    args = parser.parse_args()

    if not check_gates() and not args.mock:
        print('[claude-chat] ERROR: gates missing: create', NETWORK_GATE, 'and', LLM_GATE)
        sys.exit(2)
    enabled = read_config_enabled()
    if not enabled and not args.enable and not args.mock:
        print('[claude-chat] ERROR: claude disabled in config. Edit', CONFIG_FILE, 'or run with --enable')
        sys.exit(3)

    if args.mock:
        print('[claude-chat] Running in mock mode. Type /exit to quit.')
        while True:
            try:
                u = input('You: ')
            except EOFError:
                break
            if not u:
                continue
            if u.strip() == '/exit':
                break
            print('\n[Claude • mock] Response:')
            print('This is a mocked reply to: ', u)
            print()
        return

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print('[claude-chat] ERROR: ANTHROPIC_API_KEY not set in environment')
        sys.exit(4)

    print('[claude-chat] Interactive session started. Type /exit to quit.')
    system = "You are CBO, the Calyx Bridge Overseer. Respond concisely."
    while True:
        try:
            user = input('You: ')
        except EOFError:
            break
        if not user:
            continue
        if user.strip() == '/exit':
            break
        prompt = system + '\n\nHuman: ' + user + '\n\nAssistant:'
        print('[claude-chat] Thinking...')
        resp = call_anthropic(api_key, args.model, prompt, args.max_tokens, args.temperature)
        if isinstance(resp, dict) and 'error' in resp:
            print('[claude-chat] Error:', resp['error'])
            continue
        try:
            if isinstance(resp, dict) and 'completion' in resp:
                print('\n[Claude] ' + resp.get('completion').strip() + '\n')
            else:
                print('\n[Claude] Raw response:')
                print(json.dumps(resp, indent=2))
        except Exception as e:
            print('[claude-chat] Failed to parse response:', e)
            print(resp)


if __name__ == '__main__':
    main()
