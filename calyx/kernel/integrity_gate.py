"""
System Integrity Gate — Pre-flight validation before any spine operation.

All spine actions must pass this gate. If any component fails pulse check,
no operation proceeds (fail-closed). Prevents mail loss, multi-coordinator
split, and execution against a broken system.

Single-coordinator lease: only one process may hold the lease at a time.
Prevents multiple Cursor/agent sessions from each processing the same
Discord message (triple-envelope / triple-response).
"""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import NamedTuple


def _coordinator_lease_enabled() -> bool:
    """Lease can be disabled via env (e.g. multi-node or tests)."""
    return os.environ.get("CALYX_COORDINATOR_LEASE", "1") != "0"


@contextmanager
def acquire_coordinator_lease(runtime_dir: Path):
    """
    Acquire exclusive coordinator lease. Only one process may hold it.
    Yields True if acquired, False if another coordinator holds it.
    Prevents triple-processing when multiple Cursor/agent sessions run.
    """
    acquired = False
    lease_path = runtime_dir / "cbo" / ".coordinator_lease"
    lease_path.parent.mkdir(parents=True, exist_ok=True)
    fd = None

    if not _coordinator_lease_enabled():
        try:
            yield True
        finally:
            pass
        return

    try:
        fd = os.open(str(lease_path), os.O_RDWR | os.O_CREAT, 0o600)
        if sys.platform == "win32":
            import msvcrt  # pylint: disable=import-error
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError:
                yield False
                return
        else:
            import fcntl  # pylint: disable=import-error
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (OSError, BlockingIOError):
                yield False
                return
        acquired = True
        yield True
    except Exception:
        yield False
    finally:
        if fd is not None and acquired:
            try:
                if sys.platform == "win32":
                    import msvcrt  # pylint: disable=import-error
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl  # pylint: disable=import-error
                    fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                os.close(fd)
            except Exception:
                pass


class IntegrityFailure(NamedTuple):
    """Single component failure."""
    component: str
    reason: str


class SystemIntegrityError(Exception):
    """Raised when integrity gate fails. No operation may proceed."""
    def __init__(self, failures: list[IntegrityFailure]):
        self.failures = failures
        msg = "; ".join(f"{f.component}: {f.reason}" for f in failures)
        super().__init__(msg)


def _check_writable_dir(path: Path, component: str) -> IntegrityFailure | None:
    """Ensure dir exists and is writable (can create + remove a temp file)."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return IntegrityFailure(component, f"cannot_create:{e}")
    test_file = path / ".integrity_check"
    try:
        test_file.write_text("", encoding="utf-8")
        test_file.unlink()
    except OSError as e:
        return IntegrityFailure(component, f"not_writable:{e}")
    return None


def _check_ledger_reachable(runtime_dir: Path) -> IntegrityFailure | None:
    """Replay ledger dir must exist and be writable; ledger file readable or creatable."""
    cbo = runtime_dir / "cbo"
    cbo.mkdir(parents=True, exist_ok=True)
    ledger = cbo / "ingest_replay_ledger.jsonl"
    try:
        if ledger.exists():
            with open(ledger, "r", encoding="utf-8") as f:
                f.read()
        else:
            with open(ledger, "a", encoding="utf-8") as f:
                pass
    except OSError as e:
        return IntegrityFailure("replay_ledger", f"unreachable:{e}")
    return None


def _check_contract_loads(repo_root: Path) -> IntegrityFailure | None:
    """Contract must load."""
    try:
        from calyx.kernel.contract import load_contract
    except ImportError:
        return IntegrityFailure("contract", "kernel_contract_unavailable")
    contract_path = repo_root / "CALYX_CONTRACT.yaml"
    if not contract_path.exists():
        return IntegrityFailure("contract", "file_not_found")
    try:
        load_contract(contract_path)
    except Exception as e:
        return IntegrityFailure("contract", f"load_failed:{e}")
    return None


def _check_readable_dir(path: Path, component: str) -> IntegrityFailure | None:
    """Dir exists and is listable."""
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return IntegrityFailure(component, f"cannot_create:{e}")
    if not path.is_dir():
        return IntegrityFailure(component, "not_a_directory")
    try:
        list(path.iterdir())
    except OSError as e:
        return IntegrityFailure(component, f"not_readable:{e}")
    return None


def check_integrity(
    runtime_dir: Path,
    repo_root: Path,
    *,
    include_execution_path: bool = True,
    skip_if_env: bool = True,
) -> None:
    """
    Run system integrity pulse check. Raises SystemIntegrityError if any component fails.

    Args:
        runtime_dir: Runtime root (e.g. repo_root / "runtime")
        repo_root: Repo root for contract
        include_execution_path: If True, also check work_outbox readable
        skip_if_env: If True and CALYX_SKIP_INTEGRITY_GATE=1, skip (for tests)
    """
    if skip_if_env and os.environ.get("CALYX_SKIP_INTEGRITY_GATE") == "1":
        return

    failures: list[IntegrityFailure] = []

    # Mail inbox
    inbox = runtime_dir / "cbo" / "mail_inbox"
    if f := _check_writable_dir(inbox, "mail_inbox"):
        failures.append(f)

    # Intent artifacts dir
    intents = runtime_dir / "cbo" / "intents"
    if f := _check_writable_dir(intents, "intent_artifacts"):
        failures.append(f)

    # Replay ledger
    if f := _check_ledger_reachable(runtime_dir):
        failures.append(f)

    # Contract
    if f := _check_contract_loads(repo_root):
        failures.append(f)

    # Receipts dir
    receipts = runtime_dir / "receipts"
    if f := _check_writable_dir(receipts, "receipts"):
        failures.append(f)

    # Work outbox (execution path)
    if include_execution_path:
        outbox = runtime_dir / "cbo" / "work_outbox"
        if f := _check_readable_dir(outbox, "work_outbox"):
            failures.append(f)

    if failures:
        raise SystemIntegrityError(failures)


def gate_before_action(
    runtime_dir: Path | None = None,
    repo_root: Path | None = None,
    *,
    include_execution_path: bool = True,
) -> None:
    """
    Convenience: resolve paths and run check_integrity. Use at spine entry points.
    """
    if repo_root is None:
        from calyx.kernel.paths import resolve_repo_root
        repo_root = resolve_repo_root()
    if runtime_dir is None:
        from calyx.kernel.paths import resolve_runtime_dir
        runtime_dir = resolve_runtime_dir(repo_root)
    check_integrity(
        runtime_dir,
        repo_root,
        include_execution_path=include_execution_path,
    )


@contextmanager
def spine_operation_lease(
    runtime_dir: Path,
    repo_root: Path,
    *,
    include_execution_path: bool = True,
    skip_if_env: bool = True,
):
    """
    Acquire coordinator lease and run integrity check. Only one process may proceed.
    Yields True if lease acquired and integrity passed; False otherwise.
    Use to wrap spine operations so multiple Cursor/agent sessions don't each process the same event.
    """
    if skip_if_env and os.environ.get("CALYX_SKIP_INTEGRITY_GATE") == "1":
        yield True
        return
    with acquire_coordinator_lease(runtime_dir) as lease_ok:
        if not lease_ok:
            yield False
            return
        try:
            check_integrity(
                runtime_dir,
                repo_root,
                include_execution_path=include_execution_path,
                skip_if_env=False,
            )
            yield True
        except SystemIntegrityError:
            yield False
