#!/usr/bin/env python3
"""
OpenClaw skill wrappers for Station Calyx (gated, opt-in).

Usage:
  py -3 tools/skills_cli.py list
  py -3 tools/skills_cli.py run <skill> --args "--help" [--mock] [--enable]

This CLI wraps high-priority OpenClaw skills with Calyx governance checks:
- gates: outgoing/gates/network.ok, outgoing/gates/llm.ok
- apply gate for mutating skills: outgoing/gates/apply.ok
- station sleep mode restrictions via governance/state/station_mode.json
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.agent_api import check_gates, read_config_enabled
CONFIG = ROOT / 'config' / 'skills.yaml'
APPLY_GATE = ROOT / 'outgoing' / 'gates' / 'apply.ok'
STATION_MODE = ROOT / 'governance' / 'state' / 'station_mode.json'


def _read_config() -> Dict[str, Any]:
    try:
        txt = CONFIG.read_text(encoding='utf-8')
        # very light YAML-ish parser: handle simple key/indent blocks
        cfg: Dict[str, Any] = {'skills': {}, 'station_mode_allowlist': []}
        section = None
        current_skill = None
        for raw in txt.splitlines():
            if not raw.strip() or raw.lstrip().startswith('#'):
                continue
            indent = len(raw) - len(raw.lstrip(' '))
            s = raw.strip()
            if indent == 0:
                if s.startswith('enabled:'):
                    cfg['enabled'] = s.split(':', 1)[1].strip().lower() in ('true', '1', 'yes', 'on')
                    section = None
                    current_skill = None
                elif s.startswith('station_mode_allowlist:'):
                    section = 'allowlist'
                    current_skill = None
                elif s.startswith('skills:'):
                    section = 'skills'
                    current_skill = None
                else:
                    section = None
                    current_skill = None
                continue
            if section == 'allowlist' and indent == 2 and s.startswith('- '):
                cfg['station_mode_allowlist'].append(s[2:].strip())
                continue
            if section == 'skills' and indent == 2 and s.endswith(':'):
                current_skill = s[:-1].strip()
                cfg['skills'][current_skill] = {}
                continue
            if section == 'skills' and current_skill and indent >= 4 and ':' in s:
                k, v = s.split(':', 1)
                cfg['skills'][current_skill][k.strip()] = v.strip()
        return cfg
    except Exception:
        return {'enabled': False, 'skills': {}, 'station_mode_allowlist': []}


def _station_mode() -> str:
    try:
        if STATION_MODE.exists():
            return json.loads(STATION_MODE.read_text(encoding='utf-8')).get('mode','ACTIVE')
    except Exception:
        pass
    return 'ACTIVE'


def _ensure_allowed(skill: str, cfg: Dict[str, Any], enable: bool, mock: bool) -> None:
    if not (cfg.get('enabled') or enable or mock):
        raise SystemExit('[skills] ERROR: skills disabled in config/skills.yaml (set enabled: true or use --enable)')
    # Sleep mode allowlist
    if _station_mode() == 'SLEEP':
        if skill not in cfg.get('station_mode_allowlist', []):
            raise SystemExit(f"[skills] ERROR: station in SLEEP mode; '{skill}' not allowed")


def _run_command(cmd: str, args: str) -> int:
    exe = shutil.which(cmd)
    if not exe:
        raise SystemExit(f"[skills] ERROR: command '{cmd}' not found in PATH")
    argv = [exe] + (args.split() if args else [])
    return subprocess.call(argv)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    sub.add_parser('list')
    run = sub.add_parser('run')
    run.add_argument('skill')
    run.add_argument('--args', nargs=argparse.REMAINDER, default=[])
    run.add_argument('--mock', action='store_true')
    run.add_argument('--enable', action='store_true')
    args = parser.parse_args()

    # Allow --mock/--enable to appear after --args (argparse.REMAINDER)
    if hasattr(args, 'args'):
        if '--mock' in args.args:
            args.args = [a for a in args.args if a != '--mock']
            args.mock = True
        if '--enable' in args.args:
            args.args = [a for a in args.args if a != '--enable']
            args.enable = True

    cfg = _read_config()

    if args.cmd == 'list':
        print(json.dumps(cfg.get('skills', {}), indent=2))
        return

    if args.cmd == 'run':
        skill = args.skill
        skills = cfg.get('skills', {})
        if skill not in skills:
            raise SystemExit(f"[skills] ERROR: unknown skill '{skill}'")

        _ensure_allowed(skill, cfg, args.enable, args.mock)

        meta = skills[skill]
        requires_network = str(meta.get('requires_network','false')).lower() == 'true'
        requires_apply = str(meta.get('requires_apply','false')).lower() == 'true'

        # gate checks
        if requires_network and not args.mock:
            if not check_gates():
                raise SystemExit('[skills] ERROR: network/llm gates not present')
        if requires_apply and not APPLY_GATE.exists() and not args.mock:
            raise SystemExit('[skills] ERROR: apply.ok gate required for mutating skill')

        if args.mock:
            print(f"[skills] Mock run for {skill} with args: {' '.join(args.args)}")
            return

        cmd = meta.get('command')
        if not cmd:
            raise SystemExit(f"[skills] ERROR: no command configured for {skill}")
        code = _run_command(cmd, args.args)
        raise SystemExit(code)

    parser.print_help()


if __name__ == '__main__':
    main()
