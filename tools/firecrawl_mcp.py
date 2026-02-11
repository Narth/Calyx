#!/usr/bin/env python3
"""
Gated Firecrawl MCP wrapper for Station Calyx.

Usage:
  py -3 tools/firecrawl_mcp.py --tool scrape --args '{"url":"https://example.com"}' [--mock] [--enable]

Notes:
 - Requires gates: outgoing/gates/network.ok and outgoing/gates/llm.ok and outgoing/gates/firecrawl.ok (unless --mock)
 - Config: config/firecrawl.yaml (enabled: true) or use --enable
 - API key via env: FIRECRAWL_API_KEY
 - Custom endpoint via env: FIRECRAWL_API_URL
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
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.agent_api import check_gates, read_config_enabled, atomic_write_json

GATES_DIR = ROOT / 'outgoing' / 'gates'
FIRECRAWL_GATE = GATES_DIR / 'firecrawl.ok'
CONFIG_FILE = ROOT / 'config' / 'firecrawl.yaml'
OUT_DIR = ROOT / 'outgoing' / 'firecrawl'

DEFAULT_API_URL = 'https://api.firecrawl.dev/v1'


def call_firecrawl(api_key: str, api_url: str, tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    # Map tool name to endpoint
    endpoint = f"{api_url.rstrip('/')}/{tool}"
    body = json.dumps(arguments).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    req = urllib.request.Request(endpoint, data=body, headers=headers, method='POST')
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
    parser = argparse.ArgumentParser(description='Gated Firecrawl MCP wrapper')
    parser.add_argument('--tool', '-t', required=True, help='firecrawl tool name, e.g. scrape, map, search, crawl, extract, batch_scrape')
    parser.add_argument('--args', '-a', nargs=argparse.REMAINDER, default=[], help='JSON string of arguments for the tool')
    parser.add_argument('--mock', action='store_true', help='Run in mock mode (no network)')
    parser.add_argument('--enable', action='store_true', help='Temporarily enable Firecrawl without editing config')
    parser.add_argument('--save', action='store_true', help='Save response to outgoing/firecrawl/<tool>_<ts>.json')
    args = parser.parse_args()

    # Allow --mock/--enable to appear after --args (argparse.REMAINDER)
    if '--mock' in args.args:
        args.args = [a for a in args.args if a != '--mock']
        args.mock = True
    if '--enable' in args.args:
        args.args = [a for a in args.args if a != '--enable']
        args.enable = True

    # Gate checks
    required_gates = ('network.ok', 'llm.ok', 'firecrawl.ok')
    if not check_gates(required_gates) and not args.mock:
        print('[firecrawl] ERROR: required gates missing. Create outgoing/gates/network.ok, outgoing/gates/llm.ok and outgoing/gates/firecrawl.ok')
        sys.exit(2)

    enabled = read_config_enabled(CONFIG_FILE)
    if not enabled and not args.enable and not args.mock:
        print('[firecrawl] ERROR: Firecrawl disabled in config. Edit', str(CONFIG_FILE), 'or run with --enable')
        sys.exit(3)

    try:
        raw_args = ' '.join(args.args).strip() if isinstance(args.args, list) else str(args.args)
        raw_args = raw_args or '{}'
        tool_args = json.loads(raw_args)
    except Exception:
        print('[firecrawl] ERROR: failed to parse --args as JSON')
        sys.exit(4)

    if args.mock:
        print('[firecrawl] Running in mock mode. No network call will be made.')
        mock_resp = {'content': [{'type': 'text', 'text': f'Mocked response for tool {args.tool}'}], 'isError': False}
        print(json.dumps(mock_resp, indent=2))
        return

    api_key = os.environ.get('FIRECRAWL_API_KEY')
    api_url = os.environ.get('FIRECRAWL_API_URL', DEFAULT_API_URL)
    if not api_key:
        print('[firecrawl] ERROR: FIRECRAWL_API_KEY not set in environment')
        sys.exit(5)

    print(f'[firecrawl] Calling Firecrawl tool {args.tool} at {api_url} (prompt args len={len(args.args)})')
    resp = call_firecrawl(api_key, api_url, args.tool, tool_args)
    if isinstance(resp, dict) and resp.get('error'):
        print('[firecrawl] Error:', resp.get('error'))
        sys.exit(6)

    print(json.dumps(resp, indent=2))

    if args.save:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = __import__('time').time()
        outpath = OUT_DIR / f"{args.tool}_{int(ts)}.json"
        try:
            atomic_write_json(outpath, resp)
            print('[firecrawl] Saved response to', str(outpath))
        except Exception:
            print('[firecrawl] Failed to save response')


if __name__ == '__main__':
    main()
