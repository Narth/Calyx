"""
Calyx Discord Gateway — WO_OPENCLAW_UNIFIED_EXECUTOR_V1.
WO_IDLE_ACTIVITY_GOVERNANCE_V3: system task events, task budget, suppressible heartbeat.

Governed Discord path: Discord → CBO /chat → Discord. No local LLM.
All traffic flows through CBO Core; ledger emits openclaw.channel.* via CBO.

When CALYX_GOVERNANCE_REQUIRED=true (default): never fall back to local LLM.
If CBO unreachable: emit openclaw.channel.timeout, reply "Station unavailable."
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    import discord
except ImportError:
    discord = None

try:
    import httpx
except ImportError:
    httpx = None


DEFAULT_CBO_BASE = "http://127.0.0.1:7778"
DEFAULT_TIMEOUT_SEC = 30
SAFE_OFFLINE_MSG = "Station unavailable."

# WO_IDLE_ACTIVITY_GOVERNANCE_V3: operator controls
def _heartbeat_push_enabled() -> bool:
    v = os.environ.get("CALYX_HEARTBEAT_PUSH_ENABLED", "").strip().lower()
    if v in ("false", "0", "no", "off"):
        return False
    return True


def _heartbeat_push_interval_min() -> int:
    v = os.environ.get("CALYX_HEARTBEAT_PUSH_INTERVAL_MIN", "").strip()
    if v:
        return max(0, int(v))
    return max(0, int(os.environ.get("DISCORD_HEARTBEAT_INTERVAL_MIN", "30")))


def _heartbeat_push_destination() -> str:
    v = os.environ.get("CALYX_HEARTBEAT_PUSH_DESTINATION", "DM").strip().upper()
    if v in ("DM", "CHANNEL", "OFF"):
        return v
    return "DM"


def _emit(event: str, msg: str, level: str = "INFO", data: dict | None = None, corr_id: str | None = None, task_corr_id: str | None = None, task_name: str | None = None, schedule_id: str | None = None, trigger_reason: str | None = None) -> None:
    """Emit to Station Event Ledger. WO_CAUSAL_ENVELOPE_AUDIT_CLARITY_V1: pass task context for task emits."""
    try:
        from calyx.kernel.event_ledger import emit as ledger_emit
        ledger_emit(level=level, component="calyx_gateway", event=event, msg=msg, data=data or {}, corr_id=corr_id, task_corr_id=task_corr_id, task_name=task_name, schedule_id=schedule_id, trigger_reason=trigger_reason)
    except Exception:
        pass


def _resolve_repo_root() -> Path:
    env_root = os.environ.get("CALYX_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[2]


def _parse_discord_ids_md(root: Path) -> tuple[list[str], list[str]]:
    """Parse DISCORD_IDS.md for channel and user IDs. Returns (channel_allowlist, authorized_user_ids)."""
    path = root / "DISCORD_IDS.md"
    channels: list[str] = []
    users: list[str] = []
    if not path.exists():
        return channels, users
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if "Station Health Channel ID" in line or ("channel" in line.lower() and "ID" in line):
                m = re.search(r":\s*(\d{17,20})", line)
                if m and m.group(1) not in channels:
                    channels.append(m.group(1))
            if "Authorized User ID" in line or "User ID" in line:
                m = re.search(r":\s*(\d{17,20})", line)
                if m and m.group(1) not in users:
                    users.append(m.group(1))
    except Exception:
        pass
    return channels, users


def _resolve_config(
    cli_channels: list[str] | None,
    cli_users: list[str] | None,
) -> tuple[list[str], list[str]]:
    """Resolve config: CLI args > env vars > DISCORD_IDS.md."""
    root = _resolve_repo_root()
    channels = list(cli_channels) if cli_channels else []
    users = list(cli_users) if cli_users else []
    if not channels:
        env = os.environ.get("DISCORD_CHANNEL_ALLOWLIST", "").strip()
        if env:
            channels = [x.strip() for x in env.replace(",", " ").split() if x.strip()]
    if not users:
        env = os.environ.get("DISCORD_AUTHORIZED_USERS", "").strip()
        if env:
            users = [x.strip() for x in env.replace(",", " ").split() if x.strip()]
    if not channels or not users:
        ids_channels, ids_users = _parse_discord_ids_md(root)
        if not channels:
            channels = ids_channels
        if not users:
            users = ids_users
    return channels, users


class CalyxDiscordGateway:
    """
    Discord bot that relays every message to CBO /chat.
    No LLM. Governance is default. Ledger visibility via CBO.
    """

    def __init__(
        self,
        token_env: str = "DISCORD_BOT_TOKEN",
        cbo_base: str | None = None,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
        governance_required: bool = True,
        model_role: str = "local",
        channel_allowlist: list[str] | None = None,
        authorized_user_ids: list[str] | None = None,
    ):
        self.token_env = token_env
        self.cbo_base = (cbo_base or os.environ.get("CBO_BASE_URL") or DEFAULT_CBO_BASE).rstrip("/")
        self.timeout_sec = timeout_sec
        self.governance_required = governance_required
        self.model_role = (model_role or "local").strip().lower()
        self.channel_allowlist = list(channel_allowlist) if channel_allowlist else []
        self.authorized_user_ids = set(str(x) for x in (authorized_user_ids or []))
        self.client = None
        self._heartbeat_user_id = os.environ.get("DISCORD_HEARTBEAT_USER_ID") or (list(self.authorized_user_ids)[0] if self.authorized_user_ids else None)
        self._heartbeat_interval_min = _heartbeat_push_interval_min()
        self._heartbeat_push_enabled = _heartbeat_push_enabled()
        self._heartbeat_push_destination = _heartbeat_push_destination()
        self._heartbeat_task = None
        self._outbox_path = _resolve_repo_root() / "runtime" / "discord_outbox.jsonl"

    def _emit_identity(self) -> None:
        """WO: On boot, emit openclaw.service.identity + station.config.effective (WO_IDLE_ACTIVITY_GOVERNANCE_V3)."""
        try:
            cwd = str(Path.cwd())
            pid = os.getpid()
            _emit(
                "openclaw.service.identity",
                "Calyx Discord Gateway started",
                level="INFO",
                data={
                    "cwd": cwd[:200],
                    "pid": pid,
                    "governance_mode": "required" if self.governance_required else "optional",
                    "CALYX_GOVERNANCE_REQUIRED": self.governance_required,
                    "model_role": self.model_role,
                    "cbo_base": self.cbo_base,
                },
            )
            _emit(
                "station.config.effective",
                "Effective config (WO_IDLE_ACTIVITY_GOVERNANCE_V3)",
                level="INFO",
                data={
                    "CALYX_HEARTBEAT_PUSH_ENABLED": self._heartbeat_push_enabled,
                    "CALYX_HEARTBEAT_PUSH_INTERVAL_MIN": self._heartbeat_interval_min,
                    "CALYX_HEARTBEAT_PUSH_DESTINATION": self._heartbeat_push_destination,
                },
            )
            # WO_HEARTBEAT_SENDER_UNIFICATION_V1: exactly one sender identity
            heartbeat_sender_enabled = bool(
                self._heartbeat_push_enabled
                and self._heartbeat_user_id
                and self._heartbeat_interval_min > 0
                and self._heartbeat_push_destination != "OFF"
            )
            _emit(
                "discord.heartbeat.sender.identity",
                "Discord heartbeat sender identity",
                level="INFO",
                data={
                    "component": "calyx_gateway",
                    "pid": os.getpid(),
                    "module_entrypoint": "calyx.cbo.discord_gateway",
                    "heartbeat_sender_enabled": heartbeat_sender_enabled,
                },
            )
            # WO_GOVERNANCE_SINGULARITY_V3: Boot-time singularity confirmation
            if heartbeat_sender_enabled:
                _emit(
                    "audit.runtime.singularity.confirmed",
                    "Canonical heartbeat sender registered",
                    level="INFO",
                    data={"sender_identity": "calyx.cbo.discord_gateway", "pid": os.getpid()},
                )
        except Exception:
            pass

    def _allowed_message(self, message: "discord.Message") -> bool:
        """WO_GATEWAY_DENY_BY_DEFAULT: channel_allowlist==[] ⇒ deny all guild channels; authorized_user_ids==[] ⇒ deny all DMs."""
        if message.author == self.client.user:
            return False
        channel_id = str(message.channel.id)
        author_id = str(message.author.id)
        is_dm = isinstance(message.channel, discord.DMChannel) if discord else False
        if is_dm:
            if not self.authorized_user_ids:
                return False
            return author_id in self.authorized_user_ids
        if not self.channel_allowlist:
            return False
        return channel_id in self.channel_allowlist

    async def _send_with_governance(
        self,
        channel: "discord.abc.Messageable",
        content: str,
        *,
        corr_id: str | None = None,
        task_corr_id: str | None = None,
    ) -> bool:
        """WO_IDLE_ACTIVITY_GOVERNANCE_V3: Send only if corr_id or task_corr_id set. Else emit violation."""
        if corr_id or task_corr_id:
            await channel.send(content[:2000])
            return True
        try:
            from calyx.kernel.governance_budget import append_fe_candidate
            _emit("budget.violation", "orphan_outbound_action", level="WARN", data={"reason": "send without corr_id or task_corr_id"})
            _emit("governance.assertion.failed", "orphan_outbound_action", level="WARN", data={"reason": "send without corr_id or task_corr_id"})
            append_fe_candidate("orphan_outbound_action", "gateway", "Outbound send attempted without corr_id or task_corr_id", component="calyx_gateway")
        except Exception:
            pass
        return False

    def _read_state_summary(self) -> str:
        """Read STATE.md and runtime/station_health.json; return compact summary for Discord."""
        try:
            root = _resolve_repo_root()
            state_path = root / "STATE.md"
            health_path = root / "runtime" / "station_health.json"
            lines = []
            if state_path.exists():
                text = state_path.read_text(encoding="utf-8", errors="replace")
                for key in ("Status:", "heartbeat_ts:", "health:", "checks:", "entropy_tier:"):
                    for line in text.splitlines():
                        if line.strip().startswith(key):
                            lines.append(line.strip())
                            break
            if health_path.exists():
                try:
                    data = json.loads(health_path.read_text(encoding="utf-8", errors="replace"))
                    cpu = data.get("cpu_pct")
                    ram = data.get("ram_pct")
                    if cpu is not None or ram is not None:
                        parts = []
                        if cpu is not None:
                            parts.append(f"CPU: {cpu}%")
                        if ram is not None:
                            parts.append(f"RAM: {ram}%")
                        lines.append(" | ".join(parts))
                except Exception:
                    pass
            return "\n".join(lines) if lines else "STATE unavailable"
        except Exception:
            return "STATE read failed"

    async def _heartbeat_loop(self) -> None:
        """WO_IDLE_ACTIVITY_GOVERNANCE_V3: System task. Every N min, send STATE/HEALTH to DM. Fully suppressible."""
        if not self._heartbeat_push_enabled or not self._heartbeat_user_id or self._heartbeat_interval_min <= 0:
            return
        if self._heartbeat_push_destination == "OFF":
            return
        interval_sec = self._heartbeat_interval_min * 60
        task_name = "heartbeat_push"
        schedule_id = "hb_push_30m"
        node_id = os.environ.get("CALYX_NODE_ID", "gateway")
        while True:
            await asyncio.sleep(interval_sec)
            task_corr_id = str(uuid.uuid4())
            t0 = time.perf_counter()
            try:
                from calyx.kernel.event_ledger import set_task_context, clear_task_context
                set_task_context(task_corr_id, task_name, schedule_id, "interval")
                _emit(
                    "system.task.triggered",
                    f"System task {task_name} started",
                    level="INFO",
                    data={"task_name": task_name, "schedule_id": schedule_id, "trigger_reason": "interval", "task_corr_id": task_corr_id},
                    task_corr_id=task_corr_id,
                    task_name=task_name,
                    schedule_id=schedule_id,
                    trigger_reason="interval",
                )
                user = await self.client.fetch_user(int(self._heartbeat_user_id))
                channel = await user.create_dm()
                summary = self._read_state_summary()
                msg = f"**Station heartbeat**\n{summary}"
                sent = await self._send_with_governance(channel, msg, task_corr_id=task_corr_id)
                wall_time_ms = int((time.perf_counter() - t0) * 1000)
                if sent:
                    from calyx.kernel.governance_budget import write_task_budget_record
                    ts_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    write_task_budget_record(
                        ts_utc=ts_utc,
                        task_corr_id=task_corr_id,
                        task_name=task_name,
                        schedule_id=schedule_id,
                        node_id=node_id,
                        entry_point="scheduler",
                        wall_time_ms=wall_time_ms,
                        tool_calls=[],
                        tool_calls_total=0,
                        claims_attempted=0,
                        claims_verified=0,
                        claims_failed=0,
                        outbound_kind="discord_dm",
                        outbound_destination=f"redacted:{self._heartbeat_user_id[:4]}...",
                        outbound_message_type="heartbeat",
                        canonical_receipt_written=False,
                        _emit=_emit,
                    )
                    _emit("system.task.completed", f"System task {task_name} completed", level="INFO", data={"task_corr_id": task_corr_id, "task_name": task_name}, task_corr_id=task_corr_id, task_name=task_name, schedule_id=schedule_id, trigger_reason="interval")
                    _emit("calyx_gateway.heartbeat", "Heartbeat sent to Discord DM", data={"user_id": self._heartbeat_user_id, "task_corr_id": task_corr_id}, task_corr_id=task_corr_id, task_name=task_name, schedule_id=schedule_id, trigger_reason="interval")
                else:
                    _emit("system.task.failed", f"System task {task_name} failed (orphan send blocked)", level="WARN", data={"task_corr_id": task_corr_id, "task_name": task_name}, task_corr_id=task_corr_id, task_name=task_name, schedule_id=schedule_id, trigger_reason="interval")
            except Exception as e:
                import sys
                wall_time_ms = int((time.perf_counter() - t0) * 1000)
                print(f"[gateway] Heartbeat failed: {e}", file=sys.stderr, flush=True)
                _emit("system.task.failed", f"System task {task_name} failed: {e}", level="WARN", data={"task_corr_id": task_corr_id, "task_name": task_name}, task_corr_id=task_corr_id, task_name=task_name, schedule_id=schedule_id, trigger_reason="interval")
                _emit("calyx_gateway.heartbeat_failed", str(e), level="WARN", data={"user_id": self._heartbeat_user_id}, task_corr_id=task_corr_id, task_name=task_name, schedule_id=schedule_id, trigger_reason="interval")
            finally:
                try:
                    from calyx.kernel.event_ledger import clear_task_context
                    clear_task_context()
                except Exception:
                    pass

    async def _outbox_loop(self) -> None:
        """Placeholder. No-op to prevent AttributeError (WO_IDLE_ACTIVITY_GOVERNANCE_V3)."""
        while True:
            await asyncio.sleep(3600)

    async def _process_outbox(self) -> None:
        """Placeholder. No-op to prevent AttributeError (WO_IDLE_ACTIVITY_GOVERNANCE_V3)."""
        while True:
            await asyncio.sleep(3600)

    async def _call_cbo(self, user_text: str, session_id: str, corr_id: str) -> tuple[str | None, str | None]:
        """
        POST to CBO /chat. Returns (reply_text, error).
        CBO emits openclaw.channel.inbound/outbound/rejected.
        """
        if not httpx:
            return None, "httpx not installed"
        url = f"{self.cbo_base}/chat"
        payload = {
            "user_text": user_text,
            "session_id": session_id,
            "mode": "dev",
            "allow_tools": True,
            "model_role": self.model_role,
            "allow_second_opinion": self.model_role == "second_opinion",
        }
        headers = {
            "Content-Type": "application/json",
            "X-Calyx-Source": "calyx-discord-gateway",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                r = await client.post(url, json=payload, headers=headers)
                if r.status_code >= 400:
                    return None, f"CBO returned {r.status_code}: {(r.text or '')[:200]}"
                data = r.json()
                reply = (data.get("reply_text") or "").strip()
                return reply or "(no reply)", None
        except httpx.TimeoutException:
            _emit(
                "openclaw.channel.timeout",
                f"CBO did not respond within {self.timeout_sec}s",
                level="WARN",
                data={"session_id": session_id[:32], "timeout_sec": self.timeout_sec},
                corr_id=corr_id,
            )
            return None, "timeout"
        except Exception as e:
            _emit(
                "openclaw.channel.timeout",
                f"CBO unreachable: {e}",
                level="WARN",
                data={"session_id": session_id[:32], "error": str(e)[:200]},
                corr_id=corr_id,
            )
            return None, str(e)

    def _redact_for_public(self, text: str) -> str:
        """WO: If reply contains raw STATE-like JSON, replace with summary for guild channels."""
        if not text or "{" not in text:
            return text
        if re.search(r'"status"\s*:\s*["\']', text) and re.search(r'"checks"\s*:', text):
            return "Station status: see DM for details. (Public channels do not receive raw state.)"
        return text

    async def _on_message(self, message: "discord.Message") -> None:
        try:
            if not self._allowed_message(message):
                return
            text = (message.content or "").strip()
            if not text:
                return

            corr_id = str(uuid.uuid4())[:16]
            session_id = f"discord_{message.channel.id}"
            is_guild_channel = not isinstance(message.channel, discord.DMChannel) if discord else False
            import sys
            print(f"[gateway] Inbound: {text[:80]}...", file=sys.stderr, flush=True)

            reply, err = await self._call_cbo(text, session_id, corr_id)

            if err:
                print(f"[gateway] CBO error: {err}", file=sys.stderr, flush=True)
                await self._send_with_governance(message.channel, SAFE_OFFLINE_MSG if self.governance_required else f"Station unavailable: {err[:200]}", corr_id=corr_id)
                return

            if is_guild_channel:
                reply = self._redact_for_public(reply)
            try:
                sent = await self._send_with_governance(message.channel, reply[:2000], corr_id=corr_id)
                if sent:
                    print(f"[gateway] Outbound sent.", file=sys.stderr, flush=True)
            except discord.HTTPException as e:
                print(f"[gateway] Discord send failed: {e}", file=sys.stderr, flush=True)
                await self._send_with_governance(message.channel, (reply[:2000] or SAFE_OFFLINE_MSG)[:1900] + "...", corr_id=corr_id)
        except Exception as e:
            import sys
            print(f"[gateway] on_message error: {e}", file=sys.stderr, flush=True)
            try:
                await self._send_with_governance(message.channel, "Station error. Check logs.", corr_id=corr_id)
            except Exception:
                pass

    async def run(self) -> None:
        if discord is None:
            raise ImportError("discord.py not installed. pip install discord.py")
        if not httpx:
            raise ImportError("httpx not installed. pip install httpx")

        token = os.environ.get(self.token_env)
        if not token:
            raise ValueError(f"Discord bot token not found in env var: {self.token_env}")

        intents = discord.Intents.default()
        intents.message_content = True

        self.client = discord.Client(intents=intents)

        @self.client.event
        async def on_ready():
            import sys
            self._emit_identity()
            msg = f"Calyx Discord Gateway logged in as {self.client.user} (governance_required={self.governance_required})"
            print(msg, file=sys.stderr, flush=True)
            if self._heartbeat_push_enabled and self._heartbeat_user_id and self._heartbeat_interval_min > 0 and self._heartbeat_push_destination != "OFF":
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                print(f"[gateway] Heartbeat enabled: every {self._heartbeat_interval_min} min to user {self._heartbeat_user_id}", file=sys.stderr, flush=True)
            else:
                print(f"[gateway] Heartbeat disabled (CALYX_HEARTBEAT_PUSH_ENABLED={self._heartbeat_push_enabled}, DESTINATION={self._heartbeat_push_destination})", file=sys.stderr, flush=True)
            asyncio.create_task(self._outbox_loop())
            asyncio.create_task(self._process_outbox())

        @self.client.event
        async def on_message(msg):
            await self._on_message(msg)

        await self.client.start(token)


def main() -> None:
    """CLI entry point. Config: CLI args > env > DISCORD_IDS.md."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Calyx Discord Gateway — governed Discord → CBO relay")
    parser.add_argument("--cbo-base", default=DEFAULT_CBO_BASE, help="CBO Core base URL")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SEC, help="CBO request timeout (seconds)")
    parser.add_argument("--no-governance-required", action="store_true", help="Allow fallback when CBO down")
    parser.add_argument("--model-role", default="local", help="CBO model_role: none, local, workhorse, architect, second_opinion")
    parser.add_argument("--channel-allowlist", nargs="*", default=[], help="Channel IDs to allow (deny-by-default if empty)")
    parser.add_argument("--authorized-users", nargs="*", default=[], help="User IDs for DM (deny-by-default if empty)")
    args = parser.parse_args()

    cli_channels = args.channel_allowlist if args.channel_allowlist else None
    cli_users = args.authorized_users if args.authorized_users else None
    channels, users = _resolve_config(cli_channels, cli_users)

    model_role = os.environ.get("CBO_DISCORD_MODEL_ROLE") or args.model_role
    governance = not args.no_governance_required

    if governance and (not channels and not users):
        msg = (
            "gateway.config.invalid: governance_required but allowlists empty. "
            "Set DISCORD_CHANNEL_ALLOWLIST and/or DISCORD_AUTHORIZED_USERS, or pass --channel-allowlist and --authorized-users."
        )
        print(msg, file=sys.stderr, flush=True)
        _emit("gateway.config.invalid", msg, level="ERROR", data={"governance_required": True})
        sys.exit(2)

    gateway = CalyxDiscordGateway(
        cbo_base=args.cbo_base,
        timeout_sec=args.timeout,
        governance_required=governance,
        model_role=model_role,
        channel_allowlist=channels,
        authorized_user_ids=users,
    )
    asyncio.run(gateway.run())


if __name__ == "__main__":
    main()
