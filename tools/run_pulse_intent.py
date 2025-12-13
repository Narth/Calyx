#!/usr/bin/env python3
"""Helper to add a schema_validation intent and run one coordinator pulse, printing results."""
from pathlib import Path
from calyx.cbo.coordinator import Coordinator
import json

ROOT = Path(__file__).resolve().parents[1]

def main():
    co = Coordinator(ROOT)
    intent_id = co.add_intent(
        description='Run schema validation across logs (auto-test)',
        origin='CBO',
        required_capabilities=['schema_validation'],
        desired_outcome='Validate recent logs',
        priority_hint=40,
        autonomy_required='execute'
    )
    print('added_intent:', intent_id)
    report = co.pulse()
    print('\n--- PULSE REPORT ---')
    print(json.dumps({k:v for k,v in report.items() if k not in ('top_intents',)}, indent=2, ensure_ascii=False))

    dlg = ROOT / 'outgoing' / 'bridge' / 'dialog.log'
    print('\n--- dialog.log tail ---')
    if dlg.exists():
        lines = dlg.read_text(encoding='utf-8').strip().splitlines()
        print('\n'.join(lines[-40:]))
    else:
        print('dialog.log missing')

    err = ROOT / 'outgoing' / 'autonomy_errors.log'
    print('\n--- autonomy_errors.log ---')
    if err.exists():
        print(err.read_text(encoding='utf-8'))
    else:
        print('no errors logged')

if __name__ == '__main__':
    main()
