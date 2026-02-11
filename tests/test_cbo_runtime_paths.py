"""Smoke test: CBO runtime state resolves outside the repo code tree (runtime/cbo/)."""

from pathlib import Path

from calyx.cbo.runtime_paths import (
    get_cbo_runtime_dir,
    get_objectives_path,
    get_task_queue_path,
    runtime_state_resolves_outside_code_tree,
)


def test_runtime_state_resolves_outside_code_tree():
    """Runtime dir must not be under calyx/cbo/ (state is relocated to runtime/cbo/)."""
    assert runtime_state_resolves_outside_code_tree() is True


def test_cbo_runtime_dir_under_runtime_root():
    """CBO runtime dir should be root/{CALYX_RUNTIME_DIR}/cbo/ (default runtime/cbo/)."""
    root = Path(__file__).resolve().parents[1]
    cbo_dir = get_cbo_runtime_dir(root)
    assert cbo_dir.name == "cbo"
    assert root in cbo_dir.parents
    assert cbo_dir.resolve() != (root / "calyx" / "cbo").resolve()


def test_runtime_paths_do_not_live_under_calyx_cbo():
    """objectives and task_queue paths must not be under repo calyx/cbo/."""
    root = Path(__file__).resolve().parents[1]
    calyx_cbo = (root / "calyx" / "cbo").resolve()
    objectives = get_objectives_path(root).resolve()
    task_queue = get_task_queue_path(root).resolve()
    try:
        objectives.relative_to(calyx_cbo)
        raise AssertionError("objectives.jsonl should not be under calyx/cbo/")
    except ValueError:
        pass
    try:
        task_queue.relative_to(calyx_cbo)
        raise AssertionError("task_queue.jsonl should not be under calyx/cbo/")
    except ValueError:
        pass
