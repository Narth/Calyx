from __future__ import annotations

import importlib.util
from pathlib import Path

from calyx.cbo import discord_gateway


def _write_ids_file(root: Path) -> None:
    (root / "DISCORD_IDS.md").write_text(
        "\n".join(
            [
                "# Discord IDs",
                "- **Station Health Channel ID:** 123456789012345678",
                "- **Authorized User ID (DM processing):** 234567890123456789",
            ]
        ),
        encoding="utf-8",
    )


def _load_preflight_module():
    repo_root = Path(__file__).resolve().parents[1]
    path = repo_root / "Scripts" / "discord_gateway_preflight.py"
    spec = importlib.util.spec_from_file_location("discord_gateway_preflight", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gateway_parse_discord_ids_markdown_bold(tmp_path: Path) -> None:
    _write_ids_file(tmp_path)

    channels, users = discord_gateway._parse_discord_ids_md(tmp_path)

    assert channels == ["123456789012345678"]
    assert users == ["234567890123456789"]


def test_preflight_parse_discord_ids_markdown_bold(tmp_path: Path) -> None:
    _write_ids_file(tmp_path)
    preflight = _load_preflight_module()

    channels, users = preflight._parse_discord_ids_md(tmp_path)

    assert channels == ["123456789012345678"]
    assert users == ["234567890123456789"]
