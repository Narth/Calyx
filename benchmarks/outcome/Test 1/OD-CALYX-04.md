## Night Cycle Doctrine (3 phases)

**Phase 1: Shutdown Prep (allowed)**
- Summarize session state (telemetry + node outputs).
- Log open risks/drift signals.
- Verify Safe Mode and deny-all are active.
- Forbidden: capability elevation, unsanctioned writes, schedulers.

**Phase 2: Quiescence (allowed)**
- Minimal telemetry heartbeat; kernel check-in if invoked manually.
- Archive pointers (paths, hashes) for resumed work.
- Forbidden: new tasks, network, background loops, scaling actions.

**Phase 3: Wake Planning (allowed)**
- Draft next-session intent, TODOs, and checkpoints.
- Validate configs against governance schemas (RES, D/F/X/P/A, R-series).
- Forbidden: executing plans; only logging/reflection.

All phases: Safe Mode true; Execution Gate deny-all; append-only logs; no hidden channels.
