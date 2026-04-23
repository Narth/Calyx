import httpx
from rich.console import Console
from rich.panel import Panel

console = Console()
CBO_CHAT = "http://127.0.0.1:7778/chat"

def main():
    session_id = "home"
    mode = "dev"
    allow_tools = True
    model_role = "none"  # none | architect | workhorse | second | local

    def banner():
        return Panel.fit(
            "[bold]CBO CLI Avatar[/bold]\n"
            f"session={session_id}  mode={mode}  allow_tools={allow_tools}  model_role={model_role}\n\n"
            "Commands:\n"
            "  /mode dev|safe|observe\n"
            "  /tools on|off\n"
            "  /search <query>\n"
            "  /architect  (use Claude)\n"
            "  /workhorse  (use OpenAI)\n"
            "  /second     (use Kimi)\n"
            "  /local      (use Ollama / local model)\n"
            "  /model      (show current)\n"
            "  /exit",
            title="Station Calyx"
        )

    console.print(banner())

    while True:
        user = console.input("[bold cyan]You[/bold cyan]> ").strip()
        if not user:
            continue
        if user == "/exit":
            return
        if user.startswith("/mode "):
            mode = user.split(" ", 1)[1].strip()
            console.print(f"[yellow]Mode set to {mode}[/yellow]")
            console.print(banner())
            continue
        if user.startswith("/tools "):
            v = user.split(" ", 1)[1].strip().lower()
            allow_tools = (v == "on")
            console.print(f"[yellow]allow_tools set to {allow_tools}[/yellow]")
            console.print(banner())
            continue
        if user == "/architect":
            model_role = "architect"
            console.print("[yellow]Model role set to architect (Claude).[/yellow]")
            console.print(banner())
            continue
        if user == "/workhorse":
            model_role = "workhorse"
            console.print("[yellow]Model role set to workhorse (OpenAI).[/yellow]")
            console.print(banner())
            continue
        if user == "/second":
            model_role = "second"
            console.print("[yellow]Model role set to second (Kimi).[/yellow]")
            console.print(banner())
            continue
        if user == "/local":
            model_role = "local"
            console.print("[yellow]Model role set to local (Ollama).[/yellow]")
            console.print(banner())
            continue
        if user == "/model":
            console.print(f"[yellow]Current model_role = {model_role}[/yellow]")
            continue
        if user.startswith("/search "):
            q = user.split(" ", 1)[1].strip()
            user = f"Please search the repo for: {q}"

        try:
            allow_second_opinion = model_role in ("second", "second_opinion")
            r = httpx.post(
                CBO_CHAT,
                json={
                    "user_text": user,
                    "session_id": session_id,
                    "mode": mode,
                    "allow_tools": allow_tools,
                    "model_role": model_role,
                    "allow_second_opinion": allow_second_opinion,
                },
                timeout=60
            )
            r.raise_for_status()
            data = r.json()
            reply = data["reply_text"]
            receipt = data["receipt_sha256"]
            console.print(Panel(reply, title=f"[green]CBO[/green]  receipt={receipt[:12]}…"))
            second = data.get("second_opinion_text") or ""
            if second.strip():
                console.print(Panel(second.strip(), title="[magenta]Second opinion (Kimi)[/magenta]"))
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")

if __name__ == "__main__":
    main()