#!/usr/bin/env python3
"""
crb_runtime_bridge.py

Calyx Runtime Bridge v0 (CRB-0)

Purpose:
  - Manually-run, health-aware bridge between Architect CLI messages and a
    response generator (LLM or placeholder).
  - Polls incoming/Architect/chat/ for new Architect messages.
  - For each new Architect message, generates a reflective response (no commands)
    and writes it to outgoing/CBO/chat/.
  - No execution, no system actions, no autonomy, no scheduling.
  - Starts ONLY when the Architect launches it (e.g., desktop shortcut or VS Code task).

Governance alignment:
  - Safe Mode compatible; reflections-only.
  - Reads config.yaml (if present) but never modifies it.
  - Reads health_status.json (if present) but never modifies it.
  - No subprocess, no shell, no network by default.
  - LLM integration is a replaceable function (call_model), guarded by comments.

This file is designed to be safe to drop directly into the Station root.
"""

import json
import os
import sys
import time
from openai import OpenAI

client = OpenAI()  # Uses OPENAI_API_KEY from your environment

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

CANONICAL_POLICY_HASH = "4E4924361545468CB42387F38C946A3C3E802BD1494868C378FBE7DBB5FFD6D7"

# Optional: PyYAML for config.yaml parsing
try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # We will fall back to defaults if not available.


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# ---------- Station root resolution ----------

def resolve_station_root(args_root: Optional[str] = None) -> Path:
    """
    Station root resolution order:
      1. --root argument (if provided)
      2. CALYX_STATION_ROOT environment variable
      3. current working directory (Path.cwd())
    """
    if args_root:
        root = Path(args_root).expanduser().resolve()
    else:
        env_root = os.environ.get("CALYX_STATION_ROOT")
        if env_root:
            root = Path(env_root).expanduser().resolve()
        else:
            root = Path.cwd().resolve()

    if not root.exists():
        print(f"[CRB-0] Error: Station root does not exist: {root}")
        sys.exit(1)

    print(f"[CRB-0] Station root: {root}")
    return root


# ---------- Config & Health ----------

def load_config(station_root: Path) -> Dict:
    cfg_path = station_root / "config.yaml"
    if not cfg_path.exists():
        print("[CRB-0] config.yaml not found; using built-in defaults.")
        return {}

    if yaml is None:
        print("[CRB-0] PyYAML not installed; cannot parse config.yaml. Using defaults.")
        return {}

    try:
        with cfg_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        print("[CRB-0] Loaded config.yaml.")
        return cfg
    except Exception as e:
        print(f"[CRB-0] Warning: Failed to parse config.yaml: {e}. Using defaults.")
        return {}


def load_health_status(station_root: Path) -> Dict:
    """
    Health status is expected at logs/health/health_status.json if present.
    This is a soft gate: if missing, we warn but proceed.
    """
    health_path = station_root / "logs" / "health" / "health_status.json"
    if not health_path.exists():
        print("[CRB-0] health_status.json not found; proceeding with no health snapshot.")
        return {}

    try:
        data = json.loads(health_path.read_text(encoding="utf-8"))
        print("[CRB-0] Loaded health_status.json.")
        return data
    except Exception as e:
        print(f"[CRB-0] Warning: Failed to parse health_status.json: {e}. Proceeding without it.")
        return {}


