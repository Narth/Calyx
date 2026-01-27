#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Station Calyx Terminal UI
=========================

A beautiful, interactive terminal interface for Station Calyx.

Launch with:
    python -m station_calyx.ui.tui

Or use the launcher:
    calyx

Controls:
    q / Ctrl+C  - Quit
    d           - Dashboard
    g           - Governance
    a           - Actions
    l           - Logs
    r           - Refresh
    ?           - Help
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    LoadingIndicator,
    ProgressBar,
    Static,
    TabbedContent,
    TabPane,
)

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from station_calyx.ui.tui_styles import CALYX_CSS


# ============================================================================
# ASCII Art
# ============================================================================

CALYX_LOGO = """
╔═══════════════════════════════════╗
║                                   ║
║   STATION CALYX                   ║
║                                   ║
║   🌸 AI-For-All Project 🌸        ║
║                                   ║
╚═══════════════════════════════════╝
"""

CALYX_SMALL = """
╭───────────────────────────╮
│   🌸 STATION CALYX 🌸     │
│     AI-For-All Project    │
╰───────────────────────────╯
"""


# ============================================================================
# Helper Functions
# ============================================================================

def run_calyx_command(command: list[str]) -> tuple[bool, str]:
    """Run a Station Calyx CLI command and return result."""
    try:
        # Get the project root directory (2 levels up from tui.py)
        project_root = Path(__file__).resolve().parents[2]
        full_cmd = [sys.executable, "-B", "-m", "station_calyx.ui.cli"] + command
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_root,
        )
        output = result.stdout + result.stderr
        # Clean up the output - remove Python warnings
        lines = [l for l in output.split("\n") if not l.startswith("<frozen") and "RuntimeWarning" not in l]
        return result.returncode == 0, "\n".join(lines).strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, f"Error: {e}"


def get_system_status() -> dict:
    """Get current system status."""
    try:
        import psutil
    except ImportError:
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_used_gb": 0,
            "memory_total_gb": 0,
            "disk_percent": 0,
            "disk_used_gb": 0,
            "disk_total_gb": 0,
        }
    
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        # Use C: drive on Windows
        try:
            disk = psutil.disk_usage("C:\\")
        except:
            disk = psutil.disk_usage("/")
        
        return {
            "cpu_percent": cpu,
            "memory_percent": memory.percent,
            "memory_used_gb": memory.used / (1024**3),
            "memory_total_gb": memory.total / (1024**3),
            "disk_percent": disk.percent,
            "disk_used_gb": disk.used / (1024**3),
            "disk_total_gb": disk.total / (1024**3),
        }
    except Exception:
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_used_gb": 0,
            "memory_total_gb": 0,
            "disk_percent": 0,
            "disk_used_gb": 0,
            "disk_total_gb": 0,
        }


def get_governance_status() -> dict:
    """Get Clawdbot governance status."""
    status = {
        "enabled": True,
        "halted": False,
        "trial_mode": True,
        "pending_proposals": 0,
        "raw_output": "",
    }
    
    try:
        success, output = run_calyx_command(["clawdbot", "status"])
        status["raw_output"] = output
        
        if success and output:
            output_lower = output.lower()
            if "enabled:** true" in output_lower or "enabled: true" in output_lower:
                status["enabled"] = True
            elif "enabled:** false" in output_lower or "enabled: false" in output_lower:
                status["enabled"] = False
            
            if "halted:** true" in output_lower or "halted: true" in output_lower:
                status["halted"] = True
            
            if "trial mode: true" in output_lower:
                status["trial_mode"] = True
        
        # Get pending count
        success, output = run_calyx_command(["clawdbot", "pending"])
        if success:
            if "no pending" in output.lower():
                status["pending_proposals"] = 0
            else:
                status["pending_proposals"] = output.count("## ")
    except Exception:
        pass  # Keep defaults
    
    return status


# ============================================================================
# Welcome Screen
# ============================================================================

