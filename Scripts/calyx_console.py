# Calyx Console v1.1 (Windows-friendly prompt)
import os
import sys
import argparse
import yaml
import datetime
import subprocess
import shlex
import pathlib
import shutil

# --- UTF-8 safe I/O + simple ASCII prompt
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
except Exception:
    pass

PROMPT = "Calyx> "

ROOT = pathlib.Path(__file__).resolve().parents[0].parents[0]  # ...\Calyx_Terminal
CONFIG_PATH = ROOT / "config.yaml"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def record_session_start(cfg, source="manual", transcript=None):
    journal_dir = pathlib.Path(cfg["paths"]["journal"])
    journal_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir = journal_dir / "Sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.datetime.now()
    slug = ts.strftime("%Y-%m-%d_%H%M%S")
    session_path = sessions_dir / f"{slug}_session.md"

    lines = [
        f"# Session {ts.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"- Source: {source}",
        f"- Created: {ts.strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    if transcript:
        lines.append(f"- Trigger: {transcript}")
    lines.extend(["", "## Notes", ""])
    session_path.write_text("\n".join(lines), encoding="utf-8")

    daily_path = journal_dir / f"{ts.strftime('%Y-%m-%d')}.md"
    if not daily_path.exists():
        daily_path.write_text(f"# {ts.strftime('%Y-%m-%d')} - Notes\n\n", encoding="utf-8")
    with open(daily_path, "a", encoding="utf-8") as f:
        f.write(f"- [{ts.strftime('%H:%M:%S')}] Session started ({source})\n")
        if transcript:
            f.write(f"  - Trigger: {transcript}\n")

    return session_path


def begin_session(cfg, source="manual", transcript=None):
    codex = cfg["paths"]["codex"]
    session_log = record_session_start(cfg, source=source, transcript=transcript)

    obsidian_path = shutil.which("obsidian")
    if obsidian_path:
        subprocess.Popen([obsidian_path, codex])
        print("[Calyx] Session begun. Codex opened in Obsidian.")
    else:
        os.startfile(codex)
        print("[Calyx] Session begun. Codex folder opened.")

    try:
        os.startfile(str(session_log))
    except Exception:
        pass
    print(f"[Calyx] Session log -> {session_log}")


def list_projects(cfg):
    proj_root = pathlib.Path(cfg["paths"]["projects"])
    proj_root.mkdir(parents=True, exist_ok=True)
    names = [p.name for p in proj_root.iterdir() if p.is_dir()]
    if names:
        print("[Calyx] Projects:", ", ".join(names))
    else:
        print("[Calyx] No projects found in", proj_root)


def summon(cfg, project_name):
    proj_root = pathlib.Path(cfg["paths"]["projects"])
    proj_root.mkdir(parents=True, exist_ok=True)
    dirs = [p for p in proj_root.iterdir() if p.is_dir()]
    matches = [p for p in dirs if project_name.lower() in p.name.lower()]
    if matches:
        os.startfile(str(matches[0]))
        print(f"[Calyx] Summoned project: {matches[0].name}")
    else:
        print("[Calyx] No matching project found.")
        print("[Calyx] Available projects:", ", ".join(p.name for p in dirs) or "(none)")


def log_reflection(cfg, text=None):
    journal_dir = pathlib.Path(cfg["paths"]["journal"])
    journal_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    path = journal_dir / f"{today}.md"
    if not path.exists():
        path.write_text(f"# {today} - Reflection\n\n", encoding="utf-8")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"- {text or '(empty entry)'}\n")
    os.startfile(str(path))
    print(f"[Calyx] Logged reflection -> {path}")


