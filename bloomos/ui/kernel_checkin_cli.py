"""Manual BloomOS kernel check-in CLI (reflection-only).

Invokes run_kernel_checkin() once and prints a short summary.
"""

from __future__ import annotations

from tools.bloomos_kernel_checkin import run_kernel_checkin


def main() -> None:
    record = run_kernel_checkin()
    print(
        f"kernel_checkin recorded: {record['checkin_id']} at {record['timestamp']} "
        f"mode={record['mode']['state']} kernel_id={record['kernel_id']}"
    )


if __name__ == "__main__":
    main()
