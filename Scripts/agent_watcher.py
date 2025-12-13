#!/usr/bin/env python3
"""
Calyx Agent Watcher - Real-time Dashboard for Station Calyx

Real-time monitoring and control dashboard for all Calyx Terminal agents.
Provides visibility into agent activity, health, and coordination status.

Features:
- Real-time agent status monitoring
- Agent health scoring and alerts
- Control channel integration (banners, logs, toasts)
- Paged view with customizable options
- CBO integration for system-level coordination
"""

from __future__ import annotations

import argparse
import json
import os
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOGS = ROOT / "logs"
REGISTRY = ROOT / "calyx" / "core" / "registry.jsonl"
STATUS_FILE = OUT / "agent_watcher" / "status.json"
TOKEN_LOCK = OUT / "watcher_token.lock"
CMDS_DIR = OUT / "watcher_cmds"
PREFS_FILE = OUT / "watcher_prefs.json"


class AgentWatcherDashboard:
    """Tkinter-based agent monitoring dashboard"""
    
    def __init__(self, page_size: int = 20, hide_idle: bool = False, quiet: bool = False):
        self.page_size = page_size
        self.hide_idle = hide_idle
        self.quiet = quiet
        self.running = True
        
        # UI state
        self.root = None
        self.agent_rows = {}
        self.update_thread = None
        
        # Load preferences
        self.prefs = self._load_prefs()
        
        # Generate and save token
        self._ensure_token()
        
    def _load_prefs(self) -> Dict[str, Any]:
        """Load watcher preferences"""
        try:
            if PREFS_FILE.exists():
                return json.loads(PREFS_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass
        return {
            "theme": "calm",
            "scaling": 1.5,
            "hide_idle": self.hide_idle,
            "hide_stale": True,
            "compact": False,
            "density": "normal"
        }
    
    def _ensure_token(self) -> None:
        """Generate and save watcher token"""
        import uuid
        token = uuid.uuid4().hex
        payload = {
            "token": token,
            "created": time.time(),
            "pid": os.getpid()
        }
        TOKEN_LOCK.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_LOCK.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    
    def start(self):
        """Start the dashboard"""
        self.root = tk.Tk()
        self.root.title("Calyx Agent Watcher - Station Calyx Dashboard")
        self.root.geometry("1200x800")
        
        # Setup UI
        self._setup_ui()
        
        # Start update thread
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
        # Start UI loop
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
    
    def _setup_ui(self):
        """Setup the UI components"""
        # Top banner
        banner_frame = ttk.Frame(self.root, padding=10)
        banner_frame.pack(fill=tk.X)
        
        self.banner_label = ttk.Label(
            banner_frame,
            text="Station Calyx - Agent Monitoring Dashboard",
            font=("Arial", 12, "bold")
        )
        self.banner_label.pack(side=tk.LEFT)
        
        # Status indicator
        self.status_label = ttk.Label(
            banner_frame,
            text="●",
            foreground="green",
            font=("Arial", 16)
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # Main content area
        content = ttk.Frame(self.root)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Agent list
        left_panel = ttk.LabelFrame(content, text="Agents", padding=5)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Agent list frame with scrollbar
        list_frame = ttk.Frame(left_panel)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.agent_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 9)
        )
        self.agent_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.agent_listbox.yview)
        
        # Bind selection
        self.agent_listbox.bind('<<ListboxSelect>>', self._on_agent_select)
        
        # Right panel - Details
        right_panel = ttk.LabelFrame(content, text="Agent Details", padding=5)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Details text
        self.details_text = scrolledtext.ScrolledText(
            right_panel,
            font=("Consolas", 9),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.details_text.pack(fill=tk.BOTH, expand=True)
        
        # Bottom panel - System status
        bottom_panel = ttk.LabelFrame(self.root, text="System Status", padding=5)
        bottom_panel.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        status_frame = ttk.Frame(bottom_panel)
        status_frame.pack(fill=tk.X)
        
        self.system_health_label = ttk.Label(
            status_frame,
            text="System Health: Loading...",
            font=("Arial", 10)
        )
        self.system_health_label.pack(side=tk.LEFT, padx=5)
        
        self.agents_count_label = ttk.Label(
            status_frame,
            text="Agents: 0 active / 0 total",
            font=("Arial", 10)
        )
        self.agents_count_label.pack(side=tk.LEFT, padx=5)
        
        self.last_update_label = ttk.Label(
            status_frame,
            text="Last Update: Never",
            font=("Arial", 9),
            foreground="gray"
        )
        self.last_update_label.pack(side=tk.RIGHT, padx=5)
        
        # Controls frame
        controls_frame = ttk.Frame(self.root)
        controls_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(controls_frame, text="Refresh", command=self._refresh_now).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls_frame, text="Clear Logs", command=self._clear_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls_frame, text="CBO Status", command=self._show_cbo_status).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls_frame, text="CBO Reports", command=self._show_cbo_reports).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls_frame, text="TES Metrics", command=self._show_tes_metrics).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls_frame, text="Settings", command=self._show_settings).pack(side=tk.LEFT, padx=2)
        
        # Process command queue
        ttk.Button(controls_frame, text="Process Commands", command=self._process_commands).pack(side=tk.RIGHT, padx=2)
    
    def _update_loop(self):
        """Background update loop"""
        while self.running:
            try:
                self._update_agent_status()
                self._process_command_queue()
                time.sleep(2)  # Update every 2 seconds
            except Exception as e:
                if not self.quiet:
                    print(f"Update error: {e}")
                time.sleep(5)
    
    def _update_agent_status(self):
        """Update agent status from monitoring backend"""
        try:
            if not STATUS_FILE.exists():
                # Backend not running, show basic info
                self._show_basic_status()
                return
            
            data = json.loads(STATUS_FILE.read_text(encoding='utf-8'))
            obs = data.get('observation', {})
            
            if not obs:
                return
            
            # Update system status
            agents_active = obs.get('agents_active', 0)
            agents_total = obs.get('agents_observed', 0)
            health_score = obs.get('system_health_score', 0)
            
            self.root.after(0, lambda: self.system_health_label.config(
                text=f"System Health: {health_score:.1f}%"
            ))
            
            self.root.after(0, lambda: self.agents_count_label.config(
                text=f"Agents: {agents_active} active / {agents_total} total"
            ))
            
            self.root.after(0, lambda: self.last_update_label.config(
                text=f"Last Update: {datetime.now().strftime('%H:%M:%S')}"
            ))
            
            # Update agent list
            agent_states = obs.get('agent_states', {})
            self.root.after(0, lambda: self._update_agent_list(agent_states))
            
            # Update color indicator
            if health_score >= 80:
                color = "green"
            elif health_score >= 50:
                color = "orange"
            else:
                color = "red"
            
            self.root.after(0, lambda: self.status_label.config(foreground=color))
            
        except Exception as e:
            if not self.quiet:
                print(f"Status update error: {e}")
    
    def _show_basic_status(self):
        """Show basic status when backend is not running"""
        self.root.after(0, lambda: self.system_health_label.config(
            text="System Health: Backend not running"
        ))
        self.root.after(0, lambda: self.status_label.config(foreground="gray"))
    
    def _update_agent_list(self, agent_states: Dict[str, Any]):
        """Update the agent listbox"""
        self.agent_listbox.delete(0, tk.END)
        
        filtered_agents = []
        for agent_id, state in agent_states.items():
            health_score = state.get('health_score', 0)
            
            # Apply filters
            if self.hide_idle and health_score < 50:
                continue
            
            filtered_agents.append((agent_id, state))
        
        # Sort by health score (best first)
        filtered_agents.sort(key=lambda x: x[1].get('health_score', 0), reverse=True)
        
        # Apply paging
        page_start = 0
        page_end = min(self.page_size, len(filtered_agents))
        page_agents = filtered_agents[page_start:page_end]
        
        for agent_id, state in page_agents:
            health_score = state.get('health_score', 0)
            role = state.get('role', 'unknown')
            is_active = state.get('is_active', False)
            
            # Format entry
            status_char = "●" if is_active else "○"
            if health_score >= 80:
                status_color = "●"
            elif health_score >= 50:
                status_color = "○"
            else:
                status_color = "○"
            
            entry = f"{status_char} {agent_id:<25} [{role:<12}] {health_score:>5.1f}%"
            self.agent_listbox.insert(tk.END, entry)
            
            # Store for details lookup
            self.agent_rows[agent_id] = state
    
    def _on_agent_select(self, event):
        """Handle agent selection"""
        selection = self.agent_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        agent_id = list(self.agent_rows.keys())[index]
        state = self.agent_rows[agent_id]
        
        self._show_agent_details(agent_id, state)
    
    def _show_agent_details(self, agent_id: str, state: Dict[str, Any]):
        """Show detailed agent information"""
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        
        details = []
        details.append(f"Agent: {agent_id}")
        details.append(f"Role: {state.get('role', 'unknown')}")
        details.append(f"Status: {state.get('status_message', 'unknown')}")
        details.append(f"Health Score: {state.get('health_score', 0):.1f}%")
        details.append(f"Active: {'Yes' if state.get('is_active') else 'No'}")
        
        process_info = state.get('process_info')
        if process_info:
            details.append("")
            details.append("Process Information:")
            details.append(f"  PID: {process_info.get('pid', 'N/A')}")
            details.append(f"  Status: {process_info.get('status', 'N/A')}")
            details.append(f"  CPU: {process_info.get('cpu_percent', 0):.1f}%")
            details.append(f"  Memory: {process_info.get('memory_mb', 0):.1f} MB")
            details.append(f"  Command: {process_info.get('cmdline', 'N/A')}")
        
        lock_info = state.get('lock_file_exists')
        if lock_info is not None:
            details.append("")
            details.append("Lock File:")
            details.append(f"  Exists: {'Yes' if lock_info else 'No'}")
            if state.get('lock_file_age'):
                details.append(f"  Age: {state.get('lock_file_age', 0):.1f}s")
        
        resource_usage = state.get('resource_usage', {})
        if resource_usage:
            details.append("")
            details.append("Resource Usage:")
            for key, value in resource_usage.items():
                details.append(f"  {key}: {value}")
        
        self.details_text.insert(1.0, "\n".join(details))
        self.details_text.config(state=tk.DISABLED)
    
    def _process_command_queue(self):
        """Process incoming commands from agent_control"""
        if not CMDS_DIR.exists():
            return
        
        try:
            for cmd_file in sorted(CMDS_DIR.glob("*.json")):
                try:
                    data = json.loads(cmd_file.read_text(encoding='utf-8'))
                    
                    # Verify token
                    token = data.get('token')
                    expected_token = json.loads(TOKEN_LOCK.read_text()).get('token')
                    if token != expected_token:
                        cmd_file.unlink()
                        continue
                    
                    # Process command
                    cmd = data.get('cmd')
                    args = data.get('args', {})
                    
                    if cmd == 'set_banner':
                        self._set_banner(args.get('text', ''), args.get('color', '#1f6feb'))
                    elif cmd == 'append_log':
                        self._append_log(args.get('text', ''))
                    elif cmd == 'show_toast':
                        self._show_toast(args.get('text', ''))
                    elif cmd == 'open_path':
                        self._open_path(args.get('path', ''))
                    
                    # Remove processed command
                    cmd_file.unlink()
                    
                except Exception as e:
                    if not self.quiet:
                        print(f"Command processing error: {e}")
                    cmd_file.unlink()
                    
        except Exception:
            pass
    
    def _set_banner(self, text: str, color: str = "#1f6feb"):
        """Set banner text"""
        self.root.after(0, lambda: self.banner_label.config(text=text))
    
    def _append_log(self, text: str):
        """Append to details log"""
        self.root.after(0, lambda: self.details_text.insert(tk.END, f"\n{text}"))
    
    def _show_toast(self, text: str):
        """Show toast notification"""
        # Simple implementation - could use a toast library
        messagebox.showinfo("Calyx Agent Watcher", text)
    
    def _open_path(self, path: str):
        """Open a path (safety check needed)"""
        # Only allow paths under repo root
        full_path = ROOT / path
        if full_path.exists() and full_path.is_relative_to(ROOT):
            os.startfile(str(full_path))
    
    def _refresh_now(self):
        """Force immediate refresh"""
        self._update_agent_status()
    
    def _clear_logs(self):
        """Clear the details log"""
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.config(state=tk.DISABLED)
    
    def _show_cbo_status(self):
        """Show comprehensive CBO status in a dialog"""
        try:
            cbo_info = self._get_cbo_status()
            
            # Create a new window for CBO status
            cbo_window = tk.Toplevel(self.root)
            cbo_window.title("CBO Status")
            cbo_window.geometry("800x600")
            
            # Notebook for tabs
            notebook = ttk.Notebook(cbo_window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Status tab
            status_frame = ttk.Frame(notebook)
            notebook.add(status_frame, text="Status")
            status_text = scrolledtext.ScrolledText(status_frame, font=("Consolas", 9))
            status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            status_text.insert(1.0, json.dumps(cbo_info, indent=2))
            status_text.config(state=tk.DISABLED)
            
            # Recent Reports tab
            reports_frame = ttk.Frame(notebook)
            notebook.add(reports_frame, text="Recent Reports")
            reports_text = scrolledtext.ScrolledText(reports_frame, font=("Consolas", 9))
            reports_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Get recent reports
            recent_reports = self._get_recent_cbo_reports()
            for report in recent_reports:
                reports_text.insert(tk.END, f"{report}\n")
            reports_text.config(state=tk.DISABLED)
            
            # TES Metrics tab
            tes_frame = ttk.Frame(notebook)
            notebook.add(tes_frame, text="TES Metrics")
            tes_text = scrolledtext.ScrolledText(tes_frame, font=("Consolas", 9))
            tes_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            tes_data = self._get_tes_metrics()
            tes_text.insert(1.0, json.dumps(tes_data, indent=2))
            tes_text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CBO status: {e}")
    
    def _get_cbo_status(self) -> Dict[str, Any]:
        """Get comprehensive CBO status"""
        status = {
            "cbo_running": False,
            "process_info": None,
            "latest_report": None,
            "coordinator_status": None,
            "system_health": None
        }
        
        # Check for CBO process
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'bridge_overseer' in cmdline.lower():
                        status["cbo_running"] = True
                        status["process_info"] = {
                            "pid": proc.info['pid'],
                            "cmdline": cmdline
                        }
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        
        # Check for latest report
        reports_dir = OUT / "overseer_reports"
        if reports_dir.exists():
            reports = sorted(reports_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
            if reports:
                status["latest_report"] = {
                    "filename": reports[0].name,
                    "modified": datetime.fromtimestamp(reports[0].stat().st_mtime).isoformat()
                }
        
        # Check coordinator status
        coordinator_state = ROOT / "state" / "coordinator_state.json"
        if coordinator_state.exists():
            try:
                status["coordinator_status"] = json.loads(coordinator_state.read_text(encoding='utf-8'))
            except Exception:
                pass
        
        # Get system health
        try:
            if STATUS_FILE.exists():
                data = json.loads(STATUS_FILE.read_text(encoding='utf-8'))
                obs = data.get('observation', {})
                status["system_health"] = {
                    "health_score": obs.get('system_health_score', 0),
                    "agents_active": obs.get('agents_active', 0),
                    "agents_total": obs.get('agents_observed', 0)
                }
        except Exception:
            pass
        
        return status
    
    def _get_recent_cbo_reports(self) -> List[str]:
        """Get list of recent CBO reports"""
        reports = []
        reports_dir = OUT / "overseer_reports"
        
        if reports_dir.exists():
            for report_file in sorted(reports_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
                reports.append(report_file.name)
        
        return reports
    
    def _get_tes_metrics(self) -> Dict[str, Any]:
        """Get TES metrics from analyzer"""
        tes_data = {}
        
        try:
            tes_file = ROOT / "logs" / "agent_metrics.csv"
            if tes_file.exists():
                import csv
                with tes_file.open('r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    if rows:
                        latest = rows[-1]
                        tes_data = {
                            "latest_tes": latest.get('tes', 'N/A'),
                            "latest_timestamp": latest.get('timestamp', 'N/A'),
                            "recent_average": self._calculate_tes_average(rows[-10:])
                        }
        except Exception as e:
            tes_data = {"error": str(e)}
        
        return tes_data
    
    def _calculate_tes_average(self, rows: List[Dict]) -> float:
        """Calculate average TES from recent rows"""
        try:
            tes_values = [float(row.get('tes', 0)) for row in rows if row.get('tes')]
            return sum(tes_values) / len(tes_values) if tes_values else 0.0
        except Exception:
            return 0.0
    
    def _show_settings(self):
        """Show settings dialog"""
        messagebox.showinfo("Settings", f"Page Size: {self.page_size}\nHide Idle: {self.hide_idle}")
    
    def _show_cbo_reports(self):
        """Show available CBO reports"""
        try:
            reports = self._get_recent_cbo_reports()
            
            if not reports:
                messagebox.showinfo("CBO Reports", "No reports found")
                return
            
            # Create selection dialog
            report_window = tk.Toplevel(self.root)
            report_window.title("CBO Reports")
            report_window.geometry("600x400")
            
            listbox = tk.Listbox(report_window, font=("Consolas", 9))
            listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            for report in reports:
                listbox.insert(tk.END, report)
            
            def open_report():
                selection = listbox.curselection()
                if selection:
                    report_name = reports[selection[0]]
                    report_path = OUT / "overseer_reports" / report_name
                    if report_path.exists():
                        os.startfile(str(report_path))
            
            ttk.Button(report_window, text="Open Selected", command=open_report).pack(pady=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load reports: {e}")
    
    def _show_tes_metrics(self):
        """Show TES metrics in a dialog"""
        try:
            tes_data = self._get_tes_metrics()
            
            tes_window = tk.Toplevel(self.root)
            tes_window.title("TES Metrics")
            tes_window.geometry("500x300")
            
            tes_text = scrolledtext.ScrolledText(tes_window, font=("Consolas", 9))
            tes_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            tes_text.insert(1.0, json.dumps(tes_data, indent=2))
            tes_text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load TES metrics: {e}")
    
    def _process_commands(self):
        """Manually process command queue"""
        self._process_command_queue()
    
    def _on_close(self):
        """Handle window close"""
        self.running = False
        self.root.destroy()


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point"""
    ap = argparse.ArgumentParser(description="Calyx Agent Watcher Dashboard")
    ap.add_argument("--page-size", type=int, default=20, help="Number of agents per page")
    ap.add_argument("--hide-idle", action="store_true", help="Hide idle agents")
    ap.add_argument("--quiet", action="store_true", help="Suppress console output")
    args = ap.parse_args(argv)
    
    dashboard = AgentWatcherDashboard(
        page_size=args.page_size,
        hide_idle=args.hide_idle,
        quiet=args.quiet
    )
    
    dashboard.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
