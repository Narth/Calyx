# Calyx Console v1.0 (Windows-friendly prompt)
import os, sys, argparse, yaml, datetime, subprocess, shlex, pathlib, shutil

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

def begin_session(cfg):
    codex = cfg["paths"]["codex"]
    obsidian_path = shutil.which("obsidian")  # only call if it exists
    if obsidian_path:
        subprocess.Popen([obsidian_path, codex])
        print("[Calyx] Session begun. Codex opened in Obsidian.")
    else:
        os.startfile(codex)
        print("[Calyx] Session begun. Codex folder opened.")

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
        path.write_text(f"# {today} — Reflection\n\n", encoding="utf-8")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"- {text or '(empty entry)'}\n")
    os.startfile(str(path))
    print(f"[Calyx] Logged reflection -> {path}")

def dispatch(cfg, parts):
    cmd = parts[0].lower()
    if cmd == "begin_session":
        begin_session(cfg)
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
    elif cmd in ("exit", "quit"):
        pass
    else:
        print(f"[Calyx] Unknown command: {cmd}")

def main():
    cfg = load_config()
    parser = argparse.ArgumentParser(prog="calyx")
    parser.add_argument("command", nargs="*", help="begin_session | list_projects | summon <project> | log_reflection [text] | exit")
    args = parser.parse_args()

    # If called with args, dispatch once and exit
    if args.command:
        dispatch(cfg, args.command)
        return

    # Otherwise, run REPL
    print("Calyx Console v1.0 — type 'help' for commands, 'exit' to quit.")
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
        dispatch(cfg, parts)

if __name__ == "__main__":
    main()
