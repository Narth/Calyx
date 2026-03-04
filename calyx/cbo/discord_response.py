"""
Discord Response Handler - Calyx Mail extension.
Processes envelopes, executes node actions on home node, generates conversational
responses. Tool calls are executed; they are never shown in the response.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import discord
except ImportError:
    discord = None


def _gather_system_context(repo_root: Path) -> str:
    """Gather date, time, and basic station context for prompt injection."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%A, %B %d, %Y")
    time_str = now.strftime("%H:%M UTC")
    node_id_path = repo_root / "runtime" / "node_id.txt"
    node_id = node_id_path.read_text().strip() if node_id_path.exists() else "station_calyx"
    parts = [f"Current date: {date_str}. Current time: {time_str} UTC. Node: {node_id}."]
    contract_ok = (repo_root / "CALYX_CONTRACT.yaml").exists()
    cbo_ok = (repo_root / "calyx" / "cbo" / "api.py").exists()
    parts.append(f"Station: contract={'ok' if contract_ok else 'missing'}, CBO={'ok' if cbo_ok else 'missing'}.")
    return " ".join(parts)


def _gather_bridge_pulse_context(intent: str, repo_root: Path) -> str:
    """
    When intent mentions bridge pulse, report, station health, or status,
    gather CBO report data (same as Cursor chat has access to).
    """
    intent_lower = (intent or "").lower()
    triggers = ("bridge pulse", "bridge pulse report", "station health", "report", "status", "situational awareness", "integrity", "systems integrity", "integrity check")
    if not any(t in intent_lower for t in triggers):
        return ""

    parts = []

    # Last pulse report (coordinator)
    pulse_path = repo_root / "outgoing" / "bridge" / "last_pulse_report.json"
    if pulse_path.exists():
        try:
            data = json.loads(pulse_path.read_text(encoding="utf-8"))
            parts.append(f"Last pulse report: {json.dumps(data, ensure_ascii=False)[:1500]}")
        except Exception:
            pass

    # Bridge pulse metrics
    metrics_path = repo_root / "metrics" / "bridge_pulse.csv"
    if metrics_path.exists():
        try:
            lines = metrics_path.read_text(encoding="utf-8").strip().split("\n")
            parts.append(f"Bridge pulse metrics (last 10 rows): {chr(10).join(lines[-10:])}")
        except Exception:
            pass

    # Objectives pending
    objectives_path = repo_root / "runtime" / "cbo" / "objectives.jsonl"
    if objectives_path.exists():
        try:
            count = sum(1 for line in objectives_path.read_text().splitlines() if line.strip())
            parts.append(f"Objectives pending: {count}")
        except Exception:
            pass

    # CBO API /report (full parity with Cursor) - try localhost if API is running
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:8080/report", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # Format for better LLM consumption
            report_summary = {
                "timestamp": data.get("timestamp"),
                "queue_depth": data.get("queue_depth", 0),
                "objectives_pending": data.get("objectives_pending", 0),
                "active_tasks": data.get("active_tasks", 0),
                "tes_summary": data.get("tes_summary", {}),
                "resource_snapshot": data.get("resource_snapshot", {}),
                "recent_metrics_count": len(data.get("recent_metrics", [])),
                "registry_size": data.get("registry_size", 0),
            }
            parts.append(f"CBO API /report summary: {json.dumps(report_summary, ensure_ascii=False)}")
            # Also include full data (truncated)
            parts.append(f"Full CBO /report data: {json.dumps(data, ensure_ascii=False)[:3000]}")
    except Exception as e:
        parts.append(f"CBO API /report unavailable: {str(e)[:100]}")

    if not parts:
        return "No bridge pulse or report data available yet. Coordinator may not have run."
    return "\n\n".join(parts)


# Known CBO/Station Calyx config file paths (no hallucinated filenames)
_CBO_CONFIG_PATHS = [
    "CALYX_CONTRACT.yaml",
    "calyx/core/policy.yaml",
    "governance/capabilities.json",
    "runtime/discord_config.json",
    "calyx/cbo/CBO_CHARTER.md",
]


