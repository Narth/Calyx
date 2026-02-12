# CBO Runtime State Relocation — 2026-02-11

## Goal

Ensure CBO runtime JSONL files are no longer created under `calyx/cbo/`. All such state now lives under a single runtime root: `{CALYX_RUNTIME_DIR}/cbo/` (default `runtime/cbo/`), which is git-ignored.

## Files Changed

### New

| File | Purpose |
|------|---------|
| `calyx/cbo/runtime_paths.py` | Single source of truth for CBO runtime paths; `get_cbo_runtime_dir(root)`, `get_objectives_path()`, `get_task_queue_path()`, etc.; `runtime_state_resolves_outside_code_tree()` self-check. |
| `tests/test_cbo_runtime_paths.py` | Smoke tests: runtime state outside code tree, CBO dir under runtime root, paths not under `calyx/cbo/`. |

### Modified (code)

| File | Change |
|------|--------|
| `calyx/cbo/task_store.py` | Use `get_task_queue_path(root)`, `get_task_status_path(root)` instead of `root / "calyx" / "cbo" / "..."`. |
| `calyx/cbo/api.py` | Use `get_objectives_path(ROOT)`, `get_objectives_history_path(ROOT)`; ensure runtime dir exists at load. |
| `calyx/cbo/bridge_overseer.py` | Use `get_objectives_path(root)`; objectives_history derived with `with_name()`. |
| `calyx/cbo/maintenance.py` | Use `get_cbo_runtime_dir`, `get_task_queue_path`, `get_task_status_path`, `get_objectives_path`, `get_objectives_history_path`, `get_memory_db_path`. |
| `calyx/cbo/coordinator/domains.py` | Use `get_memory_db_path(root)` for `MemoryEmbeddingsDomain`. |
| `tools/acknowledge_sysint_suggestion.py` | Use `get_sysint_acknowledged_path(ROOT)`. |
| `tools/sys_integrator.py` | Use `get_sysint_acknowledged_path(ROOT)` for ack file. |
| `tools/system_dashboard.py` | Use `get_task_queue_path(ROOT)`. |
| `tools/system_dashboard_embedded.py` | Use `get_task_queue_path(ROOT)`. |
| `tools/station_calyx_cli.py` | Use `get_task_queue_path(ROOT)`. |
| `tools/create_dashboard.py` | Use `get_task_queue_path(ROOT)`. |

### Modified (docs)

| File | Change |
|------|--------|
| `calyx/cbo/README.md` | Paths updated to `runtime/cbo/` and `CALYX_RUNTIME_DIR`. |
| `calyx/cbo/ASSISTING_AGENT.md` | Objectives and queue paths updated to `runtime/cbo/`. |
| `docs/prompts/CBO_onboarding_prompt.md` | Objectives path updated. |
| `docs/CBO_AGENT_ONBOARDING.md` | Objectives path updated. |
| `docs/CALYX_CLI_GUIDE.md` | Objectives path updated. |
| `docs/runtime_artifacts_inventory_2026-02-11.md` | Note added about CBO relocation. |

## New Path Behavior

- **Environment:** `CALYX_RUNTIME_DIR` (default `"runtime"`). CBO state dir: `{repo_root}/{CALYX_RUNTIME_DIR}/cbo/`.
- **Paths:**  
  - `objectives.jsonl`  
  - `objectives_history.jsonl`  
  - `sysint_acknowledged.jsonl`  
  - `task_queue.jsonl`  
  - `task_status.jsonl`  
  - `memory.sqlite`  
  All resolve under that directory. The directory is created on first use (`get_cbo_runtime_dir()` calls `mkdir(parents=True, exist_ok=True)`).
- **Git:** `runtime/` is already in `.gitignore`; no change required.

## Verification Steps

1. **Smoke tests**
   ```bash
   py -m pytest tests/test_cbo_runtime_paths.py -v
   ```
   Expected: 3 passed (runtime state outside code tree, CBO dir under runtime root, paths not under calyx/cbo).

2. **Self-check in code**
   ```python
   from calyx.cbo.runtime_paths import runtime_state_resolves_outside_code_tree
   assert runtime_state_resolves_outside_code_tree() is True
   ```

3. **Runtime dir created**
   Run any CBO flow (e.g. submit objective via API or run overseer once); then:
   ```bash
   ls runtime/cbo/
   ```
   Expected: directory exists and contains the JSONL (and optionally `memory.sqlite`) as they are used.

4. **No new files under calyx/cbo/**
   After running CBO, confirm no new `objectives.jsonl`, `task_queue.jsonl`, etc. under `calyx/cbo/`. Only code and docs remain there.

## Commit

- Message: `Move CBO runtime JSONL state to ignored runtime directory`
