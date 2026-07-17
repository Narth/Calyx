"""Mail adapters: convert external input (Discord, CLI) to Mail Envelopes and route to CBO ingest."""

from __future__ import annotations

from .discord_adapter import discord_message_to_mail_envelope
from .cli_adapter import cli_args_to_mail_envelope

__all__ = ["discord_message_to_mail_envelope", "cli_args_to_mail_envelope"]