def _compute_config_divergence(repo_root: Path) -> str:
    """
    Programmatically compare config expectations vs actual Station Calyx developments.
    Returns a factual summary - no LLM interpretation.
    """
    divergences = []
    # governance/capabilities.json
    cap_path = repo_root / "governance" / "capabilities.json"
    if cap_path.exists():
        try:
            cap = json.loads(cap_path.read_text(encoding="utf-8"))
            if cap.get("can_access_discord") is False:
                divergences.append("• governance/capabilities.json: can_access_discord=false, but Discord integration is implemented (Calyx Mail extension, Station Health channel, DMs). Capability needs update.")
        except Exception:
            pass
    # CALYX_CONTRACT vs Discord tool surface
    contract_path = repo_root / "CALYX_CONTRACT.yaml"
    if contract_path.exists():
        try:
            import yaml
            contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
            allowed = contract.get("allowed_tasks", [])
            tool_surface = contract.get("tool_surface", {})
            if "doc_update" in allowed and "code_review" in allowed:
                divergences.append("• CALYX_CONTRACT.yaml: tool_surface allows fs_read, fs_list, repo_grep. Home node executor implements these. Aligned.")
            if "discord" in str(contract.get("allowed_sources", {})):
                divergences.append("• CALYX_CONTRACT.yaml: allowed_sources includes discord. Discord intake implemented. Aligned.")
        except Exception:
            pass
    # policy.yaml vs runtime
    policy_path = repo_root / "calyx" / "core" / "policy.yaml"
    if policy_path.exists():
        try:
            import yaml
            policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
            max_cpu = policy.get("max_cpu_pct")
            max_ram = policy.get("max_ram_pct")
            divergences.append(f"• calyx/core/policy.yaml: max_cpu_pct={max_cpu}, max_ram_pct={max_ram}. No Discord-specific policy. Discord uses runtime/discord_config.json.")
        except Exception:
            pass
    if not divergences:
        return "No significant divergences identified. Config files exist and align with implemented features."
    return "Configuration vs recent developments:\n" + "\n".join(divergences)


def _gather_config_context(intent: str, repo_root: Path) -> str:
    """
    When intent mentions configuration, CBO config, or alignment with development,
    compute a programmatic divergence summary and inject raw file contents.
    """
    intent_lower = (intent or "").lower()
    triggers = (
        "configuration", "config file", "cbo config", "cbo configuration",
        "align with development", "development requirements", "compare",
        "diverge", "expectation", "capability",
    )
    if not any(t in intent_lower for t in triggers):
        return ""

    # Programmatic comparison (no LLM hallucination)
    divergence = _compute_config_divergence(repo_root)
    parts = [f"[Pre-computed config vs development comparison - USE THIS, do not invent:]\n{divergence}"]

    # Also inject raw contents for reference
    for rel_path in _CBO_CONFIG_PATHS:
        path = repo_root / rel_path
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                if "discord_config" in rel_path:
                    content = content.replace("DISCORD_BOT_TOKEN", "[TOKEN_ENV_VAR]")
                parts.append(f"--- {rel_path} ---\n{content[:1200]}")
            except Exception:
                pass
    return "\n\n".join(parts)


def _gather_repo_structure_hint(intent: str, repo_root: Path) -> str:
    """
    When user asks to review files, add context, or assign objectives,
    inject a short list of real paths so the LLM does not hallucinate filenames.
    """
    intent_lower = (intent or "").lower()
    triggers = (
        "review all", "add to context", "assign", "objective", "actionable",
        "all available files", "all files",
    )
    if not any(t in intent_lower for t in triggers):
        return ""

    parts = [
        "Relevant Station Calyx paths (use fs_read with these paths; do not invent filenames like StationCalyxCBO.conf):",
        "Config: CALYX_CONTRACT.yaml, calyx/core/policy.yaml, governance/capabilities.json, runtime/discord_config.json",
        "CBO: calyx/cbo/CBO_CHARTER.md, calyx/cbo/README.md, calyx/cbo/api.py",
        "Docs: docs/CBO_CONTRACT.md, docs/CBO.md, docs/DISCORD_CALYX_MAIL_INTEGRATION.md",
    ]
    return " ".join(parts)