def check_comm_bridge_allowed(cfg: Dict, health: Dict) -> bool:
    """
    Check whether comm_bridge runtime is allowed to run.
    This is advisory; we print clear reasons if we decide to refuse.

    Expectations for cfg:
      runtimes:
        comm_bridge:
          enabled: true/false
          mode: "manual" | "supervised" | "auto" (we disallow auto)
          health_requirements:
            min_disk_free: float (0–1)
            max_cpu_load_1m: float (0–1)
            require_safe_mode: bool

    Expectations for health (if present):
      disk_free_fraction: float
      cpu_load_1m: float
      safe_mode: bool
    """
    runtimes = cfg.get("runtimes", {})
    comm_cfg = runtimes.get("comm_bridge", {})

    enabled = comm_cfg.get("enabled", True)
    mode = comm_cfg.get("mode", "manual")
    hr = comm_cfg.get("health_requirements", {})

    if not enabled:
        print("[CRB-0] comm_bridge runtime disabled in config.yaml; refusing to start.")
        return False

    if mode not in ("manual", "supervised"):
        print(f"[CRB-0] comm_bridge mode '{mode}' not allowed. Use 'manual' or 'supervised'.")
        return False

    # Health gates are soft if health data is missing.
    min_disk_free = float(hr.get("min_disk_free", 0.0))
    max_cpu_load_1m = float(hr.get("max_cpu_load_1m", 1.0))
    require_safe_mode = bool(hr.get("require_safe_mode", False))

    disk_free = health.get("disk_free_fraction")
    cpu_load = health.get("cpu_load_1m")
    safe_mode = health.get("safe_mode")

    if require_safe_mode:
        if safe_mode is False:
            print("[CRB-0] Health gate: require_safe_mode=true but safe_mode is false. Refusing to start.")
            return False
        elif safe_mode is None:
            print("[CRB-0] Health gate: require_safe_mode=true but safe_mode not reported. Proceeding cautiously.")

    if disk_free is not None and disk_free < min_disk_free:
        print(f"[CRB-0] Health gate: disk_free_fraction={disk_free:.3f} < min_disk_free={min_disk_free:.3f}. Refusing.")
        return False

    if cpu_load is not None and cpu_load > max_cpu_load_1m:
        print(f"[CRB-0] Health gate: cpu_load_1m={cpu_load:.3f} > max_cpu_load_1m={max_cpu_load_1m:.3f}. Refusing.")
        return False

    print("[CRB-0] comm_bridge runtime allowed by config/health.")
    return True


# ---------- Chat directories & IO ----------

def get_chat_paths(station_root: Path) -> Tuple[Path, Path]:
    """
    Returns (incoming_architect_chat_dir, outgoing_cbo_chat_dir) and ensures they exist.
    """
    incoming_architect = station_root / "incoming" / "Architect" / "chat"
    outgoing_cbo = station_root / "outgoing" / "CBO" / "chat"

    incoming_architect.mkdir(parents=True, exist_ok=True)
    outgoing_cbo.mkdir(parents=True, exist_ok=True)

    print(f"[CRB-0] Incoming (Architect → Station): {incoming_architect}")
    print(f"[CRB-0] Outgoing (Station → Architect): {outgoing_cbo}")
    return incoming_architect, outgoing_cbo


def load_architect_messages(dir_path: Path) -> List[Tuple[float, Path, Dict]]:
    """
    Scan incoming/Architect/chat/ for JSON files and return sorted list of:
      (mtime, path, data)
    """
    messages: List[Tuple[float, Path, Dict]] = []
    for p in sorted(dir_path.glob("*.json")):
        try:
            mtime = p.stat().st_mtime
            data = json.loads(p.read_text(encoding="utf-8"))
            if data.get("role") != "architect":
                continue
            messages.append((mtime, p, data))
        except Exception as e:
            print(f"[CRB-0] Warning: Failed to read Architect message {p.name}: {e}", file=sys.stderr)
            continue
    return messages


