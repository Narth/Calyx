#!/usr/bin/env python3
"""
Simple gated interactive chat CLI for Codex/Chat models.
Usage:
  py -3 tools/codex_chat.py [--model gpt-3.5-turbo] [--max-tokens 256] [--temperature 0.0] [--mock] [--enable]

Notes:
 - Requires gates: outgoing/gates/network.ok and outgoing/gates/llm.ok (unless --mock)
 - Requires config/codex.yaml enabled: true or use --enable
 - Set OPENAI_API_KEY in environment for real calls
 - Type '/exit' to quit
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
CONFIG_FILE = ROOT / 'config' / 'codex.yaml'

DEFAULT_MODEL = 'gpt-3.5-turbo'


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


def call_api(api_key: str, model: str, messages: list, max_tokens: int, temperature: float):
    # Chat completions for gpt-* models
    if model.startswith('gpt-'):
        url = 'https://api.openai.com/v1/chat/completions'
        data = {
            'model': model,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'n': 1,
        }
    else:
        # fallback to legacy completions with last user message
        url = f'https://api.openai.com/v1/engines/{model}/completions'
        data = {
            'prompt': messages[-1].get('content', ''),
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
        with urllib.request.urlopen(req, timeout=60) as resp:
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', '-m', default=DEFAULT_MODEL)
    parser.add_argument('--max-tokens', type=int, default=256)
    parser.add_argument('--temperature', type=float, default=0.0)
    parser.add_argument('--mock', action='store_true')
    parser.add_argument('--enable', action='store_true')
    args = parser.parse_args()

    if not check_gates() and not args.mock:
        print('[codex-chat] ERROR: gates missing: create', NETWORK_GATE, 'and', LLM_GATE)
        sys.exit(2)
    enabled = read_config_enabled(CONFIG_FILE)
    if not enabled and not args.enable and not args.mock:
        print('[codex-chat] ERROR: codex disabled in config. Edit', CONFIG_FILE, 'or run with --enable')
        sys.exit(3)

    if args.mock:
        print('[codex-chat] Running in mock mode. Type /exit to quit.')
        while True:
            try:
                u = input('You: ')
            except EOFError:
                break
            if not u:
                continue
            if u.strip() == '/exit':
                break
            print('\n[CBO • mock] Response:')
            print('This is a mocked reply to: ', u)
            print()
        return

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print('[codex-chat] ERROR: OPENAI_API_KEY not set in environment')
        sys.exit(4)

    print('[codex-chat] Interactive session started. Type /exit to quit.')
    messages = []
    # optional system identity message
    messages.append({'role':'system','content':'You are CBO, the Calyx Bridge Overseer. Respond concisely.'})
    while True:
        try:
            user = input('You: ')
        except EOFError:
            break
        if not user:
            continue
        if user.strip() == '/exit':
            break
        messages.append({'role':'user','content': user})
        print('[codex-chat] Thinking...')
        resp = call_api(api_key, args.model, messages, args.max_tokens, args.temperature)
        if isinstance(resp, dict) and 'error' in resp:
            print('[codex-chat] Error:', resp['error'])
            # do not append error to history
            continue
        # extract text
        try:
            if args.model.startswith('gpt-'):
                choice = resp.get('choices', [])[0]
                content = choice.get('message', {}).get('content') if choice else None
            else:
                choice = resp.get('choices', [])[0]
                content = choice.get('text') if choice else None
            if not content:
                print('[codex-chat] No content in response; raw:')
                print(json.dumps(resp, indent=2))
                continue
            print('\n[CBO] ' + content.strip() + '\n')
            messages.append({'role':'assistant','content':content})
            # small sleep to avoid rate bursts
            time.sleep(0.1)
        except Exception as e:
            print('[codex-chat] Failed to parse response:', e)
            print(resp)


if __name__ == '__main__':
    main()