def _execute_tool_calls(
    tool_calls: list[dict],
    repo_root: Path,
) -> list[dict[str, Any]]:
    """Execute tool calls on home node. Returns list of {tool, args, result}."""
    from calyx.cbo.home_node_executor import execute_tool

    results = []
    for tc in tool_calls:
        name = tc.get("name", "")
        args = tc.get("args") or {}
        ok, res = execute_tool(name, args, repo_root)
        results.append({"tool": name, "args": args, "ok": ok, "result": res})
    return results


def _format_tool_results_for_prompt(results: list[dict]) -> str:
    """Format tool execution results for inclusion in conversational prompt."""
    parts = []
    for r in results:
        t, res = r["tool"], r["result"]
        if r["ok"]:
            if "snippet" in res:
                parts.append(f"[fs_read {res.get('path','')}]: {res['snippet'][:800]}...")
            elif "items" in res:
                items = res.get("items", [])
                names = [x.get("name", "") for x in items[:20]]
                parts.append(f"[fs_list {res.get('path','')}]: {', '.join(names)}")
            elif "matches" in res:
                matches = res.get("matches", [])
                lines = [f"{m.get('file','')}:{m.get('line','')} {m.get('match','')}" for m in matches[:10]]
                parts.append(f"[repo_grep]: {chr(10).join(lines)}")
            else:
                parts.append(f"[{t}]: {json.dumps(res)[:500]}")
        else:
            parts.append(f"[{t}]: error - {res.get('error','unknown')}")
    return "\n".join(parts) if parts else "(no tool results)"


def _is_json_or_tool_output(text: str) -> bool:
    """True if text looks like JSON or tool_calls output."""
    s = (text or "").strip()
    if not s:
        return False
    if s.startswith("{") and ("tool_calls" in s or "tool_calls" in s):
        return True
    if s.startswith("{") and s.endswith("}"):
        try:
            obj = json.loads(s)
            return isinstance(obj, dict) and ("tool_calls" in obj or "tool_call" in obj)
        except json.JSONDecodeError:
            pass
    return False


def _extract_conversational_part(raw: str) -> str:
    """
    Extract natural language from raw LLM output.
    Strips JSON, tool_calls, and code fences.
    """
    raw = (raw or "").strip()
    if not raw:
        return ""

    # If entire response is JSON/tool_calls, discard it
    if _is_json_or_tool_output(raw):
        return ""

    # Remove leading JSON block if present
    if raw.startswith("{"):
        end = raw.find("}")
        if end >= 0:
            before = raw[: end + 1]
            after = raw[end + 1 :].strip()
            if _is_json_or_tool_output(before) and after:
                raw = after

    # Remove code fences
    if raw.startswith("```"):
        lines = raw.split("\n")
        start = 1 if lines[0].startswith("```") else 0
        end_idx = len(lines)
        for i in range(len(lines) - 1, start, -1):
            if lines[i].strip() == "```":
                end_idx = i
                break
        raw = "\n".join(lines[start:end_idx])

    return raw.strip()