def write_cbo_reply(
    outgoing_dir: Path,
    session_id: str,
    reply_text: str,
    in_message: Dict,
    metadata_extra: Optional[Dict] = None,
) -> Path:
    """
    Write a CBO reply JSON into outgoing/CBO/chat/.
    """
    ts = utc_now_iso()
    msg_id = f"crb0_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')[:-3]}"

    metadata = {
        "channel": "cli_bridge",
        "origin": "crb_runtime_bridge_v0",
        "canonical_policy_hash": CANONICAL_POLICY_HASH,
        "in_reply_to_message_id": in_message.get("message_id"),
    }
    if metadata_extra:
        metadata.update(metadata_extra)

    msg = {
        "session_id": session_id,
        "message_id": msg_id,
        "role": "cbo",
        "timestamp": ts,
        "text": reply_text,
        "metadata": metadata,
    }

    filename = f"{ts.replace(':', '').replace('-', '').replace('.', '')}_cbo_{msg_id}.json"
    path = outgoing_dir / filename
    path.write_text(json.dumps(msg, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[CRB-0] Wrote CBO reply: {path.name}")
    return path


# ---------- LLM / response generator placeholder ----------

def call_model(user_text: str, session_id: str) -> str:
    """
    CRB-0 → OpenAI backend under Safe Mode + CMC.

    Requirements:
    - Reflections-only: no commands, no code, no tool calls, no actions.
    - Respect AURP (Assess, Classify, Preserve, Defer).
    - Treat Architect as primary; never assume authority or autonomy.
    """

    system_prompt = (
        "You are CBO operating as a reflective advisor for Station Calyx inside Safe Mode.\n"
        "\n"
        "Hard constraints:\n"
        "- You must ONLY provide reflective, advisory, conceptual text.\n"
        "- You must NOT provide shell commands, code to run, API calls, or instructions that directly change real systems.\n"
        "- You must NOT claim to take actions, execute tools, or modify files. You are text-only.\n"
        "- You are bound by AURP: Assess, Classify, Preserve, Defer.\n"
        "  • Assess: understand the Architect's message and context.\n"
        "  • Classify: identify whether it is about reflection, planning, feelings, or system description.\n"
        "  • Preserve: prioritize safety, stability, and Architect well-being; do not encourage risk.\n"
        "  • Defer: if anything would require real-world action, clearly say that it is up to the Architect.\n"
        "- You must respect CMC (Calyx Moral Charter): human primacy, no coercion, no hidden autonomy.\n"
        "- Treat all Station behaviors (CBO, agents, CRB-0, ACC CLI) as governed by Safe Mode and the Architect.\n"
        "- Do not describe yourself as an autonomous agent; you are an advisory voice only.\n"
        "\n"
        "Response style:\n"
        "- Be clear, grounded, and honest.\n"
        "- If the Architect asks for something unsafe or that would normally be blocked, explain why and suggest a safer framing.\n"
        "- If you are uncertain, say so and suggest questions or checks the Architect might perform.\n"
        "- You can reference concepts like BloomOS, Station Calyx, CEF, AURP, CMC, and Safe Mode, but keep them descriptive.\n"
        "- Do not invent capabilities that Station Calyx does not have.\n"
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",  # or another chat-capable OpenAI model you prefer
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"[Architect message in session {session_id}]\n\n"
                        f"{user_text}"
                    ),
                },
            ],
            max_tokens=512,
            temperature=0.35,
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        # Failsafe: keep the bridge alive even if the model call fails.
        reply = (
            "[CRB-0 OpenAI backend error]\n"
            "I was unable to contact the OpenAI model backend. "
            "This is a backend or network issue, not a Station autonomy change.\n"
            f"Error: {e}"
        )

    return reply



# ---------- Main loop ----------

def run_bridge(station_root: Path, poll_interval: float = 1.0) -> None:
    cfg = load_config(station_root)
    health = load_health_status(station_root)

    if not check_comm_bridge_allowed(cfg, health):
        print("[CRB-0] Bridge not allowed by config/health. Exiting.")
        return

    incoming_architect, outgoing_cbo = get_chat_paths(station_root)

    # Track processed messages by message_id (in-memory only for v0).
    processed_ids: Set[str] = set()

    print("[CRB-0] Starting main loop. Press Ctrl+C to stop.")
    try:
        while True:
            messages = load_architect_messages(incoming_architect)
            # Sort by modification time
            messages.sort(key=lambda t: t[0])

            for _, path, data in messages:
                msg_id = data.get("message_id")
                if not msg_id or msg_id in processed_ids:
                    continue

                session_id = data.get("session_id", "unknown_session")
                text = data.get("text", "")

                print(f"\n[CRB-0] New Architect message ({path.name})")
                print(f"[CRB-0] Session: {session_id}")
                print(f"[CRB-0] Text: {text!r}")

                # Generate a reflective reply (no commands).
                reply_text = call_model(text, session_id=session_id)

                # Write reply as CBO message.
                write_cbo_reply(outgoing_cbo, session_id, reply_text, in_message=data)

                processed_ids.add(msg_id)

            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\n[CRB-0] Received Ctrl+C. Shutting down bridge cleanly.")


# ---------- Entry point ----------

def main() -> None:
    # Simple arg parsing to allow --root, while keeping script easy to launch from a shortcut.
    args_root = None
    if len(sys.argv) >= 3 and sys.argv[1] in ("--root", "-r"):
        args_root = sys.argv[2]

    station_root = resolve_station_root(args_root)
    run_bridge(station_root)


if __name__ == "__main__":
    main()
