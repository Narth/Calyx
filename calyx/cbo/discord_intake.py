"""
Discord Intake Adapter - Calyx Mail as sole ingress.
Converts Discord messages to Mail Envelopes and routes to CBO ingest only.
No direct execution. No write to execution outbox. All flow via CBO ingest.
"""
from __future__ import annotations

import json
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import discord
except ImportError:
    discord = None

try:
    from calyx.mail.adapters.discord_adapter import (
        discord_message_to_mail_envelope,
        deliver_discord_mail_to_cbo_ingest,
    )
except ImportError:
    discord_message_to_mail_envelope = None
    deliver_discord_mail_to_cbo_ingest = None


class DiscordIntake:
    """Discord intake: convert to Mail Envelope, route to CBO ingest only. No execution outbox."""

    # Max recent message keys to keep for deduplication (avoid duplicate processing per message)
    _DEDUPE_CAP = 500

    def __init__(self, config_path: str | Path, repo_root: str | Path):
        self.config_path = Path(config_path)
        self.repo_root = Path(repo_root)
        self.config = self._load_config()
        self.runtime_dir = self.repo_root / "runtime"
        self.receipts_path = self.runtime_dir / "receipts"
        self.schema_path = self.repo_root / "telemetry" / "envelopes" / "INTENT_ENVELOPE_SCHEMA_v0.1.json"
        
        self.receipts_path.mkdir(parents=True, exist_ok=True)
        self.client = None
        self.schema = self._load_schema()
        # One reply per Discord message: (message_id, channel_id) -> skip if already seen
        self._seen_message_keys: set[tuple[str, str]] = set()
        self._seen_message_order: list[tuple[str, str]] = []
    
    def _load_config(self) -> dict:
        """Load Discord config from JSON."""
        if not self.config_path.exists():
            return {
                "channel_allowlist": [],
                "bot_token_env_var": "DISCORD_BOT_TOKEN",
                "polling_interval_seconds": 30,
                "intake_enabled": False,
                "last_message_id": None
            }
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _load_schema(self) -> dict:
        """Load intent envelope schema."""
        if not self.schema_path.exists():
            return {}
        with open(self.schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _validate_envelope(self, envelope: dict) -> tuple[bool, Optional[str]]:
        """Basic schema validation (simplified - full validation would use jsonschema)."""
        required_fields = [
            "envelope_id", "ts_utc", "source", "author", "channel_id",
            "message_id", "intent", "task_type", "scope", "constraints",
            "requires_human_approval", "evidence_requirements"
        ]
        
        for field in required_fields:
            if field not in envelope:
                return False, f"missing_required_field: {field}"
        
        # Validate task_type enum
        allowed_tasks = [
            "code_review", "lint_fix", "test_run", "doc_update",
            "refactor_scope", "benchmark_run", "schema_validation", "receipt_generation"
        ]
        if envelope["task_type"] not in allowed_tasks:
            return False, f"invalid_task_type: {envelope['task_type']}"
        
        # Validate source
        if envelope["source"] not in ["discord", "laptop_node"]:
            return False, f"invalid_source: {envelope['source']}"
        
        return True, None
    
    def _create_mail_envelope_from_message(
        self,
        message: "discord.Message",
        intent: str,
        task_type: str,
        scope: dict,
        constraints: dict,
        risk_hint: Optional[str] = None,
        requires_approval: bool = False,
        approval_token: Optional[str] = None,
    ) -> dict:
        """Create Mail Envelope via adapter; route to CBO ingest only (no execution outbox)."""
        if discord_message_to_mail_envelope is None:
            raise RuntimeError("calyx.mail.adapters.discord_adapter not available")
        return discord_message_to_mail_envelope(
            author_id=str(message.author.id),
            channel_id=str(message.channel.id),
            message_id=str(message.id),
            content=intent,
            task_type=task_type,
            scope=scope,
            constraints=constraints,
            risk_hint=risk_hint,
            requires_human_approval=requires_approval,
            approval_token=approval_token,
        )
    
    def _deliver_mail_to_cbo_ingest(self, envelope: dict) -> tuple[Path, str] | None:
        """Route Mail Envelope to CBO ingest only. Returns (path, sha256) or None if replay."""
        if deliver_discord_mail_to_cbo_ingest is None:
            raise RuntimeError("calyx.mail.adapters.discord_adapter not available")
        path = deliver_discord_mail_to_cbo_ingest(envelope, self.runtime_dir)
        if path is None:
            return None
        envelope_bytes = json.dumps(envelope, sort_keys=True, ensure_ascii=False).encode("utf-8")
        envelope_hash = hashlib.sha256(envelope_bytes).hexdigest()
        return path, envelope_hash
    
    def _write_receipt(
        self,
        message_metadata: dict,
        envelope_hash: str,
        validation_result: bool,
        allow_deny: str,
        error: Optional[str] = None
    ):
        """Write intake receipt."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        receipt = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "message_metadata": message_metadata,
            "envelope_sha256": envelope_hash,
            "validation_result": validation_result,
            "allow_deny_decision": allow_deny,
            "error": error
        }
        
        receipt_path = self.receipts_path / f"discord_intake__{ts}.jsonl"
        with open(receipt_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(receipt, ensure_ascii=False) + "\n")
    
    def process_message(
        self,
        message: "discord.Message",
        intent: str,
        task_type: str,
        scope: dict,
        constraints: dict,
        **kwargs
    ) -> tuple[bool, Optional[str], Optional[dict]]:
        """
        Process a Discord message into an intent envelope.
        Returns (success, error_message, envelope_dict).
        """
        if not self.config.get("intake_enabled", False):
            return False, "intake_disabled", None
        
        # Check if DM or channel (validation happens in on_message handler)
        is_dm = isinstance(message.channel, discord.DMChannel) if discord else False
        channel_id = str(message.channel.id)
        
        # For DMs, we already validated authorized user in on_message
        # For channels, we already validated allowlist in on_message
        # So we can proceed here

        # Lease + integrity enforced in router when we call _deliver_mail_to_cbo_ingest.
        # Create Mail Envelope via adapter
        envelope = self._create_mail_envelope_from_message(
            message, intent, task_type, scope, constraints, **kwargs
        )

        # Validate
        is_valid, validation_error = self._validate_envelope(envelope)
        if not is_valid:
            message_metadata = {
                "channel_id": channel_id,
                "message_id": str(message.id),
                "author_id": str(message.author.id)
            }
            self._write_receipt(
                message_metadata, "", False, "deny", validation_error
            )
            return False, validation_error, None

        # Route to CBO ingest only (no execution outbox); replay or lease failure rejected
        delivered = self._deliver_mail_to_cbo_ingest(envelope)
        if delivered is None:
            return False, "replay_or_lease_held", None
        envelope_path, envelope_hash = delivered

        # Write receipt
        is_dm = isinstance(message.channel, discord.DMChannel) if discord else False
        message_metadata = {
            "channel_id": channel_id,
            "message_id": str(message.id),
            "author_id": str(message.author.id),
            "is_dm": is_dm,
            "content_preview": message.content[:100] if message.content else ""
        }
        self._write_receipt(
            message_metadata, envelope_hash, True, "allow"
        )

        return True, None, envelope
    
    async def start_bot(self):
        """Start Discord bot (requires discord.py)."""
        if discord is None:
            raise ImportError("discord.py not installed. Install with: pip install discord.py")
        
        token = os.getenv(self.config.get("bot_token_env_var", "DISCORD_BOT_TOKEN"))
        if not token:
            raise ValueError(f"Discord bot token not found in env var: {self.config['bot_token_env_var']}")
        
        intents = discord.Intents.default()
        intents.message_content = True
        
        self.client = discord.Client(intents=intents)
        
        @self.client.event
        async def on_ready():
            print(f"Discord intake bot logged in as {self.client.user}")
        
        @self.client.event
        async def on_message(message):
            # Skip bot messages
            if message.author == self.client.user:
                return
            
            # Check if DM or channel
            is_dm = isinstance(message.channel, discord.DMChannel)
            channel_id = str(message.channel.id)
            authorized_user_id = self.config.get("authorized_user_id")
            
            # Allow DMs from authorized user
            if is_dm:
                if str(message.author.id) != authorized_user_id:
                    # Ignore DMs from non-authorized users
                    return
            else:
                # For channels, check allowlist
                if channel_id not in self.config.get("channel_allowlist", []):
                    return
            
            # Extract intent from message content
            intent_text = message.content.strip()
            if not intent_text:
                # Skip empty messages
                return

            # One message → one envelope → one reply: dedupe by (message_id, channel_id)
            msg_key = (str(message.id), channel_id)
            if msg_key in self._seen_message_keys:
                return
            self._seen_message_keys.add(msg_key)
            self._seen_message_order.append(msg_key)
            if len(self._seen_message_order) > self._DEDUPE_CAP:
                old = self._seen_message_order.pop(0)
                self._seen_message_keys.discard(old)
            
            # Simple intent extraction - treat message as intent
            # Default task_type to doc_update for now (can be enhanced later)
            task_type = "doc_update"
            
            # Try to detect task type from message content
            intent_lower = intent_text.lower()
            if any(word in intent_lower for word in ["review", "code review", "check code"]):
                task_type = "code_review"
            elif any(word in intent_lower for word in ["lint", "fix lint", "format"]):
                task_type = "lint_fix"
            elif any(word in intent_lower for word in ["test", "run test", "tests"]):
                task_type = "test_run"
            elif any(word in intent_lower for word in ["refactor", "restructure"]):
                task_type = "refactor_scope"
            elif any(word in intent_lower for word in ["benchmark", "bench"]):
                task_type = "benchmark_run"
            elif any(word in intent_lower for word in ["validate", "schema"]):
                task_type = "schema_validation"
            
            # Default scope - can be enhanced with parsing
            scope = {"paths": ["**"]}  # Default to all paths
            constraints = {"timeout_seconds": 300}  # 5 minute default timeout
            
            # Process message into envelope
            try:
                success, error_msg, envelope = self.process_message(
                    message,
                    intent=intent_text,
                    task_type=task_type,
                    scope=scope,
                    constraints=constraints
                )
                
                if success and envelope:
                    # Mail delivered to CBO ingest. Send intake confirmation, then CBO reply.
                    channel_name = "DM" if is_dm else message.channel.name
                    confirm_msg = (
                        f"✅ Mail received: `{envelope['envelope_id'][:8]}...` → CBO ingest\n"
                        f"Task: `{task_type}`. No execution until CBO intent pipeline."
                    )
                    await message.channel.send(confirm_msg)
                    # CBO reply: confirm receipt, provide integrity/status when requested
                    try:
                        from calyx.cbo.discord_response import DiscordResponseHandler
                        handler = DiscordResponseHandler(self.client, self.config_path)
                        await handler.process_envelope_and_respond(envelope, is_dm=is_dm)
                    except Exception as e:
                        print(f"CBO response failed: {e}")
                        try:
                            await message.channel.send(f"❌ CBO response failed: {str(e)[:200]}")
                        except Exception:
                            pass
                    print(f"Processed message from {message.author.name} in {channel_name}: {envelope['envelope_id']}")
                else:
                    # Send error notification
                    error_msg_display = error_msg or "Unknown error"
                    await message.channel.send(f"❌ Failed to process message: {error_msg_display}")
                    print(f"Failed to process message: {error_msg_display}")
                    
            except Exception as e:
                error_msg = f"Exception processing message: {str(e)}"
                print(error_msg)
                try:
                    await message.channel.send(f"❌ Error: {error_msg}")
                except:
                    pass  # Fail silently if we can't send error message
        
        await self.client.start(token)


def main():
    """CLI entry point for testing."""
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description="Discord Intake Adapter")
    parser.add_argument("--config", default="runtime/discord_config.json")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--test-envelope", action="store_true", help="Create test envelope")
    parser.add_argument("--run", action="store_true", help="Start the Discord bot (stays online)")
    args = parser.parse_args()
    
    intake = DiscordIntake(args.config, args.repo_root)
    
    if args.run:
        asyncio.run(intake.start_bot())
        return
    
    if args.test_envelope:
        # Create a test envelope
        test_envelope = {
            "envelope_id": str(uuid.uuid4()),
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "source": "discord",
            "author": "test_user_123",
            "channel_id": "test_channel_456",
            "message_id": "test_message_789",
            "intent": "Test intent for validation",
            "task_type": "doc_update",
            "risk_hint": "low",
            "scope": {"paths": ["docs/**"]},
            "constraints": {"timeout_seconds": 60},
            "requires_human_approval": False,
            "approval_token": None,
            "evidence_requirements": {"harness_lanes": [], "checks": [], "receipt_types": []},
            "signature": None
        }
        
        is_valid, error = intake._validate_envelope(test_envelope)
        if is_valid:
            delivered = intake._deliver_mail_to_cbo_ingest(test_envelope)
            if delivered is None:
                print("Rejected (replay)")
            else:
                path, hash_val = delivered
                print(f"Test mail delivered to CBO ingest: {path}")
                print(f"SHA256: {hash_val}")
        else:
            print(f"Validation failed: {error}")
    else:
        print("Discord intake adapter initialized.")
        print("Use --test-envelope to create a test envelope.")
        print("Use --run to start the bot and stay online.")


if __name__ == "__main__":
    main()