def create_journal_entry(cfg):
    """Create a new journal entry and open it for editing"""
    journal_dir = pathlib.Path(cfg["paths"]["journal"])
    journal_dir.mkdir(parents=True, exist_ok=True)
    
    ts = datetime.datetime.now()
    today = ts.strftime("%Y-%m-%d")
    time_str = ts.strftime("%H:%M:%S")
    
    # Create daily journal if it doesn't exist
    daily_path = journal_dir / f"{today}.md"
    if not daily_path.exists():
        daily_path.write_text(f"# {today} - Journal\n\n", encoding="utf-8")
    
    # Add entry marker
    with open(daily_path, "a", encoding="utf-8") as f:
        f.write(f"\n## Entry {time_str}\n\n")
    
    # Open the journal file
    os.startfile(str(daily_path))
    print(f"[Calyx] Created journal entry -> {daily_path}")
    return daily_path


def open_journal(cfg):
    """Open the journal directory"""
    journal_dir = pathlib.Path(cfg["paths"]["journal"])
    journal_dir.mkdir(parents=True, exist_ok=True)
    os.startfile(str(journal_dir))
    print(f"[Calyx] Opened journal directory -> {journal_dir}")


def start_transcription(cfg):
    """Start transcription mode - launches the transcription listener"""
    import subprocess
    
    print("[Calyx] Starting transcription mode...")
    print("[Calyx] Say 'Aurora' or 'Calyx' to activate, then speak naturally")
    print("[Calyx] Transcription will stop after 3 seconds of silence")
    
    # Launch the transcription listener
    try:
        subprocess.Popen([
            'python', '-u', 'Scripts\\listener_transcribe.py'
        ], cwd=cfg["paths"]["root"])
        print("[Calyx] Transcription listener started")
    except Exception as e:
        print(f"[Calyx] Error starting transcription: {e}")
    
    return None


def dispatch(cfg, parts, source="console", transcript=None):
    cmd = parts[0].lower()
    if cmd == "begin_session":
        begin_session(cfg, source=source, transcript=transcript)
    elif cmd == "list_projects":
        list_projects(cfg)
    elif cmd == "summon":
        if len(parts) < 2:
            print("Usage: summon <project_name_part>")
        else:
            summon(cfg, " ".join(parts[1:]))
    elif cmd == "log_reflection":
        text = " ".join(parts[1:]) if len(parts) > 1 else None
        log_reflection(cfg, text)
    elif cmd == "create_journal_entry":
        create_journal_entry(cfg)
    elif cmd == "open_journal":
        open_journal(cfg)
    elif cmd == "start_transcription":
        start_transcription(cfg)
    elif cmd == "agent":
        # Bridge into the Agent1 console
        # Usage:
        #   agent                 -> interactive console
        #   agent <goal text...>  -> one-shot goal
        try:
            root = cfg["paths"]["root"]
            if len(parts) > 1:
                goal = " ".join(parts[1:])
                subprocess.call([
                    sys.executable, "-u", "Scripts\\agent_console.py", "--goal", goal
                ], cwd=root)
            else:
                subprocess.call([
                    sys.executable, "-u", "Scripts\\agent_console.py"
                ], cwd=root)
        except Exception as e:
            print(f"[Calyx] Failed to launch Agent1 console: {e}")
    elif cmd in ("exit", "quit"):
        pass
    else:
        print(f"[Calyx] Unknown command: {cmd}")


def main():
    cfg = load_config()
    parser = argparse.ArgumentParser(prog="calyx")
    parser.add_argument(
        "command",
        nargs="*",
        help="begin_session | list_projects | summon <project> | log_reflection [text] | exit",
    )
    args = parser.parse_args()

    if args.command:
        dispatch(cfg, args.command, source="cli")
        return

    print("Calyx Console v1.1 - type 'help' for commands, 'exit' to quit.")
    while True:
        try:
            raw = input(PROMPT).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        if not raw:
            continue
        if raw.lower() in ("exit", "quit"):
            break
        if raw.lower() in ("help", "?"):
            print("Commands:")
            print("  begin_session")
            print("  list_projects")
            print("  summon <project_name_part>")
            print("  log_reflection [text]")
            continue
        parts = shlex.split(raw)
        dispatch(cfg, parts, source="cli")


if __name__ == "__main__":
    main()