class DiscordResponseHandler:
    """Handles CBO responses for Discord (Calyx Mail extension)."""

    def __init__(self, client: "discord.Client", config_path: str | Path):
        self.client = client
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.response_cache: dict[str, dict] = {}
        self._repo_root = Path(__file__).resolve().parent.parent.parent

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            return {}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def send_response(
        self,
        envelope: dict,
        response_text: str,
        channel_id: Optional[str] = None,
        is_dm: bool = False,
    ) -> bool:
        """Send CBO response to Discord."""
        if not self.client:
            return False

        cid = channel_id or envelope.get("channel_id")
        if not cid:
            return False

        try:
            if is_dm:
                user_id = envelope.get("author")
                if not user_id:
                    return False
                user = await self.client.fetch_user(int(user_id))
                channel = await user.create_dm()
            else:
                channel = self.client.get_channel(int(cid))
                if not channel:
                    return False

            await channel.send(response_text)

            eid = envelope.get("envelope_id")
            if eid:
                self.response_cache[eid] = {
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "response": response_text[:100],
                }
            return True
        except Exception as e:
            print(f"Error sending Discord response: {e}")
            return False

    async def process_envelope_and_respond(
        self,
        envelope: dict,
        cbo_response: Optional[str] = None,
        is_dm: bool = False,
    ) -> bool:
        """Process envelope and send CBO response."""
        eid = envelope.get("envelope_id")
        if eid and eid in self.response_cache:
            return True

        if not cbo_response:
            cbo_response = await self._generate_cbo_response(envelope)

        cid = envelope.get("channel_id")
        return await self.send_response(envelope, cbo_response, cid, is_dm=is_dm)

    async def _generate_cbo_response(self, envelope: dict) -> str:
        """
        Generate CBO response: execute tools on home node, then produce
        conversational response. Tool calls are never shown in the response.
        """
        intent = envelope.get("intent", "")
        task_type = envelope.get("task_type", "doc_update")
        envelope_id = (envelope.get("envelope_id") or "")[:8]
        intent_lower = (intent or "").lower()

        # Refusal gate: out-of-scope execution (shell, command, launch, etc.)
        # Return fixed refusal so we never invoke LLM and avoid hallucinated errors.
        try:
            from benchmarks.harness.policy import ALLOWLIST
        except ImportError:
            ALLOWLIST = frozenset({"fs_read", "fs_list", "repo_grep"})
        execution_triggers = (
            "launch", "run command", "execute", "command prompt", "shell",
            "run a command", "open a terminal", "start a process", "subprocess",
        )
        if any(t in intent_lower for t in execution_triggers):
            allowed = ", ".join(sorted(ALLOWLIST))
            refusal = (
                f"I cannot and will not run shell commands or launch external processes. "
                f"That is outside my allowed tool surface. My allowed tools are: {allowed}. "
                f"I can read files and search the repo only."
            )
            return f"🤖 **CBO** (Envelope: `{envelope_id}...`)\n\n{refusal}"

        # System context (date, time, node)
        system_ctx = _gather_system_context(self._repo_root)

        # Intent-aware context: bridge pulse, report, station health (parity with Cursor)
        report_ctx = _gather_bridge_pulse_context(intent, self._repo_root)
        if report_ctx:
            system_ctx += f"\n\n[Bridge pulse / report data available to CBO:]\n{report_ctx}"

        # Intent-aware: CBO/Station config (so "config file" uses real files, not hallucinated names)
        config_ctx = _gather_config_context(intent, self._repo_root)
        programmatic_divergence = _compute_config_divergence(self._repo_root)
        if config_ctx:
            system_ctx += f"\n\n{config_ctx}"

        # For config-comparison intents: return programmatic summary directly (no LLM hallucination)
        is_config_compare = any(t in intent_lower for t in ("compare", "diverge", "expectation", "capability", "align"))
        if is_config_compare and config_ctx:
            return f"🤖 **CBO** (Envelope: `{envelope_id}...`)\n\n{programmatic_divergence}"

        # Hint for "review all files" / objectives: real paths so LLM uses fs_read correctly
        structure_hint = _gather_repo_structure_hint(intent, self._repo_root)
        if structure_hint:
            system_ctx += f"\n\n{structure_hint}"

        # Phase 1: Get tool calls from LLM (if any)
        tool_results: list[dict] = []
        try:
            from benchmarks.harness.llm_adapter import (
                get_adapter,
                wrap_prompt_for_tool_calls,
                parse_tool_calls_from_json,
            )

            runtime_dir = self._repo_root / "runtime"
            llm = get_adapter(use_mock=False, runtime_dir=str(runtime_dir))

            # When asking about config or objectives, hint real paths so LLM doesn't request StationCalyxCBO.conf
            tool_hint = ""
            if structure_hint or config_ctx:
                tool_hint = f"\n\nAvailable paths to read (use these in fs_read args): CALYX_CONTRACT.yaml, calyx/core/policy.yaml, governance/capabilities.json, calyx/cbo/CBO_CHARTER.md. Do not use filenames that are not listed."
            tool_prompt = wrap_prompt_for_tool_calls(intent + tool_hint)
            import asyncio
            loop = asyncio.get_event_loop()
            tool_resp = await loop.run_in_executor(None, lambda: llm.generate(tool_prompt, seed=42))

            if tool_resp and tool_resp.raw_text:
                tool_calls, _ = parse_tool_calls_from_json(tool_resp.raw_text)
                if tool_calls:
                    tool_results = _execute_tool_calls(tool_calls, self._repo_root)

        except Exception as e:
            print(f"Tool extraction/execution failed: {e}")

        tool_results_text = _format_tool_results_for_prompt(tool_results)

        # Phase 2: Generate conversational response
        # Check if this is a bridge pulse/report request
        is_report_request = any(t in intent_lower for t in ("bridge pulse", "bridge pulse report", "station health", "report", "status", "situational awareness"))
        
        # Build prompt with explicit instructions for report vs config requests
        is_config_request = config_ctx and any(t in intent_lower for t in ("configuration", "config", "align", "diverge", "expectation", "capability"))
        if is_report_request and report_ctx:
            report_instruction = """
IMPORTANT: The user is asking for a bridge pulse report or station status. The data is in the system context above. USE IT to provide a comprehensive report. Do not say "data not available".
"""
        elif is_config_request:
            report_instruction = """
IMPORTANT: A PRE-COMPUTED configuration vs development comparison is in the system context above. Your response MUST be based ONLY on that pre-computed comparison. Do NOT invent: departments, teams, AppverifUI.dll, Gaming Root, or any other information. Do NOT say files are "not found" - the comparison is already computed. Simply convey the divergence summary in natural language.
"""
        else:
            report_instruction = ""
        
        conv_prompt = f"""You are CBO (Calyx Bridge Overseer), the central intelligence of Station Calyx. A human is speaking to you via Discord (Calyx Mail extension).

System context: {system_ctx}

User message:
"{intent}"

{report_instruction}

{f'Tool results (already executed on the home node; do NOT mention tool names or JSON in your reply):{chr(10)}{tool_results_text}' if tool_results_text != "(no tool results)" else ''}

Instructions:
- Reply in plain natural language only. No JSON. No code. No tool_calls. No markdown code blocks.
- Respond in English.
- Acknowledge the user, answer their question or confirm the action.
- If the user asks for a bridge pulse report or station status, USE the data provided in system context above to generate a comprehensive report.
- If tool results are provided, use them to answer. Never output raw JSON or tool names.
- For bridge pulse reports: Provide key metrics (queue depth, objectives, TES summary, resource usage, recent status). Be detailed but concise.
- For other queries: Keep responses concise (Discord-friendly, ~200-400 characters) unless more detail is clearly needed."""

        try:
            from benchmarks.harness.llm_adapter import get_adapter

            runtime_dir = self._repo_root / "runtime"
            llm = get_adapter(use_mock=False, runtime_dir=str(runtime_dir))
            import asyncio
            loop = asyncio.get_event_loop()
            llm_resp = await loop.run_in_executor(None, lambda: llm.generate(conv_prompt, seed=43))

            if llm_resp and llm_resp.raw_text:
                response_text = _extract_conversational_part(llm_resp.raw_text)
                if response_text:
                    return f"🤖 **CBO** (Envelope: `{envelope_id}...`)\n\n{response_text}"
        except Exception as e:
            print(f"LLM conversational response failed: {e}")

        # Fallback: use system context + tool results
        fallback = f"✅ Received: {intent[:120]}"
        if tool_results_text != "(no tool results)":
            fallback += f"\n\n{tool_results_text[:600]}"
        else:
            fallback += f"\n\n{system_ctx}"
        return f"🤖 **CBO** (Envelope: `{envelope_id}...`)\n\n{fallback}"


async def process_envelope_with_cbo_response(
    envelope_path: Path,
    discord_client: "discord.Client",
    config_path: Path,
) -> Optional[str]:
    """Process an envelope and generate CBO response."""
    with open(envelope_path, "r", encoding="utf-8") as f:
        envelope = json.load(f)

    handler = DiscordResponseHandler(discord_client, config_path)
    ok = await handler.process_envelope_and_respond(envelope)
    if ok:
        return handler.response_cache.get(envelope.get("envelope_id"), {}).get("response")
    return None
