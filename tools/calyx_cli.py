#!/usr/bin/env python3
"""
Station Calyx CLI - Interactive command-line interface for CBO
--------------------------------------------------------------

This CLI allows you to issue commands and have conversations with CBO (Calyx Bridge Overseer)
via both direct commands and LLM integration.

Usage:
    python tools/calyx_cli.py                    # Interactive mode
    python tools/calyx_cli.py --status            # Show system status
    python tools/calyx_cli.py --objective "text"  # Submit objective
    python tools/calyx_cli.py --chat              # LLM conversation mode
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Fallback to basic print
    class Console:
        def __init__(self): pass
        def print(self, *args, **kwargs): print(*args)
        def rule(self, title): print(f"\n{title}\n")
    class Table:
        def __init__(self, *args, **kwargs): pass
        def add_row(self, *args): pass

import requests
import uuid
import os as _os

from station_calyx.core.intent_artifact import (
    IntentArtifact,
    accept_intent_artifact,
    require_clarified,
    ClarificationRequired,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
CBO_DIALOG = OUT / "bridge" / "dialog.log"
CBO_API_URL = "http://localhost:8080"

console = Console()


class CBOClient:
    """Client for interacting with CBO API"""
    
    def __init__(self, api_url: str = CBO_API_URL):
        self.api_url = api_url
        
    def heartbeat(self) -> Dict[str, Any]:
        """Check CBO heartbeat"""
        try:
            response = requests.get(f"{self.api_url}/heartbeat", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "offline"}
    
    def submit_objective(self, description: str, priority: int = 5, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Submit a new objective to CBO"""
        try:
            payload = {
                "description": description,
                "priority": priority,
                "metadata": metadata or {}
            }
            response = requests.post(f"{self.api_url}/objective", json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        try:
            response = requests.get(f"{self.api_url}/status", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def get_report(self) -> Dict[str, Any]:
        """Get comprehensive system report"""
        try:
            response = requests.get(f"{self.api_url}/report", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def get_policy(self) -> Dict[str, Any]:
        """Get current policy"""
        try:
            response = requests.get(f"{self.api_url}/policy", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}


class LLMConversation:
    """LLM-powered conversation interface with CBO"""
    
    def __init__(self, client: CBOClient):
        self.client = client
        self.conversation_history: List[Dict[str, str]] = []
        self.llm_handle = None
        self.model_loaded = False
        
    def _load_model(self) -> bool:
        """Load local LLM model"""
        if self.model_loaded and self.llm_handle:
            return True
            
        try:
            from llama_cpp import Llama
            
            # Try to load from model manifest
            model_manifest = ROOT / "tools" / "models" / "MODEL_MANIFEST.json"
            if model_manifest.exists():
                with model_manifest.open() as f:
                    manifest = json.load(f)
                    models = manifest.get("models", [])
                    # Find a general model or use first available
                    model_entry = next((m for m in models if m.get("role") == "general"), models[0] if models else None)
                    if model_entry:
                        model_path = ROOT / model_entry["filename"]
                        if model_path.exists():
                            # Try GPU offloading if available
                            try:
                                from tools.gpu_utils import get_gpu_layer_count
                                gpu_layers = get_gpu_layer_count()
                                if gpu_layers > 0:
                                    self.llm_handle = Llama(
                                        model_path=str(model_path),
                                        n_ctx=2048,
                                        temperature=0.7,
                                        n_gpu_layers=gpu_layers,
                                        verbose=False
                                    )
                                else:
                                    self.llm_handle = Llama(
                                        model_path=str(model_path),
                                        n_ctx=2048,
                                        temperature=0.7,
                                        verbose=False
                                    )
                            except Exception:
                                self.llm_handle = Llama(
                                    model_path=str(model_path),
                                    n_ctx=2048,
                                    temperature=0.7,
                                    verbose=False
                                )
                            self.model_loaded = True
                            return True
            return False
        except ImportError:
            return False
        except Exception as e:
            console.print(f"[dim]LLM loading error: {e}[/dim]")
            return False
        
    def _get_system_context(self) -> str:
        """Get current system context for LLM"""
        report = self.client.get_report()
        status = self.client.get_status()
        
        context = f"""You are Calyx Bridge Overseer (CBO), the Central Bridge Overseer for Station Calyx.

Current System Status:
- Tasks Queued: {report.get('queue_depth', 0)}
- Objectives Pending: {report.get('objectives_pending', 0)}
- TES Summary: {json.dumps(report.get('tes_summary', {}), indent=2)}
- Recent Updates: {len(report.get('recent_status_updates', []))}

You coordinate agents, manage tasks, and ensure Station Calyx operates safely and efficiently.
Respond conversationally but maintain your role as the overseer."""
        
        return context
    
    def _call_llm(self, user_message: str) -> str:
        """Call local LLM for conversation"""
        # Try to load model if not already loaded
        if not self.model_loaded:
            if not self._load_model():
                return self._simple_response(user_message)
        
        if not self.llm_handle:
            return self._simple_response(user_message)
        
        try:
            # Build conversation context
            context = self._get_system_context()
            
            # Format conversation history
            history_text = ""
            for msg in self.conversation_history[-6:]:  # Last 6 messages
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    history_text += f"User: {content}\n"
                elif role == "assistant":
                    history_text += f"Assistant: {content}\n"
            
            # Create prompt
            prompt = f"""{context}

Conversation History:
{history_text}

User: {user_message}
Assistant:"""
            
            # Call LLM
            response = self.llm_handle(
                prompt,
                max_tokens=256,
                temperature=0.7,
                stop=["User:", "\n\nUser:"],
                echo=False
            )
            
            # Extract text
            text = response.get("choices", [{}])[0].get("text", "").strip()
            
            if not text:
                return self._simple_response(user_message)
            
            return text
            
        except Exception as e:
            console.print(f"[dim]LLM error: {e}[/dim]")
            return self._simple_response(user_message)
    
    def _simple_response(self, user_message: str) -> str:
        """Simple rule-based response when LLM not available"""
        msg_lower = user_message.lower()
        
        if "status" in msg_lower or "how" in msg_lower:
            report = self.client.get_report()
            return f"Current status: {report.get('queue_depth', 0)} tasks queued, {report.get('objectives_pending', 0)} objectives pending."
        
        if "objective" in msg_lower or "task" in msg_lower or "goal" in msg_lower:
            return "I can queue objectives for the Station. What would you like me to coordinate?"
        
        if "help" in msg_lower:
            return "I can help you monitor Station Calyx, submit objectives, check status, and coordinate tasks. What do you need?"
        
        return "I understand your message. How can I assist with Station Calyx operations?"
    
    def chat(self, message: str) -> str:
        """Process a chat message and return response"""
        # Add to history
        self.conversation_history.append({"role": "user", "content": message})
        
        # Get response
        response = self._call_llm(message)
        
        # Add to history
        self.conversation_history.append({"role": "assistant", "content": response})
        
        return response


def show_status(client: CBOClient):
    """Display current system status"""
    console.rule("Station Calyx Status")
    
    # Check heartbeat
    hb = client.heartbeat()
    if "error" in hb:
        console.print(f"[red]CBO API offline: {hb['error']}[/red]")
        return
    
    console.print(f"[green]CBO: Online[/green]")
    console.print(f"Status: {hb.get('status', 'unknown')}")
    console.print(f"Timestamp: {hb.get('timestamp', 'unknown')}")
    
    # Get report
    report = client.get_report()
    if "error" not in report:
        console.print("\n[bold]System Metrics:[/bold]")
        console.print(f"Queue Depth: {report.get('queue_depth', 0)}")
        console.print(f"Objectives Pending: {report.get('objectives_pending', 0)}")
        
        tes_summary = report.get('tes_summary', {})
        if tes_summary:
            console.print(f"\n[bold]TES Summary:[/bold]")
            console.print(f"Mean TES: {tes_summary.get('mean_tes', 'N/A')}")
            console.print(f"Latest TES: {tes_summary.get('latest_tes', 'N/A')}")
            console.print(f"Samples: {tes_summary.get('sample_count', 'N/A')}")


def show_detailed_report(client: CBOClient):
    """Display detailed system report"""
    console.rule("Station Calyx Detailed Report")
    
    report = client.get_report()
    if "error" in report:
        console.print(f"[red]Error: {report['error']}[/red]")
        return
    
    # Tasks
    tasks = report.get('active_tasks', 0)
    console.print(f"\n[bold]Tasks:[/bold] {tasks}")
    
    # Recent status updates
    updates = report.get('recent_status_updates', [])
    if updates:
        console.print(f"\n[bold]Recent Updates:[/bold]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Task ID")
        table.add_column("Status")
        table.add_column("Agent")
        table.add_column("Time")
        
        for update in updates[-10:]:  # Last 10
            table.add_row(
                update.get('task_id', 'N/A')[:8],
                update.get('status', 'N/A'),
                update.get('agent_id', 'N/A'),
                update.get('updated_at', 'N/A')[:19] if update.get('updated_at') else 'N/A'
            )
        console.print(table)


def submit_objective_interactive(client: CBOClient):
    """Interactive objective submission"""
    console.rule("Submit Objective to CBO")
    
    description = Prompt.ask("\nObjective description")
    priority_str = Prompt.ask("Priority (1-10)", default="5")
    
    try:
        priority = int(priority_str)
        if priority < 1 or priority > 10:
            priority = 5
    except ValueError:
        priority = 5
    
    result = client.submit_objective(description, priority)
    
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
    else:
        console.print(f"[green]Objective submitted: {result.get('objective_id', 'unknown')}[/green]")


def chat_mode(client: CBOClient):
    """Interactive chat mode with CBO"""
    console.rule("Chat with CBO")
    console.print("[dim]Type 'exit' to quit, 'help' for commands[/dim]\n")
    
    llm = LLMConversation(client)
    
    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            
            if user_input.lower() in ('exit', 'quit', 'q'):
                break
            
            if user_input.lower() == 'help':
                console.print("""
Commands:
  status      - Show system status
  report      - Show detailed report
  clear       - Clear conversation history
  exit        - Exit chat mode
""")
                continue
            
            if user_input.lower() == 'status':
                show_status(client)
                continue
            
            if user_input.lower() == 'report':
                show_detailed_report(client)
                continue
            
            if user_input.lower() == 'clear':
                llm.conversation_history = []
                console.print("[green]Conversation cleared[/green]")
                continue
            
            # Get response from LLM
            response = llm.chat(user_input)
            console.print(f"\n[bold green]CBO>[/bold green] {response}")
            
        except KeyboardInterrupt:
            break
    
    console.print("\n[dim]Exiting chat mode...[/dim]")


def interactive_mode(client: CBOClient):
    """Main interactive CLI mode"""
    console.rule("Station Calyx CLI")
    console.print("[dim]Type 'help' for commands, 'exit' to quit[/dim]\n")
    
    while True:
        try:
            command = Prompt.ask("\n[bold cyan]Calyx>[/bold cyan]")
            
            if not command:
                continue
            
            cmd_parts = command.strip().split(maxsplit=1)
            cmd = cmd_parts[0].lower()
            args = cmd_parts[1] if len(cmd_parts) > 1 else ""
            
            if cmd in ('exit', 'quit', 'q'):
                break
            
            if cmd == 'help':
                console.print("""
Commands:
  status              - Show system status
  report              - Show detailed report
  objective           - Submit a new objective
  chat                - Enter LLM conversation mode
  heartbeat           - Check CBO heartbeat
  policy              - Show current policy
  exit                - Exit CLI
""")
                continue
            
            if cmd == 'status':
                show_status(client)
                continue
            
            if cmd == 'report':
                show_detailed_report(client)
                continue
            
            if cmd == 'objective':
                if args:
                    client.submit_objective(args)
                    console.print(f"[green]Objective submitted[/green]")
                else:
                    submit_objective_interactive(client)
                continue
            
            if cmd == 'chat':
                chat_mode(client)
                continue
            
            if cmd == 'heartbeat':
                hb = client.heartbeat()
                console.print(json.dumps(hb, indent=2))
                continue
            if cmd == 'policy':
                policy = client.get_policy()
                console.print(json.dumps(policy, indent=2))
                continue

            if cmd == 'push-evidence':
                console.print("[dim]Use: python tools/push_evidence.py --to <url> --token <token>[/dim]")
                console.print("[dim]Or: python tools/calyx_cli.py --push-evidence --to <url> --token <token>[/dim]")
                continue

            console.print(f"[yellow]Unknown command: {cmd}[/yellow]")

        except KeyboardInterrupt:
            break

    console.print("\n[dim]Goodbye[/dim]")


def run_push_evidence(args) -> int:
    """Run push-evidence command."""
    import os as _os

    target_url = args.to or _os.environ.get("CALYX_HOME_INGEST_URL")
    token = args.token or _os.environ.get("CALYX_INGEST_TOKEN")

    if not target_url:
        console.print("[red]Target URL required. Use --to or set CALYX_HOME_INGEST_URL[/red]")
        return 1

    if not args.dry_run and not token:
        console.print("[red]Auth token required. Use --token or set CALYX_INGEST_TOKEN[/red]")
        return 1

    # Import and run push_evidence
    try:
        from tools.push_evidence import run_push
        success, accepted, rejected = run_push(
            target_url=target_url,
            token=token or "",
            dry_run=args.dry_run,
        )
        return 0 if success else 1
    except ImportError as e:
        console.print(f"[red]Failed to import push_evidence: {e}[/red]")
        return 1
    except Exception as e:
        console.print(f"[red]Push failed: {e}[/red]")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Station Calyx CLI")
    parser.add_argument("--status", action="store_true", help="Show system status")
    parser.add_argument("--report", action="store_true", help="Show detailed report")
    parser.add_argument("--objective", help="Submit an objective")
    parser.add_argument("--priority", type=int, default=5, help="Priority (1-10) for objective")
    parser.add_argument("--chat", action="store_true", help="Enter chat mode")
    parser.add_argument("--api-url", default=CBO_API_URL, help="CBO API URL")
    parser.add_argument("--push-evidence", action="store_true", help="Push evidence to home workstation")
    parser.add_argument("--to", help="Target URL for push-evidence (e.g., http://192.168.1.100:8420)")
    parser.add_argument("--token", help="Auth token for push-evidence")
    parser.add_argument("--dry-run", action="store_true", help="Dry run for push-evidence")
    # Intent ingestion (Phase 1)
    parser.add_argument("--intent-file", help="Path to intent artifact JSON file to ingest")
    parser.add_argument("--intent-raw", help="Raw user input text for intent creation")
    parser.add_argument("--intent-goal", help="Interpreted goal (short) for the intent")
    parser.add_argument("--intent-confidence", type=float, help="Confidence score (0.0-1.0)")
    parser.add_argument("--intent-clarify", action="store_true", help="Mark intent as requiring clarification")
    parser.add_argument("intent-audit-maintain", nargs='?', help="Run audit maintenance: rotate/cleanup audit sink", default=None)
    subparsers = parser.add_subparsers(dest='subcmd')
    um = subparsers.add_parser('usermodel', help='UserModel inspection and management')
    um.add_argument('op', choices=['show','export','reset'], help='Operation')
    um.add_argument('user_id', help='User ID')

    args = parser.parse_args()

    # Handle intent ingestion if requested (Phase 1 ingress)
    if args.intent_file or args.intent_raw:
        # Build artifact either from file or from provided fields
        if args.intent_file:
            try:
                raw = Path(args.intent_file).read_text(encoding="utf-8")
                data = json.loads(raw)
                artifact = IntentArtifact.from_dict(data)
            except Exception as e:
                console.print(f"[red]Failed to load intent file: {e}[/red]")
                return 1
        else:
            if not args.intent_raw:
                console.print("[red]Provide --intent-raw or --intent-file[/red]")
                return 1
            intent_id = f"intent-{uuid.uuid4().hex[:8]}"
            confidence = float(args.intent_confidence) if args.intent_confidence is not None else 1.0
            artifact = IntentArtifact(
                intent_id=intent_id,
                raw_user_input=args.intent_raw,
                interpreted_goal=(args.intent_goal or ""),
                confidence_score=confidence,
                clarification_required=bool(args.intent_clarify),
            )

        # Persist artifact (accept as-provided)
        try:
            accept_intent_artifact(artifact)
            console.print(f"[green]Intent artifact persisted: {artifact.intent_id}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to persist intent artifact: {e}[/red]")
            return 1

        # Enforce clarification gate before any planning/governance
        try:
            require_clarified(artifact)
            console.print("[green]Intent passes clarification threshold. Governance may proceed once plans are available.[/green]")
            return 0
        except ClarificationRequired as ce:
            console.print(f"[yellow]Intent requires clarification: {ce}[/yellow]")
            console.print("[dim]No governance or execution will proceed until clarified.[/dim]")
            return 2

    # Audit maintenance command
    if args.intent_audit_maintain is not None:
        try:
            from station_calyx.core.intent_artifact import maintain_audit_sink
            maintain_audit_sink()
            console.print("[green]Audit maintenance completed.[/green]")
            return 0
        except Exception as e:
            console.print(f"[red]Audit maintenance failed: {e}[/red]")
            return 1


    # Handle push-evidence command separately (does not need CBO API)
    if args.push_evidence:
        return run_push_evidence(args)

    client = CBOClient(api_url=args.api_url)
    
    # Check if CBO is reachable
    hb = client.heartbeat()
    if "error" in hb and args.status:
        console.print(f"[red]CBO API offline at {args.api_url}[/red]")
        console.print("[yellow]Ensure CBO API is running: python -m calyx.cbo.api[/yellow]")
        return 1
    
    # Execute based on arguments
    if args.status:
        show_status(client)
    elif args.report:
        show_detailed_report(client)
    elif args.objective:
        result = client.submit_objective(args.objective, args.priority)
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            return 1
        console.print(f"[green]Objective submitted: {result.get('objective_id')}[/green]")
    elif args.chat:
        chat_mode(client)
    else:
        # Interactive mode
        interactive_mode(client)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
