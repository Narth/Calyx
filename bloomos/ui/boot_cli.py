"""
One-click demo boot: kernel init + naming rites + assistance intake.
Safe Mode, deny-all, append-only. No external access; no schedulers.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from bloomos.kernel.boot import boot_kernel
from bloomos.human.naming_rites import needs_naming_rites, prompt_naming_rites, persist_naming_rites
from bloomos.human.assistance_intake import prompt_assistance


def write_summary(boot_id: str, naming_path: str | None, assist_path: str | None) -> Path:
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    safe_boot_id = boot_id.replace(":", "-")
    path = reports_dir / f"demo_safe_boot_run_{safe_boot_id}.md"
    lines = [
        "# Demo Safe Boot Run Summary",
        "",
        f"- boot_id: {boot_id}",
        f"- naming_rites_config: {naming_path or 'existing'}",
        f"- assist_envelope: {assist_path or 'none'}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Calyx/BloomOS demo safe boot (one click).")
    parser.add_argument("--profile", default="demo_safe", help="Profile name (default: demo_safe)")
    args = parser.parse_args()

    boot = boot_kernel(profile=args.profile)
    naming_path = None
    assist_path = None

    if boot.naming_rites_required:
        cfg = prompt_naming_rites()
        naming_path = str(persist_naming_rites(cfg))
    else:
        print("Naming rites already configured.")

    assist = prompt_assistance(boot.boot_id)
    assist_path = assist.get("envelope_path")

    summary_path = write_summary(boot.boot_id, naming_path, assist_path)
    print("\n=== Demo Safe Boot Completed ===")
    print(f"boot_id: {boot.boot_id}")
    print(f"kernel_boot_log: logs/bloomos/kernel_boot.jsonl")
    print(f"naming_rites_config: {naming_path or 'existing'}")
    print(f"assist_request: {assist_path}")
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    main()
