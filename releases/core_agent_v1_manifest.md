# Core Agent v1 Manifest
Generated: 2025-10-29 21:36:37 -07:00

## Maintenance Block
- Duration: 4 hours (scheduled) for core + agent consolidation prior to public beta.

## Module Checksums
| Module | SHA256 |
| --- | --- |
| tools/agent_runner.py | E5F0FE407E549B5CFD66C54BB08D85521F1C14DE36D7F0EFF8D2C5B7319E2E90 |
| tools/autonomy_monitor.py | 60FB976FF064D813F36877E7CE280C54B7C7C42B1A31FEA71867F49C8D4BDC7E |
| tools/agent_watcher.py | C9B708BA61E36F98410EB9A77EF3A7033298CD7B4EE3A1AA7010A8139DBB29BC |
| tools/agent_metrics.py | 8FFCB7C065735480419E43749BDAED0547111969FBFCB780690587C03F88CBC8 |
| tools/agent_scheduler.py | B745EAB666EB551C6DCE595CF624EAF14D630671BC4550A0577DE2AC4D0C1B5A |

## Inter-Agent Message Schema (Current)
- `outgoing/bridge/dispatch/*.json`: {"targets": [agent_id], "action": "start|stop", "domain": "win|wsl", "args": "..."}
- `outgoing/heartbeat/*.lock`: JSON payload with {"name", "phase", "status", "status_message", ...}
- `outgoing/watchdog/*.log`: array of candidate objects with {"pid", "action", "name", "username"}

## TES Baseline
- Average TES (last 20 runs): 97.03

## Notes
- Manifest anchors module state prior to beta release. Any changes require checksum refresh and updated manifest version.
- TES schema version: 3 with optional compliance/coherence fields backfilled across historical metrics.