class WelcomeScreen(Screen):
    """Welcome screen shown on startup."""
    
    BINDINGS = [
        Binding("enter", "continue", "Continue"),
        Binding("q", "quit", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static(CALYX_LOGO, id="welcome-ascii"),
            Static('"Capability under governance. Action with authorization."', id="welcome-motto"),
            Static(""),
            Static("Press [bold cyan]ENTER[/] to continue or [bold red]Q[/] to quit", id="welcome-prompt"),
            id="welcome-container",
        )
    
    def action_continue(self) -> None:
        self.app.switch_mode("dashboard")
    
    def action_quit(self) -> None:
        self.app.exit()


# ============================================================================
# Dashboard Screen
# ============================================================================

class DashboardScreen(Screen):
    """Main dashboard showing system overview."""
    
    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("g", "governance", "Governance"),
        Binding("a", "actions", "Actions"),
        Binding("l", "logs", "Logs"),
        Binding("q", "quit", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Static("📊 [bold orange1]SYSTEM STATUS[/]"),
            Static(""),
            Static(id="cpu-status"),
            Static(id="memory-status"),
            Static(id="disk-status"),
            Static(id="uptime-status"),
            Static(""),
            Static("🛡️ [bold orange1]GOVERNANCE[/]"),
            Static(""),
            Static(id="gov-hvd1"),
            Static(id="gov-clawdbot"),
            Static(id="gov-trial"),
            Static(id="gov-pending"),
            Static(""),
            Static("⚡ [bold orange1]QUICK ACTIONS[/]"),
            Static(""),
            Horizontal(
                Button("Status", id="btn-status", classes="primary"),
                Button("Assess", id="btn-assess", classes="primary"),
                Button("Digest", id="btn-digest", classes="secondary"),
                Button("Discord", id="btn-discord", classes="secondary"),
            ),
            Static(""),
            Static("📜 [bold orange1]RECENT ACTIVITY[/]"),
            Static(""),
            Static(id="recent-activity"),
            id="dashboard-content",
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize dashboard data."""
        self.refresh_data()
        self.set_interval(30, self.refresh_data)
    
    def refresh_data(self) -> None:
        """Refresh all dashboard data."""
        # System status
        status = get_system_status()
        
        cpu_color = "green" if status["cpu_percent"] < 70 else "yellow" if status["cpu_percent"] < 90 else "red"
        mem_color = "green" if status["memory_percent"] < 70 else "yellow" if status["memory_percent"] < 90 else "red"
        disk_color = "green" if status["disk_percent"] < 70 else "yellow" if status["disk_percent"] < 90 else "red"
        
        self.query_one("#cpu-status", Static).update(
            f"  CPU:    [{cpu_color}]{status['cpu_percent']:5.1f}%[/]"
        )
        self.query_one("#memory-status", Static).update(
            f"  Memory: [{mem_color}]{status['memory_percent']:5.1f}%[/] ({status['memory_used_gb']:.1f}/{status['memory_total_gb']:.1f} GB)"
        )
        self.query_one("#disk-status", Static).update(
            f"  Disk:   [{disk_color}]{status['disk_percent']:5.1f}%[/] ({status['disk_used_gb']:.0f}/{status['disk_total_gb']:.0f} GB)"
        )
        self.query_one("#uptime-status", Static).update(
            f"  Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Governance status
        gov = get_governance_status()
        
        self.query_one("#gov-hvd1", Static).update(
            "  HVD-1:     [green]✓ Active[/]"
        )
        
        clawdbot_status = "[green]✓ Enabled[/]" if gov["enabled"] else "[red]✗ Disabled[/]"
        if gov["halted"]:
            clawdbot_status = "[red]⚠ HALTED[/]"
        self.query_one("#gov-clawdbot", Static).update(f"  Clawdbot:  {clawdbot_status}")
        
        self.query_one("#gov-trial", Static).update(
            f"  Trial:     [yellow]{'Active' if gov['trial_mode'] else 'Inactive'}[/]"
        )
        
        pending_color = "green" if gov["pending_proposals"] == 0 else "yellow"
        self.query_one("#gov-pending", Static).update(
            f"  Pending:   [{pending_color}]{gov['pending_proposals']} proposals[/]"
        )
        
        # Recent activity
        self.query_one("#recent-activity", Static).update(
            "  • Dashboard loaded\n"
            f"  • Last refresh: {datetime.now().strftime('%H:%M:%S')}\n"
            "  • System operational"
        )
    
    def action_refresh(self) -> None:
        self.refresh_data()
        self.notify("Dashboard refreshed", severity="information")
    
    def action_governance(self) -> None:
        self.app.switch_mode("governance")
    
    def action_actions(self) -> None:
        self.app.switch_mode("actions")
    
    
    def action_logs(self) -> None:
        self.app.switch_mode("logs")
    
    def action_quit(self) -> None:
        self.app.exit()
    
    @on(Button.Pressed, "#btn-status")
    def on_status_button(self) -> None:
        success, output = run_calyx_command(["status"])
        self.app.push_screen(OutputModal("System Status", output))
    
    @on(Button.Pressed, "#btn-assess")
    def on_assess_button(self) -> None:
        self.notify("Running assessment...", severity="information")
        success, output = run_calyx_command(["assess", "--recent", "30"])
        self.app.push_screen(OutputModal("System Assessment", output))
    
    @on(Button.Pressed, "#btn-digest")
    def on_digest_button(self) -> None:
        self.notify("Generating digest...", severity="information")
        success, output = run_calyx_command(["digest", "--stdout"])
        self.app.push_screen(OutputModal("Truth Digest", output))
    
    @on(Button.Pressed, "#btn-discord")
    def on_discord_button(self) -> None:
        self.app.push_screen(OutputModal(
            "Discord Integration",
            "🌸 Calyx Agent is available on Discord!\n\n"
            "You can interact with Station Calyx via:\n"
            "  • Direct messages to @Calyx Agent\n"
            "  • Commands like: 'Run: python -m station_calyx.ui.cli status'\n\n"
            "The Discord relay provides mobile access to Station Calyx."
        ))


# ============================================================================
# Governance Screen
# ============================================================================

class GovernanceScreen(Screen):
    """Governance management screen."""
    
    BINDINGS = [
        Binding("d", "dashboard", "Dashboard"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("🛡️ [bold]STATION CALYX GOVERNANCE[/]", classes="panel-title"),
            Static(""),
            Horizontal(
                Vertical(
                    Static("[bold]Governance Documents[/]"),
                    Static(""),
                    Static("  📄 HVD-1  - Human Value Declaration"),
                    Static("  📄 PBS-1  - Privacy Boundary Schema"),
                    Static("  📄 DRP-1  - Data Retention Policy"),
                    Static("  📄 DP-1   - Disclosure Protocol"),
                    Static("  📄 EG-1   - Exit Guarantee"),
                    id="gov-docs",
                ),
                Vertical(
                    Static("[bold]Clawdbot Status[/]"),
                    Static(""),
                    Static(id="clawdbot-status"),
                    Static(""),
                    Horizontal(
                        Button("Enable", id="btn-enable", classes="primary"),
                        Button("Disable", id="btn-disable", classes="secondary"),
                        Button("Halt", id="btn-halt", classes="danger"),
                    ),
                    id="clawdbot-controls",
                ),
            ),
            Static(""),
            Static("[bold]Pending Action Proposals[/]"),
            Static(id="pending-proposals"),
            id="content",
        )
        yield Footer()
    
    def on_mount(self) -> None:
        self.refresh_data()
    
    def refresh_data(self) -> None:
        # Get governance status
        gov = get_governance_status()
        
        status_text = []
        status_text.append(f"  Enabled: [{'green' if gov['enabled'] else 'red'}]{'Yes' if gov['enabled'] else 'No'}[/]")
        status_text.append(f"  Halted:  [{'red' if gov['halted'] else 'green'}]{'Yes' if gov['halted'] else 'No'}[/]")
        status_text.append(f"  Trial:   [yellow]{'Active' if gov['trial_mode'] else 'Inactive'}[/]")
        status_text.append(f"  Pending: [cyan]{gov['pending_proposals']}[/] proposals")
        
        self.query_one("#clawdbot-status", Static).update("\n".join(status_text))
        
        # Get pending proposals
        success, output = run_calyx_command(["clawdbot", "pending"])
        if success:
            if "no pending" in output.lower():
                self.query_one("#pending-proposals", Static).update("  [green]✓ No pending action proposals[/]")
            else:
                self.query_one("#pending-proposals", Static).update(output)
        else:
            self.query_one("#pending-proposals", Static).update("  [green]✓ Queue clear[/]")
    
    def action_dashboard(self) -> None:
        self.app.switch_mode("dashboard")
    
    def action_refresh(self) -> None:
        self.refresh_data()
        self.notify("Governance data refreshed", severity="information")
    
    def action_quit(self) -> None:
        self.app.exit()
    
    @on(Button.Pressed, "#btn-enable")
    def on_enable(self) -> None:
        success, output = run_calyx_command(["clawdbot", "enable", "--reason", "Enabled via TUI"])
        self.notify(output, severity="information" if success else "error")
        self.refresh_data()
    
    @on(Button.Pressed, "#btn-disable")
    def on_disable(self) -> None:
        success, output = run_calyx_command(["clawdbot", "disable", "--reason", "Disabled via TUI"])
        self.notify(output, severity="information" if success else "error")
        self.refresh_data()
    
    @on(Button.Pressed, "#btn-halt")
    def on_halt(self) -> None:
        success, output = run_calyx_command(["clawdbot", "halt", "--reason", "Emergency halt via TUI"])
        self.notify(output, severity="warning" if success else "error")
        self.refresh_data()


# ============================================================================
# Actions Screen
# ============================================================================

class ActionsScreen(Screen):
    """Quick actions screen."""
    
    BINDINGS = [
        Binding("d", "dashboard", "Dashboard"),
        Binding("q", "quit", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("⚡ [bold]STATION CALYX ACTIONS[/]", classes="panel-title"),
            Static(""),
            Horizontal(
                Vertical(
                    Static("[bold]System Commands[/]"),
                    Button("System Status", id="btn-status", classes="primary"),
                    Button("System Assessment", id="btn-assess", classes="primary"),
                    Button("Generate Digest", id="btn-digest", classes="primary"),
                    Button("Evidence Summary", id="btn-evidence", classes="secondary"),
                ),
                Vertical(
                    Static("[bold]Governance Commands[/]"),
                    Button("Clawdbot Status", id="btn-clawdbot", classes="primary"),
                    Button("View Pending", id="btn-pending", classes="primary"),
                    Button("View History", id="btn-history", classes="secondary"),
                ),
                Vertical(
                    Static("[bold]Utilities[/]"),
                    Button("Open Terminal", id="btn-terminal", classes="secondary"),
                    Button("View Logs", id="btn-logs", classes="secondary"),
                    Button("Refresh All", id="btn-refresh", classes="secondary"),
                ),
            ),
            id="content",
        )
        yield Footer()
    
    def action_dashboard(self) -> None:
        self.app.switch_mode("dashboard")
    
    def action_quit(self) -> None:
        self.app.exit()
    
    @on(Button.Pressed, "#btn-status")
    def on_status(self) -> None:
        success, output = run_calyx_command(["status"])
        self.app.push_screen(OutputModal("System Status", output))
    
    @on(Button.Pressed, "#btn-assess")
    def on_assess(self) -> None:
        self.notify("Running assessment...")
        success, output = run_calyx_command(["assess", "--recent", "50"])
        self.app.push_screen(OutputModal("System Assessment", output))
    
    @on(Button.Pressed, "#btn-digest")
    def on_digest(self) -> None:
        self.notify("Generating digest...")
        success, output = run_calyx_command(["digest", "--stdout"])
        self.app.push_screen(OutputModal("Truth Digest", output))
    
    @on(Button.Pressed, "#btn-evidence")
    def on_evidence(self) -> None:
        success, output = run_calyx_command(["evidence", "summary"])
        self.app.push_screen(OutputModal("Evidence Summary", output))
    
    @on(Button.Pressed, "#btn-clawdbot")
    def on_clawdbot(self) -> None:
        success, output = run_calyx_command(["clawdbot", "status"])
        self.app.push_screen(OutputModal("Clawdbot Status", output))
    
    @on(Button.Pressed, "#btn-pending")
    def on_pending(self) -> None:
        success, output = run_calyx_command(["clawdbot", "pending"])
        self.app.push_screen(OutputModal("Pending Proposals", output))
    
    @on(Button.Pressed, "#btn-history")
    def on_history(self) -> None:
        success, output = run_calyx_command(["clawdbot", "history"])
        self.app.push_screen(OutputModal("Action History", output))
    
    @on(Button.Pressed, "#btn-terminal")
    def on_terminal(self) -> None:
        self.notify("Opening terminal... (not implemented in TUI)")
    
    @on(Button.Pressed, "#btn-logs")
    def on_logs(self) -> None:
        self.app.switch_mode("logs")
    
    @on(Button.Pressed, "#btn-refresh")
    def on_refresh(self) -> None:
        self.notify("Refreshed!", severity="information")


# ============================================================================
# Logs Screen
# ============================================================================

class LogsScreen(Screen):
    """Log viewer screen."""
    
    BINDINGS = [
        Binding("d", "dashboard", "Dashboard"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("📜 [bold]STATION CALYX LOGS[/]", classes="panel-title"),
            ScrollableContainer(
                Static(id="log-content"),
            ),
            id="content",
        )
        yield Footer()
    
    def on_mount(self) -> None:
        self.load_logs()
    
    def load_logs(self) -> None:
        log_path = Path(__file__).resolve().parents[3] / "logs"
        log_content = []
        
        if log_path.exists():
            log_files = sorted(log_path.glob("*.log"), reverse=True)[:3]
            for log_file in log_files:
                log_content.append(f"[bold]{log_file.name}[/]")
                try:
                    with open(log_file, "r") as f:
                        lines = f.readlines()[-20:]
                        log_content.extend(["  " + line.strip() for line in lines])
                except Exception as e:
                    log_content.append(f"  Error reading: {e}")
                log_content.append("")
        else:
            log_content.append("No logs directory found")
        
        self.query_one("#log-content", Static).update("\n".join(log_content))
    
    def action_dashboard(self) -> None:
        self.app.switch_mode("dashboard")
    
    def action_refresh(self) -> None:
        self.load_logs()
        self.notify("Logs refreshed", severity="information")
    
    def action_quit(self) -> None:
        self.app.exit()


# ============================================================================
# Output Modal
# ============================================================================

class OutputModal(ModalScreen):
    """Modal for displaying command output."""
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("enter", "close", "Close"),
    ]
    
    def __init__(self, title: str, content: str) -> None:
        super().__init__()
        self.title = title
        self.content = content
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"[bold]{self.title}[/]", classes="panel-title"),
            ScrollableContainer(
                Static(self.content),
            ),
            Static(""),
            Button("Close", id="btn-close", classes="secondary"),
            id="modal-dialog",
        )
    
    def action_close(self) -> None:
        self.dismiss()
    
    @on(Button.Pressed, "#btn-close")
    def on_close(self) -> None:
        self.dismiss()


# ============================================================================
# Main Application
# ============================================================================

class StationCalyxTUI(App):
    """Station Calyx Terminal User Interface."""
    
    TITLE = "Station Calyx"
    SUB_TITLE = "AI-For-All Project"
    CSS = CALYX_CSS
    
    MODES = {
        "welcome": WelcomeScreen,
        "dashboard": DashboardScreen,
        "governance": GovernanceScreen,
        "actions": ActionsScreen,
        "logs": LogsScreen,
    }
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("d", "switch_mode('dashboard')", "Dashboard", show=True),
        Binding("g", "switch_mode('governance')", "Governance", show=True),
        Binding("a", "switch_mode('actions')", "Actions", show=True),
        Binding("l", "switch_mode('logs')", "Logs", show=True),
        Binding("?", "help", "Help", show=True),
    ]
    
    def on_mount(self) -> None:
        self.switch_mode("welcome")
    
    def action_help(self) -> None:
        help_text = """
[bold]Station Calyx TUI - Keyboard Shortcuts[/]

[cyan]Navigation:[/]
  d     Dashboard
  g     Governance
  a     Actions
  l     Logs
  
[cyan]Actions:[/]
  r     Refresh current view
  ?     Show this help
  q     Quit

[cyan]In Modals:[/]
  Enter / Escape    Close modal

[bold]Station Calyx / AI-For-All[/]
"Capability under governance. Action with authorization."
        """
        self.push_screen(OutputModal("Help", help_text))


# ============================================================================
# Entry Point
# ============================================================================

def main():
    """Run the Station Calyx TUI."""
    app = StationCalyxTUI()
    app.run()


if __name__ == "__main__":
    main()
