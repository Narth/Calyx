"""
Naming rites ritual (human-owned, Safe Mode).

Prompts for naming config, persists to config/naming_rites_v1.json,
and appends audit to logs/governance/naming_rites.jsonl.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH = Path("config/naming_rites_v1.json")
AUDIT_PATH = Path("logs/governance/naming_rites.jsonl")


def now_iso() -> str:
    from datetime import datetime, timezone

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.write("\n")


def needs_naming_rites() -> bool:
    return not CONFIG_PATH.exists()


@dataclass
class NamingRitesConfig:
    schema: str
    created_at: str
    architect_display_name: str
    system_roles: Dict[str, str]
    agent_naming_rules: Dict[str, Any]


def prompt_naming_rites() -> NamingRitesConfig:
    print("Naming Rites Ritual: please provide the following (press Enter to accept defaults).")
    arch = input("Architect display name [Architect]: ").strip() or "Architect"
    architect_role = input("Role name for architect [Architect]: ").strip() or "Architect"
    gov_role = input("Role name for governance auditor [CBO]: ").strip() or "CBO"
    kernel_role = input("Role name for kernel [BloomOS Kernel]: ").strip() or "BloomOS Kernel"

    # Choose agent naming mode
    print("\nAgent naming mode:")
    print(" 1) Choose from flower list")
    print(" 2) Specify a custom prefix")
    mode = input("Select [1/2, default 2]: ").strip()
    if mode == "1":
        flowers = ["Aster", "Azalea", "Camellia", "Dahlia", "Gardenia", "Iris", "Lily", "Magnolia", "Orchid", "Peony", "Rose", "Zinnia"]
        print("Available flowers:")
        for idx, f in enumerate(flowers, 1):
            print(f" {idx}) {f}")
        choice = input("Pick a flower number or name [Rose]: ").strip()
        chosen = "Rose"
        if choice:
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(flowers):
                    chosen = flowers[idx]
            else:
                if choice in flowers:
                    chosen = choice
        prefix = chosen
    else:
        prefix = input("Agent naming prefix [Calyx]: ").strip() or "Calyx"

    require_confirm = input("Require human confirmation for agent names? [Y/n]: ").strip().lower()
    require_human_confirmation = False if require_confirm in ("n", "no") else True

    cfg = NamingRitesConfig(
        schema="naming_rites_v1",
        created_at=now_iso(),
        architect_display_name=arch,
        system_roles={
            "architect": architect_role,
            "governance_auditor": gov_role,
            "kernel": kernel_role,
        },
        agent_naming_rules={
            "prefix": prefix,
            "require_human_confirmation": require_human_confirmation,
        },
    )
    return cfg


def persist_naming_rites(cfg: NamingRitesConfig) -> Path:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
    append_jsonl(
        AUDIT_PATH,
        {
            "timestamp": now_iso(),
            "event": "naming_rites_set",
            "config_path": str(CONFIG_PATH),
            "schema": cfg.schema,
        },
    )
    return CONFIG_PATH
